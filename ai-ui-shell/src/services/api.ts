// ─────────────────────────────────────────────────────────────
// Ferreira Technology — Shell Universal
// Cliente REST/SSE agnóstico de backend.
// Basta apontar VITE_API_URL (ou Configurações) e remapear os
// caminhos — as respostas são normalizadas por adaptadores.
// ─────────────────────────────────────────────────────────────

import type { FileNode, Project, ProjectStatus, ProviderInfo, Settings } from '../types';

export function buildUrl(apiUrl: string, path: string): string {
  return `${apiUrl.replace(/\/+$/, '')}/${path.replace(/^\/+/, '')}`;
}

export function resolvePath(template: string, params: Record<string, string>): string {
  return template.replace(/\{(\w+)\}/g, (_, k: string) => params[k] ?? '');
}

function authHeaders(token?: string): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function jsonFetch(url: string, init: RequestInit = {}, token?: string): Promise<any> {
  const res = await fetch(url, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(token),
      ...(init.headers ?? {}),
    },
  });
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body?.message || body?.error) msg = typeof body.message === 'string' ? body.message : String(body.error);
    } catch {
      /* corpo não-JSON */
    }
    throw new Error(msg);
  }
  const ct = res.headers.get('content-type') ?? '';
  return ct.includes('application/json') ? res.json() : res.text();
}

// ───────────────────────── Health ─────────────────────────

export async function checkHealth(
  settings: Settings
): Promise<{ ok: boolean; latency?: number; data?: unknown }> {
  const start = performance.now();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 4000);
  try {
    const res = await fetch(buildUrl(settings.apiUrl, settings.endpoints.health), {
      signal: controller.signal,
      headers: authHeaders(settings.apiToken),
    });
    const latency = Math.round(performance.now() - start);
    return { ok: res.ok, latency, data: res.ok ? await res.json().catch(() => null) : undefined };
  } catch {
    return { ok: false, latency: Math.round(performance.now() - start) };
  } finally {
    clearTimeout(timer);
  }
}

// ───────────────────────── Projetos ─────────────────────────

export async function getProjects(settings: Settings): Promise<any[]> {
  const data = await jsonFetch(buildUrl(settings.apiUrl, settings.endpoints.projects), {}, settings.apiToken);
  return Array.isArray(data) ? data : data?.projects ?? data?.data ?? [];
}

export async function createProject(settings: Settings, name: string): Promise<unknown> {
  return jsonFetch(
    buildUrl(settings.apiUrl, settings.endpoints.projectCreate),
    { method: 'POST', body: JSON.stringify({ name }) },
    settings.apiToken
  );
}

export async function deleteProject(settings: Settings, id: string): Promise<void> {
  await jsonFetch(
    buildUrl(settings.apiUrl, resolvePath(settings.endpoints.projectDelete, { id })),
    { method: 'DELETE' },
    settings.apiToken
  );
}

export async function startProject(settings: Settings, id: string): Promise<void> {
  await jsonFetch(
    buildUrl(settings.apiUrl, resolvePath(settings.endpoints.projectStart, { id })),
    { method: 'POST', body: JSON.stringify({}) },
    settings.apiToken
  );
}

export async function stopProject(settings: Settings, id: string): Promise<void> {
  await jsonFetch(
    buildUrl(settings.apiUrl, resolvePath(settings.endpoints.projectStop, { id })),
    { method: 'POST', body: JSON.stringify({}) },
    settings.apiToken
  );
}

// ───────────────────────── Chat (SSE) ─────────────────────────

export interface StreamHandlers {
  onChunk: (text: string) => void;
  onDone?: (fullText: string) => void;
  signal?: AbortSignal;
}

export async function streamChat(
  settings: Settings,
  payload: { prompt: string; projectId?: string; model: string },
  handlers: StreamHandlers
): Promise<string> {
  const res = await fetch(buildUrl(settings.apiUrl, settings.endpoints.chat), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(settings.apiToken),
    },
    body: JSON.stringify({
      prompt: payload.prompt,
      projectId: payload.projectId,
      model: payload.model,
    }),
    signal: handlers.signal,
  });

  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body?.message || body?.error) msg = typeof body.message === 'string' ? body.message : String(body.error);
    } catch {
      /* ignore */
    }
    throw new Error(msg);
  }

  // Resposta JSON simples (sem SSE): usa o campo de conteúdo direto
  const ct = res.headers.get('content-type') ?? '';
  if (ct.includes('application/json')) {
    const body = await res.json().catch(() => null);
    const text = String(body?.content ?? body?.reply ?? body?.message ?? body?.text ?? '');
    handlers.onChunk(text);
    handlers.onDone?.(text);
    return text;
  }

  return parseSSE(res, handlers);
}

