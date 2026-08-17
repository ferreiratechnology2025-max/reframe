import type { AccentKey, EndpointMap, Settings } from './types';

// ─────────────────────────────────────────────────────────────
// Marca
// ─────────────────────────────────────────────────────────────

export const BRAND = {
  name: 'Ferreira Technology',
  short: 'FT',
  product: 'Shell Universal',
  tagline: 'Interface universal para backends CLI via REST/SSE',
  version: '1.0.0',
};

export function hostOf(url: string): string {
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
}

// ─────────────────────────────────────────────────────────────
// Contrato de endpoints (remapável — a UI é agnóstica de backend)
// ─────────────────────────────────────────────────────────────

export const DEFAULT_ENDPOINTS: EndpointMap = {
  health: '/health',
  projects: '/api/projects',
  projectCreate: '/api/projects',
  projectDelete: '/api/projects/{id}',
  projectStart: '/api/projects/{id}/start',
  projectStop: '/api/projects/{id}/stop',
  chat: '/api/chat',
  execute: '/api/execute',
  providerStatus: '/api/providers/status',
  providerConfigure: '/api/providers/{id}/configure',
};

export interface EndpointDoc {
  key: keyof EndpointMap;
  method: 'GET' | 'POST' | 'DELETE';
  description: string;
}

export const ENDPOINT_DOCS: EndpointDoc[] = [
  { key: 'health', method: 'GET', description: 'Health check do backend' },
  { key: 'projects', method: 'GET', description: 'Lista os projetos' },
  { key: 'projectCreate', method: 'POST', description: 'Cria projeto · body { name }' },
  { key: 'projectDelete', method: 'DELETE', description: 'Remove projeto · {id}' },
  { key: 'projectStart', method: 'POST', description: 'Inicia projeto · {id}' },
  { key: 'projectStop', method: 'POST', description: 'Para projeto · {id}' },
  { key: 'chat', method: 'POST', description: 'Chat com LLM (SSE) · body { prompt, projectId?, model }' },
  { key: 'execute', method: 'POST', description: 'Executa comando CLI (SSE) · body { projectId?, command }' },
  { key: 'providerStatus', method: 'GET', description: 'Status dos provedores LLM' },
  { key: 'providerConfigure', method: 'POST', description: 'Configura provedor · {id} · body { apiKey }' },
];

export const SSE_FORMAT_DOC = [
  'Formato do streaming (SSE — text/event-stream):',
  '',
  'POST /chat',
  '  data: {"content":"olá"}',
  '  data: {"content":" mundo"}',
  '  data: [DONE]',
  '',
  'POST /execute',
  '  chunks de texto bruto (stdout da CLI)',
  '',
  'Auth opcional: Authorization: Bearer <token>',
].join('\n');

// ─────────────────────────────────────────────────────────────
// Configuração padrão
// ─────────────────────────────────────────────────────────────

export const DEFAULT_SETTINGS: Settings = {
  apiUrl: 'http://localhost:4000',
  apiToken: '',
  model: 'auto',
  models: ['auto', 'sonnet-4', 'gpt-4o', 'deepseek-v3'],
  endpoints: DEFAULT_ENDPOINTS,
  accent: 'emerald',
  username: 'dev@ferreira.tech',
};

// ─────────────────────────────────────────────────────────────
// Temas de destaque (classes estáticas para o Tailwind v4)
// ─────────────────────────────────────────────────────────────

export interface AccentTheme {
  key: AccentKey;
  label: string;
  hex: string;
  dot: string;
  solid: string;
  soft: string;
  text: string;
  border: string;
  gradient: string;
  chip: string;
  glow: string;
  ring: string;
}

export const ACCENTS: Record<AccentKey, AccentTheme> = {
  emerald: {
    key: 'emerald',
    label: 'Esmeralda',
    hex: '#34d399',
    dot: 'bg-emerald-400',
    solid: 'bg-emerald-500 hover:bg-emerald-400 text-zinc-950',
    soft: 'bg-emerald-500/10 text-emerald-300',
    text: 'text-emerald-400',
    border: 'border-emerald-500/40',
    gradient: 'from-emerald-400 to-teal-300',
    chip: 'border border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
    glow: 'shadow-emerald-500/25',
    ring: 'focus-within:border-emerald-500/60 focus-within:ring-emerald-500/20',
  },
  cyan: {
    key: 'cyan',
    label: 'Ciano',
    hex: '#22d3ee',
    dot: 'bg-cyan-400',
    solid: 'bg-cyan-500 hover:bg-cyan-400 text-zinc-950',
    soft: 'bg-cyan-500/10 text-cyan-300',
    text: 'text-cyan-400',
    border: 'border-cyan-500/40',
    gradient: 'from-cyan-400 to-blue-400',
    chip: 'border border-cyan-500/30 bg-cyan-500/10 text-cyan-300',
    glow: 'shadow-cyan-500/25',
    ring: 'focus-within:border-cyan-500/60 focus-within:ring-cyan-500/20',
  },
  violet: {
    key: 'violet',
    label: 'Violeta',
    hex: '#a78bfa',
    dot: 'bg-violet-400',
    solid: 'bg-violet-500 hover:bg-violet-400 text-zinc-950',
    soft: 'bg-violet-500/10 text-violet-300',
    text: 'text-violet-400',
    border: 'border-violet-500/40',
    gradient: 'from-violet-400 to-fuchsia-400',
    chip: 'border border-violet-500/30 bg-violet-500/10 text-violet-300',
    glow: 'shadow-violet-500/25',
    ring: 'focus-within:border-violet-500/60 focus-within:ring-violet-500/20',
  },
  orange: {
    key: 'orange',
    label: 'Laranja',
    hex: '#fb923c',
    dot: 'bg-orange-400',
    solid: 'bg-orange-500 hover:bg-orange-400 text-zinc-950',
    soft: 'bg-orange-500/10 text-orange-300',
    text: 'text-orange-400',
    border: 'border-orange-500/40',
    gradient: 'from-orange-400 to-amber-300',
    chip: 'border border-orange-500/30 bg-orange-500/10 text-orange-300',
    glow: 'shadow-orange-500/25',
    ring: 'focus-within:border-orange-500/60 focus-within:ring-orange-500/20',
  },
  rose: {
    key: 'rose',
    label: 'Rosa',
    hex: '#fb7185',
    dot: 'bg-rose-400',
    solid: 'bg-rose-500 hover:bg-rose-400 text-white',
    soft: 'bg-rose-500/10 text-rose-300',
    text: 'text-rose-400',
    border: 'border-rose-500/40',
    gradient: 'from-rose-400 to-pink-400',
    chip: 'border border-rose-500/30 bg-rose-500/10 text-rose-300',
    glow: 'shadow-rose-500/25',
    ring: 'focus-within:border-rose-500/60 focus-within:ring-rose-500/20',
  },
};
