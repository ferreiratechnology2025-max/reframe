// ─────────────────────────────────────────────────────────────
// Ferreira Technology — Shell Universal
// Backend simulado (modo demo). Ativado automaticamente quando
// nenhum backend responde em /health — permite experimentar a
// interface completa sem infraestrutura.
// ─────────────────────────────────────────────────────────────

import type { FileNode, Project, ProviderInfo, TerminalKind } from '../types';

const f = (name: string, size?: string): FileNode => ({ name, type: 'file', size, modified: 'há 2h' });
const d = (name: string, children: FileNode[]): FileNode => ({ name, type: 'dir', children });

export const MOCK_PROJECTS: Project[] = [
  {
    id: 'ft-gateway',
    name: 'ft-gateway',
    description: 'API Gateway central da plataforma — roteamento, autenticação e rate-limit.',
    status: 'active',
    framework: 'Node.js · Express',
    port: 8080,
    url: 'http://localhost:8080',
    createdAt: '2025-09-12',
    files: [
      d('src', [
        f('index.ts', '2.1 KB'),
        f('routes.ts', '4.8 KB'),
        d('middleware', [f('auth.ts', '1.2 KB'), f('cors.ts', '0.6 KB')]),
        d('services', [f('proxy.ts', '3.4 KB')]),
      ]),
      d('tests', [f('gateway.spec.ts', '5.9 KB')]),
      f('package.json', '0.9 KB'),
      f('.env.example', '0.3 KB'),
      f('Dockerfile', '0.4 KB'),
      f('README.md', '1.7 KB'),
    ],
  },
  {
    id: 'ecommerce-api',
    name: 'ecommerce-api',
    description: 'Microserviço de e-commerce — pedidos, pagamentos e catálogo.',
    status: 'stopped',
    framework: 'Go · chi',
    port: 3001,
    url: 'http://localhost:3001',
    createdAt: '2025-10-03',
    files: [
      d('cmd', [d('api', [f('main.go', '1.4 KB')])]),
      d('internal', [
        d('orders', [f('handler.go', '3.2 KB'), f('service.go', '2.9 KB')]),
        d('payments', [f('client.go', '1.8 KB')]),
        f('db.go', '2.2 KB'),
      ]),
      f('go.mod', '0.4 KB'),
      f('Makefile', '0.5 KB'),
      f('.env', '0.2 KB'),
    ],
  },
  {
    id: 'data-pipeline',
    name: 'data-pipeline',
    description: 'Pipeline ETL de dados — extração, transformação e carga no warehouse.',
    status: 'error',
    framework: 'Python · Airflow',
    port: 9090,
    url: 'http://localhost:9090',
    createdAt: '2025-08-21',
    files: [
      d('pipeline', [f('extract.py', '5.1 KB'), f('transform.py', '7.6 KB'), f('load.py', '3.9 KB')]),
      d('notebooks', [f('explore.ipynb', '112 KB')]),
      f('requirements.txt', '0.3 KB'),
      f('pyproject.toml', '0.8 KB'),
      f('airflow.cfg', '2.0 KB'),
    ],
  },
];

export const MOCK_PROVIDERS: ProviderInfo[] = [
  { id: 'openai', name: 'OpenAI', configured: true },
  { id: 'anthropic', name: 'Anthropic', configured: true },
  { id: 'deepseek', name: 'DeepSeek', configured: false },
];

export const delay = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

export async function getMockProjects(): Promise<Project[]> {
  await delay(420);
  return MOCK_PROJECTS;
}

export function getMockProviders(): ProviderInfo[] {
  return MOCK_PROVIDERS;
}

// ───────────────────────── Chat simulado ─────────────────────────

interface MockChatPayload {
  prompt: string;
  projectName?: string;
  model?: string;
}

interface MockHandlers {
  onChunk: (text: string) => void;
  signal?: AbortSignal;
}