async function parseSSE(res: Response, handlers: StreamHandlers): Promise<string> {
  const reader = res.body?.getReader();
  const decoder = new TextDecoder();
  let full = '';
  let buffer = '';

  if (!reader) {
    const text = await res.text();
    handlers.onChunk(text);
    handlers.onDone?.(text);
    return text;
  }

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';

    for (const raw of lines) {
      const line = raw.trim();
      if (!line) continue;

      if (line.startsWith('data:')) {
        const payload = line.slice(5).trim();
        if (payload === '[DONE]') {
          handlers.onDone?.(full);
          return full;
        }
        try {
          const json = JSON.parse(payload);
          const content = json.content ?? json.delta ?? json.text ?? json.message ?? '';
          if (typeof content === 'string' && content) {
            full += content;
            handlers.onChunk(content);
          }
          if (json.done || json.finished) {
            handlers.onDone?.(full);
            return full;
          }
        } catch {
          full += payload;
          handlers.onChunk(payload);
        }
      } else if (!line.startsWith('event:') && !line.startsWith('id:') && !line.startsWith(':')) {
        full += line + '\n';
        handlers.onChunk(line + '\n');
      }
    }
  }

  handlers.onDone?.(full);
  return full;
}

// ───────────────────── Execute CLI (SSE) ─────────────────────

export async function streamExecute(
  settings: Settings,
  payload: { projectId?: string; command: string },
  handlers: { onChunk: (text: string) => void }
): Promise<void> {
  const res = await fetch(buildUrl(settings.apiUrl, settings.endpoints.execute), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(settings.apiToken),
    },
    body: JSON.stringify({ projectId: payload.projectId, command: payload.command }),
  });

  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body?.message || body?.error) msg = typeof body.message === 'string' ? body.message : String(body.error);
    } catch {
      /* ignore */
    }
    throw new Error(msg);
  }

  const reader = res.body?.getReader();
  if (!reader) return;
  const decoder = new TextDecoder();
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    handlers.onChunk(decoder.decode(value, { stream: true }));
  }
}

// ───────────────────────── Provedores ─────────────────────────

export async function getProviders(settings: Settings): Promise<any[]> {
  const data = await jsonFetch(
    buildUrl(settings.apiUrl, settings.endpoints.providerStatus),
    {},
    settings.apiToken
  );
  if (Array.isArray(data)) return data;
  if (data && typeof data === 'object') return Object.values(data);
  return [];
}

export async function configureProvider(settings: Settings, providerId: string, apiKey: string): Promise<void> {
  await jsonFetch(
    buildUrl(settings.apiUrl, resolvePath(settings.endpoints.providerConfigure, { id: providerId })),
    { method: 'POST', body: JSON.stringify({ apiKey }) },
    settings.apiToken
  );
}

// ───────────────────────── Adaptadores ─────────────────────────
// Normalizam QUALQUER formato de resposta do backend para o
// formato interno da UI (com fallbacks). É aqui que você ajusta
// campos caso o seu backend use outra nomenclatura.

export function adaptProject(raw: any): Project {
  const status: ProjectStatus =
    raw?.status === 'active' || raw?.status === 'stopped' || raw?.status === 'error'
      ? raw.status
      : raw?.running === true
        ? 'active'
        : 'stopped';
  return {
    id: String(raw?.id ?? raw?._id ?? raw?.uuid ?? `p-${Math.random().toString(36).slice(2, 8)}`),
    name: String(raw?.name ?? raw?.title ?? 'projeto'),
    description: raw?.description != null ? String(raw.description) : undefined,
    status,
    framework: raw?.framework != null ? String(raw.framework) : undefined,
    port: typeof raw?.port === 'number' ? raw.port : undefined,
    url: raw?.url != null ? String(raw.url) : undefined,
    createdAt: String(raw?.createdAt ?? raw?.created_at ?? new Date().toISOString().slice(0, 10)),
    files: normalizeFiles(raw?.files ?? raw?.fileTree ?? raw?.tree),
  };
}

export function adaptProvider(raw: any): ProviderInfo {
  const id = String(raw?.id ?? raw?.provider ?? raw?.name ?? 'unknown');
  return {
    id,
    name: String(raw?.name ?? id),
    configured: Boolean(raw?.configured ?? raw?.ok ?? false),
  };
}

function normalizeFiles(raw: unknown): FileNode[] {
  if (!Array.isArray(raw)) return [];
  const hasPaths = raw.some((it: any) => it && typeof it.path === 'string');
  if (hasPaths) return buildTree(raw.map((it: any) => it.path as string));
  return raw.map((item: any): FileNode => ({
    name: String(item?.name ?? 'arquivo'),
    type: item?.type === 'dir' || item?.type === 'directory' || Array.isArray(item?.children) ? 'dir' : 'file',
    children: Array.isArray(item?.children) ? normalizeFiles(item.children) : undefined,
    size: item?.size != null ? String(item.size) : undefined,
  }));
}

function buildTree(paths: string[]): FileNode[] {
  const root: FileNode[] = [];
  for (const p of paths) {
    const parts = p.split('/').filter(Boolean);
    if (!parts.length) continue;
    let level = root;
    parts.forEach((part, i) => {
      const isFile = i === parts.length - 1 && !p.endsWith('/');
      let node = level.find((n) => n.name === part);
      if (!node) {
        node = { name: part, type: isFile ? 'file' : 'dir', children: isFile ? undefined : [] };
        level.push(node);
      }
      if (!isFile) level = node.children ?? (node.children = []);
    });
  }
  return root;
}
