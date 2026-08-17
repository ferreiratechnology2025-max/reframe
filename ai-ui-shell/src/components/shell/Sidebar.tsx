import { useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { Cpu, FileJson, Plus, RefreshCw, Search, Settings, Trash2, X } from 'lucide-react';
import { useApp } from '../../state/AppContext';
import { BRAND, hostOf } from '../../config';

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const app = useApp();
  const [query, setQuery] = useState('');
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState('');

  const filtered = useMemo(
    () => app.projects.filter((p) => p.name.toLowerCase().includes(query.toLowerCase())),
    [app.projects, query]
  );

  const statusInfo = {
    connected: {
      dot: 'bg-emerald-400',
      label: 'Backend conectado',
      sub: app.health?.latency != null ? `${app.health.latency} ms` : 'online',
    },
    demo: { dot: 'bg-amber-400', label: 'Modo demo', sub: 'backend simulado' },
    connecting: { dot: 'bg-cyan-400 animate-pulse', label: 'Conectando…', sub: 'testando endpoint' },
    error: { dot: 'bg-rose-400', label: 'Backend offline', sub: 'sem resposta' },
  }[app.status];

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(false);
    await app.createProject(name);
    setName('');
  };

  return (
    <>
      {open && (
        <div className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden" onClick={onClose} />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 w-72 lg:static lg:z-auto flex flex-col shrink-0 bg-[#0d1017] border-r border-white/[0.06] transition-transform duration-300 ${
          open ? 'translate-x-0' : '-translate-x-full'
        } lg:translate-x-0`}
      >
        {/* Marca */}
        <div className="px-4 pt-4 pb-3 border-b border-white/[0.06]">
          <div className="flex items-center gap-3">
            <div
              className={`w-10 h-10 rounded-xl bg-gradient-to-br ${app.accent.gradient} grid place-items-center text-zinc-950 font-extrabold text-lg shadow-lg ${app.accent.glow}`}
            >
              FT
            </div>
            <div className="min-w-0 flex-1">
              <h1 className="text-[15px] font-bold text-white leading-tight">{BRAND.name}</h1>
              <p className="text-[11px] text-zinc-500">
                {BRAND.product} · v{BRAND.version}
              </p>
            </div>
            <button
              className="lg:hidden p-1.5 rounded-md text-zinc-500 hover:text-white hover:bg-white/[0.06]"
              onClick={onClose}
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Status da conexão */}
        <div className="px-4 py-3 border-b border-white/[0.06]">
          <div className="flex items-center gap-2.5">
            <span className="relative flex w-2.5 h-2.5">
              <span
                className={`absolute inline-flex w-full h-full rounded-full opacity-40 animate-ping ${statusInfo.dot}`}
              />
              <span className={`relative inline-flex w-2.5 h-2.5 rounded-full ${statusInfo.dot}`} />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-[12.5px] font-medium text-zinc-200">{statusInfo.label}</p>
              <p className="text-[10.5px] text-zinc-500 truncate font-mono">
                {hostOf(app.settings.apiUrl)} · {statusInfo.sub}
              </p>
            </div>
            <button
              title="Reconectar"
              onClick={() => void app.boot(true)}
              className="p-1.5 rounded-md text-zinc-500 hover:text-white hover:bg-white/[0.06] transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Projetos */}
        <div className="flex-1 min-h-0 flex flex-col px-3 py-3">
          <div className="flex items-center justify-between px-1 mb-2">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
              Projetos
            </p>
            <button
              onClick={() => setCreating((v) => !v)}
              className="p-1 rounded-md text-zinc-500 hover:text-white hover:bg-white/[0.06] transition-colors"
              title="Novo projeto"
            >
              <Plus className="w-3.5 h-3.5" />
            </button>
          </div>

          {creating && (
            <form onSubmit={submit} className="mb-2 space-y-1.5">
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="nome do projeto…"
                autoFocus
                className="w-full rounded-lg border border-white/10 bg-[#12151d] px-2.5 py-1.5 text-[12px] text-zinc-100 outline-none placeholder:text-zinc-600 focus:border-white/20"
              />
              <div className="flex gap-1.5">
                <button
                  type="submit"
                  className={`flex-1 h-7 rounded-md text-[11px] font-medium ${app.accent.solid} transition-colors`}
                >
                  Criar
                </button>
                <button
                  type="button"
                  onClick={() => setCreating(false)}
                  className="flex-1 h-7 rounded-md border border-white/10 text-[11px] text-zinc-400 hover:bg-white/[0.05]"
                >
                  Cancelar
                </button>
              </div>
            </form>
          )}

          <div className="relative mb-2">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-zinc-600" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="buscar…"
              className="w-full rounded-lg border border-white/[0.07] bg-white/[0.03] pl-7 pr-2.5 py-1.5 text-[11.5px] text-zinc-200 outline-none placeholder:text-zinc-600 focus:border-white/15"
            />
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto space-y-0.5 -mx-1 px-1">
            {filtered.map((p) => {
              const active = app.activeProjectId === p.id;
              const dotCls =
                p.status === 'active'
                  ? 'bg-emerald-400'
                  : p.status === 'error'
                    ? 'bg-rose-400'
                    : 'bg-zinc-600';
              return (
                <div
                  key={p.id}
                  onClick={() => app.setActive(p.id)}
                  className={`group flex items-center gap-2.5 px-2.5 py-2 rounded-lg cursor-pointer transition-colors ${
                    active ? 'bg-white/[0.06]' : 'hover:bg-white/[0.04]'
                  }`}
                >
                  <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${dotCls}`} />
                  <div className="min-w-0 flex-1">
                    <p
                      className={`text-[12.5px] truncate ${
                        active ? 'text-white font-medium' : 'text-zinc-300'
                      }`}
                    >
                      {p.name}
                    </p>
                    <p className="text-[10px] text-zinc-600 truncate">
                      {p.framework ?? 'projeto'}
                      {p.port ? ` · :${p.port}` : ''}
                    </p>
                  </div>
                  {p.status === 'active' && (
                    <span className="text-[9px] font-mono uppercase text-emerald-400/80">on</span>
                  )}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      app.deleteProject(p.id);
                    }}
                    title="Remover projeto"
                    className="opacity-0 group-hover:opacity-100 p-1 rounded text-zinc-500 hover:text-rose-400 transition-all"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })}
            {filtered.length === 0 && (
              <p className="text-[11px] text-zinc-600 text-center py-6">nenhum projeto encontrado</p>
            )}
          </div>
        </div>

        {/* Provedores LLM */}
        <div className="px-4 py-3 border-t border-white/[0.06]">
          <div className="flex items-center justify-between mb-2">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
              Provedores LLM
            </p>
            <button
              onClick={() => app.setSettingsOpen(true)}
              className="text-[10px] text-zinc-500 hover:text-zinc-300"
            >
              gerenciar
            </button>
          </div>
          <div className="flex items-center gap-1.5 flex-wrap">
            {app.providers.slice(0, 4).map((pr) => (
              <span
                key={pr.id}
                className={`text-[10px] px-2 py-0.5 rounded-full border ${
                  pr.configured
                    ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                    : 'border-white/10 bg-white/[0.03] text-zinc-500'
                }`}
              >
                {pr.name}
              </span>
            ))}
            {app.providers.length === 0 && (
              <span className="text-[10px] text-zinc-600">
                nenhum provedor — configure no painel
              </span>
            )}
          </div>
        </div>

        {/* Rodapé */}
        <div className="px-3 py-2.5 border-t border-white/[0.06] space-y-0.5">
          <button
            onClick={() => app.setSettingsOpen(true)}
            className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-[12.5px] text-zinc-400 hover:text-white hover:bg-white/[0.05] transition-colors"
          >
            <Settings className="w-4 h-4" /> Configurações & Conexão
          </button>
          <button
            onClick={() => app.setSettingsOpen(true)}
            className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-[12.5px] text-zinc-400 hover:text-white hover:bg-white/[0.05] transition-colors"
          >
            <FileJson className="w-4 h-4" /> Contrato de API (REST/SSE)
          </button>
          <div className="flex items-center gap-2 px-2.5 py-1.5">
            <Cpu className="w-3.5 h-3.5 text-zinc-600" />
            <span className="text-[10.5px] font-mono text-zinc-600 truncate">
              LLM: {app.settings.model}
            </span>
          </div>
        </div>
      </aside>
    </>
  );
}