export async function mockStreamChat(payload: MockChatPayload, handlers: MockHandlers): Promise<string> {
  const text = buildMockResponse(payload);
  await delay(450);
  const parts = text.split(/(\s+)/);
  const chunks: string[] = [];
  for (let i = 0; i < parts.length; i += 2) chunks.push(parts.slice(i, i + 2).join(''));
  for (const token of chunks) {
    if (handlers.signal?.aborted) return text;
    handlers.onChunk(token);
    await delay(12 + Math.random() * 24);
  }
  return text;
}

function buildMockResponse({ prompt, projectName, model }: MockChatPayload): string {
  const p = prompt.toLowerCase();
  const name = projectName ?? 'global';
  const modelLine = `\`${model ?? 'auto'}\``;

  if (/(listar|arquivo|estrutura|tree|\bls\b|files)/.test(p)) {
    return [
      `Claro! Esta é a estrutura atual do projeto **${name}**:`,
      '',
      '```bash',
      `$ ft tree --project ${name}`,
      '├── src/',
      '│   ├── index.ts',
      '│   ├── routes.ts',
      '│   └── services/',
      '├── package.json',
      '├── .env.example',
      '└── Dockerfile',
      '```',
      '',
      'Posso **criar, editar ou remover** qualquer arquivo — é só pedir. A execução acontece no seu backend via `POST /api/execute` (SSE).',
      '',
      '> ⚙️ *Modo demo ativo* — conecte seu backend em **Configurações → Conexão** para operações reais.',
    ].join('\n');
  }

  if (/(status|health|saúde|saude|online|estado)/.test(p)) {
    return [
      `Status verificado via \`GET /health\`:`,
      '',
      `- **Backend** — online (simulado, 42 ms)`,
      `- **Projeto** — \`${name}\` · estado \`active\``,
      `- **LLM** — modelo ${modelLine} disponível`,
      `- **Transporte** — REST + SSE (streaming ativo)`,
      '',
      '```bash',
      '$ ft status',
      'backend ....... online',
      `projeto ....... ${name}`,
      'uptime ........ 3h 42m',
      'memória ....... 128 MB',
      '```',
    ].join('\n');
  }

  if (/(deploy|publicar|produção|producao|subir)/.test(p)) {
    return [
      `Aqui está o roteiro de **deploy** para \`${name}\`:`,
      '',
      `1. Rodar testes — \`ft test --project ${name}\``,
      '2. Gerar build — `ft build --prod`',
      '3. Subir artefato — `ft deploy --env production`',
      '4. Smoke test — `ft health --remote`',
      '',
      '```bash',
      '$ ft deploy --env production',
      '▸ build .......... ok (2.4s)',
      '▸ upload ......... ok',
      '▸ health check ... ok',
      '✓ deploy concluído',
      '```',
      '',
      '> ⚙️ *Modo demo* — nenhuma alteração real foi aplicada.',
    ].join('\n');
  }

  if (/(contrato|endpoint|api|rest|sse)/.test(p)) {
    return [
      'O shell espera o seguinte **contrato de API** no seu backend:',
      '',
      '```json',
      '{',
      '  "health":    "GET  /health",',
      '  "projects":  "GET  /api/projects",',
      '  "chat":      "POST /api/chat     (SSE)",',
      '  "execute":   "POST /api/execute  (SSE)"',
      '}',
      '```',
      '',
      '- **SSE do chat** — linhas `data: {"content":"<delta>"}` e `data: [DONE]`',
      '- **SSE do execute** — chunks de texto bruto (stdout)',
      '- **Auth** — header `Authorization: Bearer <token>` (opcional)',
      '',
      'Você pode remapear todos os caminhos em **Configurações → Contrato de API** — o shell é 100% agnóstico de backend.',
    ].join('\n');
  }

  return [
    '**Entendido!** Vou orquestrar isso pelo shell **Ferreira Technology**.',
    '',
    '## Plano de execução',
    '',
    `1. **Analisar** — interpretar o prompt contra o contexto do projeto \`${name}\``,
    '2. **Planejar** — montar o roteiro de comandos CLI',
    '3. **Executar** — disparar via `POST /api/execute` (SSE)',
    '4. **Validar** — conferir o output e reportar o resultado',
    '',
    '```bash',
    `$ ft exec --project ${name}`,
    '▸ analisando contexto... ok',
    '▸ gerando plano... ok',
    '▸ aplicando alterações... ok',
    '✓ concluído em 1.8s',
    '```',
    '',
    `> **Modo demo** — modelo ${modelLine}. Conecte um backend real para respostas do seu LLM.`,
    '',
    '**Próximos passos:** peça para listar arquivos, ver o status ou rode comandos no terminal (`ft help`).',
  ].join('\n');
}

