import { useState } from 'react';
import type { CSSProperties } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { AppProvider, useApp } from './state/AppContext';
import { Sidebar } from './components/shell/Sidebar';
import { TabBar } from './components/shell/TabBar';
import { StatusBar } from './components/shell/StatusBar';
import { SettingsPanel } from './components/shell/SettingsPanel';
import { ChatPanel } from './components/chat/ChatPanel';
import { Inspector } from './components/workspace/Inspector';
import { Terminal } from './components/workspace/Terminal';
import { Leads } from './projects/reframe/pages/Leads';
import { NewLead } from './projects/reframe/pages/NewLead';
import { GenerationTracker } from './projects/reframe/pages/GenerationTracker';
import { Dashboard } from './projects/reframe/pages/Dashboard';
import type { ViewKey } from './types';

function Shell() {
  const app = useApp();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const isReframe =
    location.pathname === '/' ||
    location.pathname.startsWith('/leads') ||
    location.pathname.startsWith('/generation');

  const view: ViewKey = location.pathname.startsWith('/inspector')
    ? 'inspector'
    : location.pathname.startsWith('/terminal')
      ? 'terminal'
      : 'chat';

  const handleViewChange = (v: ViewKey) => {
    navigate(v === 'chat' ? '/chat' : v === 'inspector' ? '/inspector' : '/terminal');
  };

  if (app.status === 'connecting' && app.projects.length === 0) {
    return <BootScreen />;
  }

  return (
    <div
      className="h-screen w-screen flex flex-col overflow-hidden bg-[#0b0d12] text-zinc-200"
      style={{ '--accent': app.accent.hex } as CSSProperties}
    >
      <div className="flex flex-1 min-h-0">
        <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

        <main className="flex-1 flex flex-col min-w-0">
          <TabBar
            view={isReframe ? null : view}
            onViewChange={handleViewChange}
            onToggleSidebar={() => setSidebarOpen((o) => !o)}
          />

          <div className="flex-1 min-h-0 flex">
            <Routes>
              <Route path="/" element={<Leads />} />
              <Route path="/leads" element={<Leads />} />
              <Route path="/leads/new" element={<NewLead />} />
              <Route path="/generation/new" element={<GenerationTracker />} />
              <Route path="/generation/:id" element={<GenerationTracker />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route
                path="/chat"
                element={
                  <>
                    <aside className="hidden xl:flex w-[320px] shrink-0 flex-col min-h-0 border-r border-white/[0.06] bg-[#0d1017]">
                      <Inspector compact />
                    </aside>
                    <ChatPanel />
                  </>
                }
              />
              <Route
                path="/inspector"
                element={
                  <div className="flex-1 min-h-0">
                    <Inspector />
                  </div>
                }
              />
              <Route
                path="/terminal"
                element={
                  <div className="flex-1 min-h-0">
                    <Terminal />
                  </div>
                }
              />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </div>
        </main>
      </div>

      <StatusBar />
      <SettingsPanel open={app.settingsOpen} onClose={() => app.setSettingsOpen(false)} />
    </div>
  );
}

function BootScreen() {
  return (
    <div className="h-screen w-screen flex flex-col items-center justify-center gap-5 bg-[#0b0d12] text-zinc-200">
      <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-emerald-400 to-teal-300 grid place-items-center text-zinc-950 font-extrabold text-2xl shadow-lg shadow-emerald-500/25">
        FT
      </div>
      <div className="text-center">
        <h1 className="text-lg font-semibold">Ferreira Technology Shell</h1>
        <p className="text-sm text-zinc-500 mt-1">Conectando ao backend…</p>
      </div>
      <div className="w-40 h-1 rounded-full bg-white/[0.06] overflow-hidden">
        <div className="h-full w-1/2 rounded-full bg-emerald-400 animate-[ft-loading_1s_ease-in-out_infinite]" />
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <Shell />
      </BrowserRouter>
    </AppProvider>
  );
}