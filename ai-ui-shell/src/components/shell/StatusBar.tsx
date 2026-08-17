import { Zap } from 'lucide-react';
import { useApp } from '../../state/AppContext';
import { BRAND, hostOf } from '../../config';

export function StatusBar() {
  const app = useApp();
  const mode = {
    connected: { cls: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300', label: 'ONLINE' },
    demo: { cls: 'border-amber-500/30 bg-amber-500/10 text-amber-300', label: 'MODO DEMO' },
    connecting: { cls: 'border-cyan-500/30 bg-cyan-500/10 text-cyan-300', label: 'CONECTANDO' },
    error: { cls: 'border-rose-500/30 bg-rose-500/10 text-rose-300', label: 'OFFLINE' },
  }[app.status];

  return (
    <footer className="h-7 shrink-0 flex items-center gap-3 px-3 bg-[#0d1017] border-t border-white/[0.06] text-[10.5px] font-mono text-zinc-500">
      <span className="flex items-center gap-1.5 text-zinc-400">
        <Zap className={`w-3 h-3 ${app.accent.text}`} />
        {BRAND.name} Shell
      </span>
      <span className="hidden sm:inline text-zinc-600">v{BRAND.version}</span>
      <span className="hidden md:inline text-zinc-600">REST + SSE</span>
      <span className="flex-1" />
      <span className="hidden md:inline text-zinc-600">{hostOf(app.settings.apiUrl)}</span>
      <span className={`px-1.5 py-px rounded border ${mode.cls}`}>{mode.label}</span>
      <span className="hidden sm:inline">modelo: {app.settings.model}</span>
      {app.health?.latency != null && (
        <span className="text-emerald-400/80">{app.health.latency} ms</span>
      )}
    </footer>
  );
}
