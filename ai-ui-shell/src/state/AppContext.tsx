// ─────────────────────────────────────────────────────────────
// Ferreira Technology — Shell Universal
// Estado global: conexão com o backend, projetos, chat (SSE),
// terminal e configurações persistidas em localStorage.
// ─────────────────────────────────────────────────────────────

import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import * as api from '../services/api';
import * as mock from '../services/mock';
import { ACCENTS, DEFAULT_SETTINGS } from '../config';
import type { AccentTheme } from '../config';
import type {
  BackendStatus,
  ChatMessage,
  HealthInfo,
  Project,
  ProjectStatus,
  ProviderInfo,
  Settings,
  TerminalKind,
  TerminalLine,
} from '../types';

const LS_SETTINGS = 'ft-shell.settings.v1';

interface AppContextValue {
  settings: Settings;
  updateSettings: (patch: Partial<Settings>) => void;
  resetSettings: () => void;
  status: BackendStatus;
  health: HealthInfo | null;
  projects: Project[];
  activeProjectId: string | null;
  setActive: (id: string | null) => void;
  openTabs: string[];
  closeTab: (id: string) => void;
  messages: Record<string, ChatMessage[]>;
  isStreaming: boolean;
  sendChat: (prompt: string) => Promise<void>;
  stopChat: () => void;
  clearChat: () => void;
  terminal: TerminalLine[];
  runCommand: (cmd: string) => void;
  clearTerminal: () => void;
  providers: ProviderInfo[];
  settingsOpen: boolean;
  setSettingsOpen: (v: boolean) => void;
  createProject: (name: string) => Promise<void>;
  deleteProject: (id: string) => void;
  toggleProject: (id: string) => void;
  testConnection: () => Promise<boolean>;
  boot: (force?: boolean) => Promise<void>;
  accent: AccentTheme;
}

const AppContext = createContext<AppContextValue | null>(null);

