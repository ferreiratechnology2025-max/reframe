// ─────────────────────────────────────────────────────────────
// Ferreira Technology — Shell Universal
// Tipos compartilhados entre UI, cliente REST/SSE e adaptadores
// ─────────────────────────────────────────────────────────────

export type Role = 'user' | 'assistant';

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  timestamp: number;
  pending?: boolean;
  error?: boolean;
}

export type ProjectStatus = 'active' | 'stopped' | 'error';

export interface FileNode {
  name: string;
  type: 'file' | 'dir';
  children?: FileNode[];
  size?: string;
  modified?: string;
}

export interface Project {
  id: string;
  name: string;
  description?: string;
  status: ProjectStatus;
  framework?: string;
  port?: number;
  url?: string;
  createdAt: string;
  files: FileNode[];
}

export type TerminalKind = 'input' | 'output' | 'error' | 'info' | 'success' | 'system';

export interface TerminalLine {
  id: number;
  kind: TerminalKind;
  text: string;
  ts: number;
}

export type BackendStatus = 'connecting' | 'connected' | 'demo' | 'error';

export type ViewKey = 'chat' | 'inspector' | 'terminal';

export interface EndpointMap {
  health: string;
  projects: string;
  projectCreate: string;
  projectDelete: string;
  projectStart: string;
  projectStop: string;
  chat: string;
  execute: string;
  providerStatus: string;
  providerConfigure: string;
}

export type AccentKey = 'emerald' | 'cyan' | 'violet' | 'orange' | 'rose';

export interface Settings {
  apiUrl: string;
  apiToken: string;
  model: string;
  models: string[];
  endpoints: EndpointMap;
  accent: AccentKey;
  username: string;
}

export interface ProviderInfo {
  id: string;
  name: string;
  configured: boolean;
}

export interface HealthInfo {
  ok: boolean;
  latency?: number;
  data?: unknown;
}
