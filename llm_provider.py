import os
import re
import json
import logging
import requests
from typing import Optional
from models import BusinessData, LLMOutput, ProposalTemplateData, normalize_llm_output

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Fase 17.1: Evidence Integrity — instruções obrigatórias para impedir que o
# LLM reinterprete evidências verificáveis (ex: "1209 avaliações" virando
# "mais de 1.200 alunos"), trocando a entidade, a unidade ou a precisão do
# fato original. Injetado no prompt principal logo após o bloco de evidências.
EVIDENCE_INTEGRITY = """
INTEGRIDADE DA EVIDÊNCIA (REGRAS OBRIGATÓRIAS):

As evidências fornecidas são FATOS VERIFICÁVEIS. Você DEVE preservar sua precisão semântica.

REGRAS:
1. NUNCA mude a ENTIDADE de um número:
   - "1209 avaliações" → NUNCA vire "1209 clientes", "1209 alunos", "1209 pessoas"
   - "4.1/5" → NUNCA vire "excelente" (a menos que seja paráfrase explícita)
   - Mantenha a UNIDADE ORIGINAL: avaliações, estrelas, horas, anos

2. NUNCA mude a RELAÇÃO CAUSAL:
   - "Avaliação alta" → NÃO implica automaticamente "clientes satisfeitos" (a menos que seja dito)
   - "Horário 08-18" → NÃO vire "horário flexível" (a menos que seja dito)
   - "Website disponível" → NÃO vire "serviços online"

3. NUNCA infira FATOS NÃO DECLARADOS:
   - Se não há evidência de "alunos", NÃO mencione alunos
   - Se não há evidência de "clientes satisfeitos", NÃO mencione clientes satisfeitos
   - Se não há evidência de "preço", NÃO mencione preço
   - Se não há evidência de "desconto", NÃO mencione desconto

4. PRESERVE A FONTE quando relevante:
   - "Avaliação 4.1/5 no Google" (correto)
   - "Avaliação excelente" (impreciso - qual fonte?)
   - "4.1 estrelas" (aceitável se a fonte for Google)

5. NÚMEROS devem manter sua PRECISÃO:
   - "1209" → NUNCA vire "mais de 1200" (isso altera o fato)
   - "4.1" → NUNCA vire "4.5" ou "4.0"
   - "08:00" → NUNCA vire "8h" (a menos que seja claramente equivalente)

EXEMPLOS:
✅ Correto: "Avaliação 4.1/5 no Google, com 1.209 avaliações"
❌ Incorreto: "Mais de 1.200 alunos satisfeitos" (avaliações ≠ alunos)
✅ Correto: "Horário: Segunda a Sexta, 08:00-18:00"
❌ Incorreto: "Horário flexível" (sem evidência de flexibilidade)
✅ Correto: "Website oficial disponível para mais informações"
❌ Incorreto: "Serviços online disponíveis" (sem evidência)

AO USAR EVIDÊNCIAS:
- Cite a evidência com sua unidade original
- Preserve a fonte quando relevante
- NÃO adicione interpretações não fundamentadas
- NÃO transforme números em estimativas
- NÃO mude a entidade dos dados
"""


def clean_json_payload(raw_text: str) -> str:
    """Remove blocos de markdown e extrai JSON puro."""
    text = raw_text.strip()
    m = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text, re.IGNORECASE)
    if m:
        text = m.group(1)
    start, end = text.find('{'), text.rfind('}')
    if start != -1 and end != -1:
        text = text[start:end+1]
    return text.strip()


def call_ollama(prompt: str, temperature: float) -> str:
    """Chama Ollama local."""
    host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
    model = os.getenv('OLLAMA_MODEL', 'qwen2.5:7b')
    
    r = requests.post(
        f"{host}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {"temperature": temperature}
        },
        timeout=90
    )
    r.raise_for_status()
    return r.json().get('response', '')


def call_gemini(prompt: str, temperature: float) -> str:
    """Chama Gemini API."""
    from google import genai

    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY não configurada no .env")

    # Modelo configurável via env — evita quebrar em produção quando a Google
    # descontinua uma versão fixa (ex: gemini-2.0-flash). "gemini-flash-latest"
    # é um alias mantido pela Google sempre apontando para um modelo suportado.
    model = os.getenv('GEMINI_MODEL', 'gemini-flash-latest')

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config={"temperature": temperature}
    )
    return response.text


