"""
Fase 17.1 / 17.1A — Ferramenta de validação de integridade de evidências.

Verifica se a copy gerada pelo LLM preservou a precisão semântica das
evidências comerciais (CommercialEvidence): entidade, unidade e valor
numérico originais. Não modifica arquétipos nem CommercialEvidence — é uma
checagem independente, com um contrato de violações estruturado (Fase
17.1A) que o pipeline usa como gate obrigatório antes da publicação (ver
main.py::_evidence_integrity_gate).
"""
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from models import CommercialEvidence

# Entidades que NÃO podem substituir "avaliações" quando um número aparece
# na copy (ex: "1209 avaliações" virando "1209 alunos").
_FORBIDDEN_REVIEW_ENTITIES = [
    "aluno", "alunos",
    "cliente", "clientes",
    "pessoa", "pessoas",
    "usuário", "usuários", "usuario", "usuarios",
    "estudante", "estudantes",
    "paciente", "pacientes",
]

_ENTITY_SUBSTITUTION_PATTERN = re.compile(
    r'(\d[\d.,]*)\s*\.?\s*(' + '|'.join(_FORBIDDEN_REVIEW_ENTITIES) + r')\b',
    re.IGNORECASE,
)

# Linguagem de aproximação ("mais de X", "cerca de X"...) é o sinal mais
# confiável de que um número preciso foi generalizado/arredondado — evita
# falso positivo quando a evidência simplesmente não foi citada na copy
# (omissão não é distorção, ver EvidenceIntegrityValidator._validate_rating).
_APPROXIMATION_PATTERN = re.compile(
    r'(?:mais de|cerca de|aproximadamente|em torno de|quase)\s*(\d[\d.,]*)',
    re.IGNORECASE,
)


class IntegrityViolationCode(str, Enum):
    """Códigos estruturados para violações de integridade — espelham os
    ErrorCode EVIDENCE_* de api/errors.py (mesmo valor de string) para que
    o pipeline classifique o erro sem heurística adicional."""
    NUMERIC_MISMATCH = "EVIDENCE_NUMERIC_MISMATCH"
    ENTITY_SUBSTITUTION = "EVIDENCE_ENTITY_SUBSTITUTION"
    UNSUPPORTED_INFERENCE = "EVIDENCE_UNSUPPORTED_INFERENCE"
    TIME_INTERPRETATION = "EVIDENCE_TIME_INTERPRETATION"
    MISSING_EVIDENCE = "EVIDENCE_MISSING"  # evidência disponível, mas não usada — não é distorção


@dataclass
class IntegrityViolation:
    """Representa uma violação de integridade de evidência."""
    code: IntegrityViolationCode
    message: str
    evidence: Optional[str] = None
    copy_snippet: Optional[str] = None
    severity: str = "high"  # critical, high, medium, low


class EvidenceIntegrityResult:
    """Resultado estruturado da validação de integridade.

    `passed` é False assim que QUALQUER violação é registrada, mas o gate do
    pipeline só bloqueia a publicação para severidade "high"/"critical" —
    ver main.py::_evidence_integrity_gate. Violações "medium"/"low" ficam
    registradas para observabilidade, sem impedir a publicação.
    """

    def __init__(self):
        self.passed: bool = True
        self.violations: List[IntegrityViolation] = []

    def add_violation(
        self,
        code: IntegrityViolationCode,
        message: str,
        evidence: Optional[str] = None,
        copy_snippet: Optional[str] = None,
        severity: str = "high",
    ) -> None:
        self.passed = False
        self.violations.append(IntegrityViolation(
            code=code,
            message=message,
            evidence=evidence,
            copy_snippet=copy_snippet,
            severity=severity,
        ))

    @property
    def critical_violations(self) -> List[IntegrityViolation]:
        """Violações que devem bloquear a publicação (severity high/critical)."""
        return [v for v in self.violations if v.severity in ("high", "critical")]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "violations": [
                {
                    "code": v.code.value,
                    "message": v.message,
                    "evidence": v.evidence,
                    "copy_snippet": v.copy_snippet,
                    "severity": v.severity,
                }
                for v in self.violations
            ],
        }