// ───────────────────────── CLI simulada ─────────────────────────

function flattenTree(nodes: FileNode[], prefix = ''): string[] {
  const out: string[] = [];
  for (const n of nodes) {
    out.push(prefix + (n.type === 'dir' ? n.name + '/' : n.name));
    if (n.children) out.push(...flattenTree(n.children, prefix + '  '));
  }
  return out;
}

export function mockExec(cmd: string, project?: Project | null, projects?: Project[]): string[] {
  const lower = cmd.trim().toLowerCase();

  if (lower === 'ls' || lower === 'tree' || lower.startsWith('ls ') || lower.startsWith('tree ')) {
    if (!project) return ['sem projeto ativo — selecione um na barra lateral'];
    return [project.name, ...flattenTree(project.files)];
  }

  if (lower === 'status') {
    return [
      'backend ....... online (simulado)',
      `projeto ....... ${project ? project.name : '—'}`,
      `estado ........ ${project?.status ?? 'n/d'}`,
      'uptime ........ 3h 42m',
      'llm ........... auto · pronto',
    ];
  }

  if (lower === 'projects') {
    return (projects ?? MOCK_PROJECTS).map(
      (p) => `${p.status === 'active' ? '●' : p.status === 'error' ? '▲' : '○'} ${p.name} — ${p.status}${p.port ? ` :${p.port}` : ''}`
    );
  }

  if (lower.startsWith('npm ') || lower.startsWith('yarn ') || lower.startsWith('pnpm ') || lower.startsWith('make ')) {
    return [`> ${cmd.trim()}`, '✓ concluído em 1.2s (0 erros)'];
  }

  if (lower.startsWith('git ')) {
    return [`(simulado) ${cmd.trim()}`, '✓ ok'];
  }

  if (lower.startsWith('curl ')) {
    return ['HTTP/1.1 200 OK', 'content-type: application/json', '', '{"status":"ok","demo":true}'];
  }

  if (lower.startsWith('ft ')) {
    return ['▸ ft CLI v1.0.0 (simulação)', `▸ comando: ${cmd.trim()}`, '▸ analisando... ok', '✓ executado'];
  }

  return [`bash: ${cmd.trim()}: comando não encontrado — digite help para ver os comandos`];
}

export function mockHelpLines(): Array<{ kind: TerminalKind; text: string }> {
  return [
    { kind: 'output', text: 'Comandos disponíveis (Shell Ferreira Technology):' },
    { kind: 'output', text: '  help          — lista os comandos' },
    { kind: 'output', text: '  clear         — limpa o terminal' },
    { kind: 'output', text: '  status        — estado do backend e do projeto' },
    { kind: 'output', text: '  ls | tree     — arquivos do projeto ativo' },
    { kind: 'output', text: '  projects      — lista os projetos' },
    { kind: 'output', text: '  connect <url> — aponta o shell para outro backend' },
    { kind: 'output', text: '  chat <msg>    — fala direto com o LLM' },
    { kind: 'output', text: '  ft <cmd>      — CLI do projeto (via POST /api/execute)' },
  ];
}