def call_agnes(prompt: str, temperature: float) -> str:
    """Chama Agnes (OpenAI-compatible)."""
    api_key = os.getenv('AGNES_API_KEY')
    if not api_key:
        raise ValueError("AGNES_API_KEY não configurada no .env")
    
    base_url = os.getenv('AGNES_BASE_URL', 'https://apihub.agnes-ai.com/v1')
    model = os.getenv('AGNES_MODEL', 'agnes-2.0-flash')
    
    r = requests.post(
        f"{base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature
        },
        timeout=90
    )
    r.raise_for_status()
    return r.json()['choices'][0]['message']['content']


def call_llm(provider: str, prompt: str, temperature: float) -> str:
    """Dispatch para o provedor correto."""
    if provider == 'ollama':
        return call_ollama(prompt, temperature)
    elif provider == 'gemini':
        return call_gemini(prompt, temperature)
    elif provider == 'agnes':
        return call_agnes(prompt, temperature)
    else:
        raise ValueError(f"Provedor LLM desconhecido: {provider}")


def trigger_telegram_alert(place_id: str, message: str):
    """Envia alerta para Telegram (implementação placeholder)."""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        logging.warning(f"[ALERTA TELEGRAM] {place_id}: {message}")
        return
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={
            "chat_id": chat_id,
            "text": f"🚨 {place_id}\n{message}"
        }, timeout=5)
    except Exception as e:
        logging.error(f"Falha ao enviar alerta Telegram: {e}")