class EvidenceIntegrityValidator:
    """Valida se a copy preservou a integridade das evidências fornecidas."""

    def __init__(self, evidence: CommercialEvidence):
        self.evidence = evidence

    def validate(self, copy: str) -> EvidenceIntegrityResult:
        """Valida a copy contra as evidências fornecidas. Retorna um
        EvidenceIntegrityResult novo a cada chamada (sem estado acumulado
        entre validações)."""
        result = EvidenceIntegrityResult()

        # Sem evidência configurada, não há nada a preservar.
        if not self.evidence.has_evidence:
            return result

        if self.evidence.credentials:
            for cred in self.evidence.credentials:
                if "avalia" in cred.lower():
                    self._validate_rating(copy, cred, result)

        if self.evidence.opening_hours:
            self._validate_opening_hours(copy, result)

        if self.evidence.services:
            self._validate_services(copy, result)

        return result

    def _validate_rating(self, copy: str, cred: str, result: EvidenceIntegrityResult) -> None:
        """Valida que rating/contagem de avaliações não foi distorcido."""
        rating_match = re.search(r'(\d+\.?\d*)\s*/\s*5', cred)
        count_match = re.search(r'(\d[\d.]*)\s*avalia', cred.lower())

        # 1. Substituição de entidade: qualquer número seguido de uma
        #    entidade proibida (aluno/cliente/pessoa/...) enquanto a
        #    evidência em questão é sobre avaliações — crítico independente
        #    de o número bater exatamente (o número também pode ter sido
        #    arredondado junto com a troca de entidade).
        for m in _ENTITY_SUBSTITUTION_PATTERN.finditer(copy):
            result.add_violation(
                code=IntegrityViolationCode.ENTITY_SUBSTITUTION,
                message=f"Transformou avaliações em '{m.group(2).lower()}'",
                evidence=cred,
                copy_snippet=copy[max(0, m.start() - 20): m.end() + 20],
                severity="critical",
            )

        # 2. Rating/contagem ausente da copy inteiramente NÃO é violação — a
        #    evidência pode simplesmente não ter sido usada nessa copy.
        #    Só é violação quando o número É usado mas distorcido: seja por
        #    troca de entidade (acima) seja por arredondamento/generalização
        #    (abaixo, via linguagem de aproximação: "mais de X", "cerca de X"...).

        # 3. Precisão numérica: uma alegação aproximada ("mais de 1200
        #    avaliações") sobre a MESMA contagem que a evidência já dá com
        #    precisão exata é uma perda de precisão do fato original.
        if count_match:
            raw = count_match.group(1)
            digits = re.sub(r'\D', '', raw)

            for m in _APPROXIMATION_PATTERN.finditer(copy):
                mention_digits = re.sub(r'\D', '', m.group(1))
                if mention_digits and mention_digits != digits:
                    result.add_violation(
                        code=IntegrityViolationCode.NUMERIC_MISMATCH,
                        message=(
                            f"Número de avaliações ({digits}) foi generalizado/arredondado "
                            f"para '{m.group(0)}' na copy"
                        ),
                        evidence=cred,
                        copy_snippet=m.group(0),
                        severity="high",
                    )

    def _validate_opening_hours(self, copy: str, result: EvidenceIntegrityResult) -> None:
        """Valida que horário não foi distorcido para uma alegação não fundamentada."""
        hours = self.evidence.opening_hours or ""
        copy_lower = copy.lower()
        if "flexível" in copy_lower and "flexível" not in hours.lower():
            idx = copy_lower.find("flexível")
            result.add_violation(
                code=IntegrityViolationCode.TIME_INTERPRETATION,
                message="Adicionou 'horário flexível' sem evidência",
                evidence=hours,
                copy_snippet=copy[idx:idx + 50],
                severity="medium",
            )

    def _validate_services(self, copy: str, result: EvidenceIntegrityResult) -> None:
        """Reservado para validações específicas de serviços/produtos (não
        há regra de distorção conhecida ainda para este campo)."""
        pass


def validate_copy_against_evidence(evidence: CommercialEvidence, copy: str) -> Dict[str, Any]:
    """Atalho funcional para validar uma copy contra uma evidência.

    Retorna o formato legado (dict com `has_violations`/`violations` como
    lista de strings) usado pelos testes da Fase 17.1, mantido por
    compatibilidade — para o contrato estruturado (códigos, severidade),
    use EvidenceIntegrityValidator(evidence).validate(copy) diretamente.
    """
    result = EvidenceIntegrityValidator(evidence).validate(copy)
    return {
        "has_violations": not result.passed,
        "violations": [v.message for v in result.violations],
        "copy": copy,
    }


if __name__ == "__main__":
    import sys

    example_evidence = CommercialEvidence(
        credentials=["Avaliação 4.1/5 no Google (1209 avaliações)"],
        opening_hours="Seg-Sex 08:00-18:00",
    )
    example_copy = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "Mais de 1.200 alunos satisfeitos, com horário flexível para você."
    )

    result = EvidenceIntegrityValidator(example_evidence).validate(example_copy)
    print(f"Passou: {result.passed}")
    print(f"Violações encontradas: {len(result.violations)}")
    for v in result.violations:
        print(f" - [{v.severity}] {v.code.value}: {v.message}")
