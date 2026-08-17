import { FolderTree, Menu, MessageSquare, Settings, SquareTerminal, X } from 'lucide-react';
import { useApp } from '../../state/AppContext';
import type { ViewKey } from '../../types';

const VIEWS: { key: ViewKey; label: string; icon: typeof MessageSquare }[] = [
  { key: 'chat', label: 'Chat', icon: MessageSquare },
  { key: 'inspector', label: 'Inspetor', icon: FolderTree },
  { key: 'terminal', label: 'Terminal', icon: SquareTerminal },
];

export function TabBar({
  view,
  onViewChange,
  onToggleSidebar,
}: {
  view: ViewKey | null;
  onViewChange: (v: ViewKey) => void;
  onToggleSidebar: () => void;
}) {
  const app = useApp();

  return (
    <header className="h-11 shrink-0 flex items-center gap-1 px-2 border-b border-white/[0.06] bg-[#0d1017]">
      <button
        onClick={onToggleSidebar}
        className="lg:hidden p-1.5 rounded-md text-zinc-400 hover:text-white hover:bg-white/[0.06]"
      >
        <Menu className="w-4 h-4" />
      </button>

      {/* Abas dos projetos abertos */}
      <div className="flex-1 flex items-center gap-1 overflow-x-auto">
        {app.openTabs.map((id) => {
          const p = app.projects.find((x) => x.id === id);
          if (!p) return null;
          const active = app.activeProjectId === id;
          const dotCls =
            p.status === 'active'
              ? 'bg-emerald-400'
              : p.status === 'error'
                ? 'bg-rose-400'
                : 'bg-zinc-600';
          return (
            <div
              key={id}
              onClick={() => app.setActive(id)}
              className={`group flex items-center gap-2 pl-3 pr-1.5 h-8 rounded-lg text-[12px] cursor-pointer select-none transition-colors ${
                active
                  ? 'bg-white/[0.07] text-white'
                  : 'text-zinc-500 hover:text-zinc-200 hover:bg-white/[0.04]'
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${dotCls}`} />
              <span className="max-w-[140px] truncate">{p.name}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  app.closeTab(id);
                }}
                title="Fechar aba"
                className="p-0.5 rounded text-zinc-600 hover:text-zinc-200 opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          );
        })}
        {app.openTabs.length === 0 && (
          <span className="text-[11px] text-zinc-600 px-2">nenhum projeto aberto</span>
        )}
      </div>

      {/* Seletor de views */}
      <div className="flex items-center gap-0.5 bg-white/[0.04] border border-white/[0.06] rounded-lg p-0.5">
        {VIEWS.map((v) => {
          const active = view === v.key;
          const Icon = v.icon;
          return (
            <button
              key={v.key}
              onClick={() => onViewChange(v.key)}
              className={`flex items-center gap-1.5 px-2.5 h-7 rounded-md text-[11.5px] transition-colors ${
                active ? `${app.accent.soft} font-medium` : 'text-zinc-500 hover:text-zinc-200'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">{v.label}</span>
            </button>
          );
        })}
      </div>

      <button
        onClick={() => app.setSettingsOpen(true)}
        className="p-1.5 ml-1 rounded-md text-zinc-500 hover:text-white hover:bg-white/[0.06] transition-colors"
        title="Configurações"
      >
        <Settings className="w-4 h-4" />
      </button>
    </header>
  );
}