def generate_proposal_with_fallback(
    trusted_business: dict,
    max_retries: int = 3
) -> Optional[ProposalTemplateData]:
    """
    Gera proposta com retry e fallback de LLM.
    
    Args:
        trusted_business: Dados validados da Places API (name, niche, city, place_id, phone)
        max_retries: Número máximo de tentativas antes de fallback
    
    Returns:
        ProposalTemplateData ou None se falhar
    """
    primary_llm = os.getenv('PRIMARY_LLM', 'ollama')
    fallback_llm = os.getenv('FALLBACK_LLM', 'gemini')
    
    # Validação fora do loop (fail fast)
    try:
        business_obj = BusinessData(**trusted_business)
    except Exception as e:
        trigger_telegram_alert(
            trusted_business.get('place_id', 'UNKNOWN'),
            f"Dados de negócio inválidos: {e}"
        )
        # Erro estruturado (prefixo "INVALID_LEAD:") em vez de engolir a
        # exceção — permite classificação determinística por código no
        # pipeline_adapter, independente do conteúdo da mensagem (ex: nome
        # do lead coincidir por acaso com palavras da heurística de string).
        raise ValueError(f"INVALID_LEAD: Dados de negócio inválidos: {e}") from e
    
    original_prompt = (
        f"Gere APENAS JSON com chaves copywriting, assets, seo. "
        f"NÃO gere business, place_id, slug ou phone. "
        f"REGRAS CRÍTICAS DE PERSPECTIVA (FOCO NO CONSUMIDOR FINAL - B2C):\n"
        f"1) O site gerado é uma página de vendas para o CLIENTE FINAL do estabelecimento. Proibido usar palavras como 'negócio', 'gestão', 'empresa' ou 'transformar'.\n"
        f"2) A seção de 'pain_points' deve focar nos desejos e frustrações reais do consumidor "
        f"COM O NICHO ESPECÍFICO informado em 'niche' abaixo — nunca em problemas de gestão do dono, "
        f"e nunca reaproveitando um desejo típico de outro tipo de negócio.\n"
        f"3) Use urgência apenas quando fizer sentido para o nicho informado. A urgência deve ser "
        f"específica e plausível para ESSE negócio — não invente promoções, descontos, escassez, "
        f"horários ou condições comerciais que não estejam no contexto fornecido. "
        f"NÃO copie frases de urgência de outro segmento (ex: uma expressão sobre comida saindo do "
        f"forno não faz sentido numa oficina mecânica ou numa loja de roupas).\n"
        f"4) O Hero deve ser focado em experiência e localização: '[Nome]: O melhor [Nicho] de [Cidade]'.\n"
        f"\n"
        f"VOCABULÁRIO DO NICHO — verificação antes de responder:\n"
        f"Toda a copy (headline, subheadline, pain_points, proofs, cta_whatsapp) deve usar "
        f"vocabulário compatível exclusivamente com o nicho '{trusted_business.get('niche', '')}' "
        f"e com os dados do negócio abaixo.\n"
        f"- Nenhuma expressão, metáfora ou gatilho de urgência pode pertencer a outro segmento "
        f"(ex: termos de comida/alimentação num negócio que não vende comida).\n"
        f"- A copy deve poder ser lida isoladamente por um consumidor desse nicho sem parecer "
        f"adaptada de outro tipo de negócio.\n"
        f"- Se um exemplo citado nestas instruções não fizer sentido para o nicho atual, NÃO o reutilize "
        f"literalmente — use-o só como referência de tom, nunca como texto a copiar.\n"
        f"\n"
        f"EVIDÊNCIAS COMERCIAIS (FATOS VERIFICÁVEIS):\n"
        f"{business_obj.evidence.evidence_summary}\n"
        f"{EVIDENCE_INTEGRITY}\n"
        f"5) Use as evidências acima como a ÚNICA fonte de fatos específicos (horário, "
        f"disponibilidade, diferenciais, credenciais, ofertas). Se a lista disser 'Nenhuma "
        f"evidência comercial disponível', NÃO invente nenhum desses fatos — fique em copy "
        f"genérica mas honesta para essa parte, sem alegar horário, promoção, prêmio ou "
        f"diferencial que não esteja explicitamente listado acima.\n"
        f"\n"
        f"Contexto: {json.dumps({k: v for k, v in trusted_business.items() if k not in ('evidence', 'location')}, ensure_ascii=False)}\n\n"
        f"Estrutura JSON obrigatória:\n"
        f"{{\n"
        f'  "copywriting": {{\n'
        f'    "headline": "Título principal (5-80 caracteres)",\n'
        f'    "subheadline": "Subtítulo (5-140 caracteres)",\n'
        f'    "cta_whatsapp": "Texto curto do botão (2-30 caracteres)",\n'
        f'    "pain_points": ["Dor/necessidade 1", "Dor/necessidade 2"],\n'
        f'    "proofs": ["Prova 1", "Prova 2"]\n'
        f"  }},\n"
        f'  "assets": {{\n'
        f'    "suggested_images_keywords": ["palavra1", "palavra2", "palavra3"],\n'
        f'    "color_palette_hint": "Descrição cores",\n'
        f'    "primary_color": "#HEX"\n'
        f"  }},\n"
        f'  "seo": {{\n'
        f'    "title": "Título SEO (5-70 caracteres)",\n'
        f'    "description": "Descrição SEO (20-160 caracteres)"\n'
        f"  }}\n"
        f"}}"
    )
    prompt, last_error = original_prompt, ""
    
    for attempt in range(max_retries):
        try:
            # Escolha do provedor baseada na tentativa
            if attempt == 0:
                raw = call_llm(primary_llm, prompt, 0.3)
            elif attempt == 1:
                # Primeira falha: retry com temperatura 0 e instrução de correção
                prompt = f"{original_prompt}\nERRO ANTERIOR: {last_error}\nCorrija e retorne JSON puro."
                raw = call_llm(primary_llm, prompt, 0.0)
            else:
                # Segunda falha: fallback definitivo
                raw = call_llm(fallback_llm, prompt, 0.0)
            
            # Limpeza, normalização (truncagem de limites mecânicos) e validação
            clean = clean_json_payload(raw)
            data = normalize_llm_output(json.loads(clean))
            llm_out = LLMOutput.model_validate(data)
            
            return ProposalTemplateData(
                business=business_obj,
                copywriting=llm_out.copywriting,
                assets=llm_out.assets,
                seo=llm_out.seo
            )
        
        except Exception as e:
            last_error = str(e)[:500]
            logging.warning(f"Tentativa {attempt + 1} falhou: {last_error}")
            continue
    
    # Falha crítica após todas as tentativas
    trigger_telegram_alert(
        business_obj.place_id,
        f"Falha crítica geração após {max_retries} tentativas: {last_error}"
    )
    return None