function loadSettings(): Settings {
  try {
    const raw = localStorage.getItem(LS_SETTINGS);
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<Settings>;
      return {
        ...DEFAULT_SETTINGS,
        ...parsed,
        endpoints: { ...DEFAULT_SETTINGS.endpoints, ...(parsed.endpoints ?? {}) },
        models: Array.isArray(parsed.models) && parsed.models.length ? parsed.models : DEFAULT_SETTINGS.models,
      };
    }
  } catch {
    /* ignore */
  }
  return DEFAULT_SETTINGS;
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<Settings>(loadSettings);
  const [status, setStatus] = useState<BackendStatus>('connecting');
  const [health, setHealth] = useState<HealthInfo | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  const [openTabs, setOpenTabs] = useState<string[]>([]);
  const [messages, setMessages] = useState<Record<string, ChatMessage[]>>({});
  const [isStreaming, setIsStreaming] = useState(false);
  const [terminal, setTerminal] = useState<TerminalLine[]>([]);
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const idRef = useRef(100);
  const abortRef = useRef<AbortController | null>(null);
  const statusRef = useRef<BackendStatus>('connecting');
  const activeRef = useRef<string | null>(null);
  const projectsRef = useRef<Project[]>([]);
  const settingsRef = useRef(settings);
  const isStreamingRef = useRef(false);
  const lastUrlRef = useRef('');
  const lastTokenRef = useRef('');

  useEffect(() => {
    settingsRef.current = settings;
  }, [settings]);

  useEffect(() => {
    try {
      localStorage.setItem(LS_SETTINGS, JSON.stringify(settings));
    } catch {
      /* ignore */
    }
  }, [settings]);

  const updateSettings = useCallback((patch: Partial<Settings>) => {
    setSettings((prev) => {
      const next = { ...prev, ...patch };
      settingsRef.current = next; // mantém o ref síncrono p/ comandos imediatos (connect, test)
      return next;
    });
  }, []);

  const resetSettings = useCallback(() => {
    try {
      localStorage.removeItem(LS_SETTINGS);
    } catch {
      /* ignore */
    }
    setSettings(DEFAULT_SETTINGS);
  }, []);

  const pushTerminal = useCallback((lines: Array<{ kind: TerminalKind; text: string }>) => {
    setTerminal((t) => [
      ...t,
      ...lines.map((l) => ({ id: idRef.current++, kind: l.kind, text: l.text, ts: Date.now() })),
    ]);
  }, []);

  const setActive = useCallback((id: string | null) => {
    activeRef.current = id;
    setActiveProjectId(id);
    if (id) setOpenTabs((t) => (t.includes(id) ? t : [...t, id]));
  }, []);

  const closeTab = useCallback(
    (id: string) => {
      setOpenTabs((t) => t.filter((x) => x !== id));
      if (activeRef.current === id) {
        const next = projectsRef.current.find((p) => p.id !== id);
        setActive(next?.id ?? null);
      }
    },
    [setActive]
  );

  // ───────────────────────── Boot / conexão ─────────────────────────

  const boot = useCallback(
    async (force = false) => {
      if (isStreamingRef.current) return;
      // Evita re-check a cada 30s no modo demo quando nada mudou
      if (
        !force &&
        statusRef.current === 'demo' &&
        settingsRef.current.apiUrl === lastUrlRef.current &&
        settingsRef.current.apiToken === lastTokenRef.current
      ) {
        return;
      }
      lastUrlRef.current = settingsRef.current.apiUrl;
      lastTokenRef.current = settingsRef.current.apiToken;
      setStatus('connecting');
      const result = await api.checkHealth(settingsRef.current);

    if (result.ok) {
      statusRef.current = 'connected';
      setStatus('connected');
      setHealth(result);
      try {
        const raw = await api.getProjects(settingsRef.current);
        const list = (raw ?? []).map((p: unknown) => api.adaptProject(p));
        setProjects(list);
        projectsRef.current = list;
        if (list.length && !activeRef.current) setActive(list[0].id);
        if (activeRef.current && list.length && !list.some((p) => p.id === activeRef.current)) {
          setActive(list[0].id);
        }
      } catch {
        /* mantém projetos atuais */
      }
      try {
        const raw = await api.getProviders(settingsRef.current);
        setProviders(raw.map((p: unknown) => api.adaptProvider(p)));
      } catch {
        /* ignore */
      }
    } else {
      statusRef.current = 'demo';
      setStatus('demo');
      setHealth(null);
      if (!projectsRef.current.length) {
        const list = await mock.getMockProjects();
        setProjects(list);
        projectsRef.current = list;
        if (!activeRef.current) setActive(list[0]?.id ?? null);
      }
      setProviders(mock.getMockProviders());
    }
  }, [setActive]);

  useEffect(() => {
    void boot();
    const timer = setInterval(() => void boot(), 30000);
    return () => clearInterval(timer);
  }, [boot]);

  const testConnection = useCallback(async (): Promise<boolean> => {
    const result = await api.checkHealth(settingsRef.current);
    if (result.ok) {
      statusRef.current = 'connected';
      setStatus('connected');
      setHealth(result);
      try {
        const raw = await api.getProjects(settingsRef.current);
        const list = (raw ?? []).map((p: unknown) => api.adaptProject(p));
        if (list.length) {
          setProjects(list);
          projectsRef.current = list;
          if (!list.some((x) => x.id === activeRef.current)) setActive(list[0].id);
        }
      } catch {
        /* ignore */
      }
      try {
        const raw = await api.getProviders(settingsRef.current);
        setProviders(raw.map((p: unknown) => api.adaptProvider(p)));
      } catch {
        /* ignore */
      }
      return true;
    }
    statusRef.current = 'demo';
    setStatus('demo');
    setHealth(null);
    if (!projectsRef.current.length) {
      const list = await mock.getMockProjects();
      setProjects(list);
      projectsRef.current = list;
      if (!activeRef.current) setActive(list[0]?.id ?? null);
    }
    return false;
  }, [setActive]);

  // ───────────────────────── Projetos ─────────────────────────

  const createProject = useCallback(
    async (name: string) => {
      const clean = name.trim();
      if (!clean) return;
      try {
        if (statusRef.current === 'connected') {
          await api.createProject(settingsRef.current, clean);
          await boot();
        } else {
          const proj: Project = {
            id: `demo-${Date.now()}`,
            name: clean,
            description: 'Projeto criado no modo demo (simulado).',
            status: 'stopped',
            framework: '—',
            createdAt: new Date().toISOString().slice(0, 10),
            files: [
              { name: 'src', type: 'dir', children: [{ name: 'index.ts', type: 'file', size: '0.4 KB' }] },
              { name: 'package.json', type: 'file', size: '0.3 KB' },
              { name: 'README.md', type: 'file', size: '0.1 KB' },
            ],
          };
          setProjects((prev) => [proj, ...prev]);
          projectsRef.current = [proj, ...projectsRef.current];
          pushTerminal([{ kind: 'success', text: `✓ projeto ${clean} criado (simulado)` }]);
          setActive(proj.id);
        }
      } catch (err) {
        pushTerminal([
          { kind: 'error', text: `falha ao criar projeto: ${err instanceof Error ? err.message : 'erro'}` },
        ]);
      }
    },
    [boot, pushTerminal, setActive]
  );

  const deleteProject = useCallback(
    (id: string) => {
      if (!window.confirm('Remover este projeto?')) return;
      void (async () => {
        if (statusRef.current === 'connected') {
          try {
            await api.deleteProject(settingsRef.current, id);
          } catch (err) {
            pushTerminal([
              { kind: 'error', text: `falha ao remover: ${err instanceof Error ? err.message : 'erro'}` },
            ]);
            return;
          }
        }
        setProjects((prev) => prev.filter((p) => p.id !== id));
        projectsRef.current = projectsRef.current.filter((p) => p.id !== id);
        setOpenTabs((t) => t.filter((x) => x !== id));
        setMessages((prev) => {
          const next = { ...prev };
          delete next[id];
          return next;
        });
        if (activeRef.current === id) {
          setActive(projectsRef.current[0]?.id ?? null);
        }
        pushTerminal([{ kind: 'info', text: `projeto ${id} removido` }]);
      })();
    },
    [pushTerminal, setActive]
  );

  const patchProjectStatus = useCallback((id: string, nextStatus: ProjectStatus) => {
    setProjects((prev) => prev.map((p) => (p.id === id ? { ...p, status: nextStatus } : p)));
    projectsRef.current = projectsRef.current.map((p) =>
      p.id === id ? { ...p, status: nextStatus } : p
    );
  }, []);

  const toggleProject = useCallback(
    (id: string) => {
      void (async () => {
        try {
          if (statusRef.current === 'connected') {
            const proj = projectsRef.current.find((p) => p.id === id);
            if (proj?.status === 'active') await api.stopProject(settingsRef.current, id);
            else await api.startProject(settingsRef.current, id);
            const raw = await api.getProjects(settingsRef.current);
            const list = (raw ?? []).map((p: unknown) => api.adaptProject(p));
            setProjects(list);
            projectsRef.current = list;
          } else {
            const proj = projectsRef.current.find((p) => p.id === id);
            const next: ProjectStatus = proj?.status === 'active' ? 'stopped' : 'active';
            patchProjectStatus(id, next);
            pushTerminal([{ kind: 'info', text: `projeto ${id}: ${next} (simulado)` }]);
          }
        } catch (err) {
          pushTerminal([
            { kind: 'error', text: `falha: ${err instanceof Error ? err.message : 'erro'}` },
          ]);
        }
      })();
    },
    [patchProjectStatus, pushTerminal]
  );

  // ───────────────────────── Chat ─────────────────────────

  const clearChat = useCallback(() => {
    const key = activeRef.current ?? 'global';
    setMessages((prev) => {
      const next = { ...prev };
      next[key] = [];
      return next;
    });
  }, []);

  const stopChat = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const sendChat = useCallback(
    async (prompt: string) => {
      if (!prompt.trim() || isStreamingRef.current) return;
      const pid = activeRef.current;
      const key = pid ?? 'global';
      const uid = `u-${idRef.current++}`;
      const aid = `a-${idRef.current++}`;

      const userMsg: ChatMessage = { id: uid, role: 'user', content: prompt, timestamp: Date.now() };
      const assistantMsg: ChatMessage = {
        id: aid,
        role: 'assistant',
        content: '',
        timestamp: Date.now(),
        pending: true,
      };
      setMessages((m) => ({ ...m, [key]: [...(m[key] ?? []), userMsg, assistantMsg] }));

      setIsStreaming(true);
      isStreamingRef.current = true;
      const controller = new AbortController();
      abortRef.current = controller;

      const patch = (content: string, extra?: Partial<ChatMessage>) =>
        setMessages((m) => {
          const list = m[key] ?? [];
          return {
            ...m,
            [key]: list.map((msg) => (msg.id === aid ? { ...msg, content, ...extra } : msg)),
          };
        });

      let full = '';
      const onChunk = (t: string) => {
        full += t;
        patch(full, { pending: false });
      };

      const project = projectsRef.current.find((p) => p.id === pid);

      try {
        if (statusRef.current === 'connected') {
          await api.streamChat(
            settingsRef.current,
            { prompt, projectId: pid ?? undefined, model: settingsRef.current.model },
            { onChunk, signal: controller.signal }
          );
        } else {
          await mock.mockStreamChat(
            { prompt, projectName: project?.name, model: settingsRef.current.model },
            { onChunk, signal: controller.signal }
          );
        }
        patch(full, { pending: false });
        if (controller.signal.aborted) {
          pushTerminal([{ kind: 'info', text: '→ fluxo interrompido pelo usuário' }]);
        } else if (statusRef.current !== 'connected') {
          pushTerminal([
            { kind: 'system', text: `$ ft exec --project ${project?.name ?? 'global'}` },
            { kind: 'output', text: '▸ aplicando plano... ok' },
            { kind: 'success', text: '✓ concluído (simulado)' },
          ]);
        }
      } catch (err) {
        if (controller.signal.aborted) {
          patch(full, { pending: false });
          pushTerminal([{ kind: 'info', text: '→ fluxo interrompido pelo usuário' }]);
        } else {
          const msg = err instanceof Error ? err.message : 'erro desconhecido';
          if (!full) patch(`**Erro:** ${msg}`, { pending: false, error: true });
          else patch(full, { pending: false });
          pushTerminal([{ kind: 'error', text: `[llm] ${msg}` }]);
        }
      } finally {
        setIsStreaming(false);
        isStreamingRef.current = false;
        abortRef.current = null;
      }
    },
    [pushTerminal]
  );

  // ───────────────────────── Terminal ─────────────────────────

  const clearTerminal = useCallback(() => setTerminal([]), []);

  const runCommand = useCallback(
    (cmdRaw: string) => {
      const cmd = cmdRaw.trim();
      if (!cmd) return;
      const lower = cmd.toLowerCase();

      setTerminal((t) => [
        ...t,
        { id: idRef.current++, kind: 'input', text: cmd, ts: Date.now() },
      ]);

      void (async () => {
        if (lower === 'clear' || lower === 'cls') {
          setTerminal([]);
          return;
        }
        if (lower === 'help' || lower === 'ajuda') {
          pushTerminal(mock.mockHelpLines());
          return;
        }
        if (lower === 'connect' || lower.startsWith('connect ')) {
          const url = cmd.split(/\s+/)[1];
          if (url) {
            updateSettings({ apiUrl: url });
            pushTerminal([{ kind: 'system', text: `endpoint alterado para ${url} — testando conexão…` }]);
            await boot(true);
            pushTerminal([
              {
                kind: statusRef.current === 'connected' ? 'success' : 'error',
                text:
                  statusRef.current === 'connected'
                    ? '✓ conexão estabelecida'
                    : '✗ backend não respondeu — modo demo ativo',
              },
            ]);
          } else {
            pushTerminal([{ kind: 'info', text: 'uso: connect <http://host:porta>' }]);
          }
          return;
        }
        if (lower.startsWith('chat ')) {
          const msg = cmd.slice(5).trim();
          if (!msg) {
            pushTerminal([{ kind: 'info', text: 'uso: chat <mensagem>' }]);
            return;
          }
          pushTerminal([{ kind: 'info', text: '→ enviando mensagem ao LLM…' }]);
          await sendChat(msg);
          return;
        }

        if (statusRef.current === 'connected') {
          const buf = { s: '' };
          try {
            await api.streamExecute(
              settingsRef.current,
              { projectId: activeRef.current ?? undefined, command: cmd },
              {
                onChunk: (t) => {
                  buf.s += t;
                  const lines = buf.s.split('\n');
                  buf.s = lines.pop() ?? '';
                  if (lines.length) {
                    pushTerminal(lines.map((l) => ({ kind: 'output' as const, text: l })));
                  }
                },
              }
            );
            if (buf.s.trim()) pushTerminal([{ kind: 'output', text: buf.s }]);
          } catch (err) {
            pushTerminal([
              {
                kind: 'error',
                text: `falha ao executar: ${err instanceof Error ? err.message : 'erro'}`,
              },
            ]);
          }
          return;
        }

        // Modo demo — CLI simulada
        const project = projectsRef.current.find((p) => p.id === activeRef.current) ?? null;
        const out = mock.mockExec(cmd, project, projectsRef.current);
        for (const line of out) {
          await mock.delay(35);
          pushTerminal([{ kind: 'output', text: line }]);
        }
      })();
    },
    [boot, pushTerminal, sendChat, updateSettings]
  );

  // Mensagem de boas-vindas no terminal
  useEffect(() => {
    pushTerminal([
      { kind: 'system', text: 'Ferreira Technology Shell v1.0.0 — REST + SSE' },
      { kind: 'info', text: 'digite help para ver os comandos · conecte seu backend em Configurações' },
    ]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const accent = ACCENTS[settings.accent];

  const value: AppContextValue = {
    settings,
    updateSettings,
    resetSettings,
    status,
    health,
    projects,
    activeProjectId,
    setActive,
    openTabs,
    closeTab,
    messages,
    isStreaming,
    sendChat,
    stopChat,
    clearChat,
    terminal,
    runCommand,
    clearTerminal,
    providers,
    settingsOpen,
    setSettingsOpen,
    createProject,
    deleteProject,
    toggleProject,
    testConnection,
    boot,
    accent,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp deve ser usado dentro de <AppProvider>');
  return ctx;
}
