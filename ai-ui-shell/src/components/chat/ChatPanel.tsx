import { useEffect, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import { Activity, Bot, Boxes, FileJson, FolderTree, RotateCcw, Send, Square } from 'lucide-react';
import { useApp } from '../../state/AppContext';
import { Markdown } from '../Markdown';
import type { AccentTheme } from '../../config';
import type { ChatMessage } from '../../types';

const SUGGESTIONS = [
  { icon: Boxes, label: 'Criar um novo microserviço com endpoints REST' },
  { icon: FolderTree, label: 'Listar os arquivos do projeto ativo' },
  { icon: Activity, label: 'Ver o status do backend' },
  { icon: FileJson, label: 'Mostrar o contrato de API esperado' },
];

export function ChatPanel() {
  const app = useApp();
  const key = app.activeProjectId ?? 'global';
  const messages = app.messages[key] ?? [];
  const project = app.projects.find((p) => p.id === app.activeProjectId) ?? null;
  const [value, setValue] = useState('');
  const taRef = useRef<HTMLTextAreaElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, app.isStreaming]);

  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`;
  }, [value]);

  const submit = () => {
    const text = value.trim();
    if (!text || app.isStreaming) return;
    setValue('');
    void app.sendChat(text);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <section className="flex-1 min-w-0 flex flex-col min-h-0">
      <div ref={scrollRef} className="flex-1 min-h-0 overflow-y-auto">
        {messages.length === 0 ? (
          <EmptyState onPick={(t) => void app.sendChat(t)} accent={app.accent} />
        ) : (
          <div className="max-w-3xl mx-auto px-4 md:px-6 py-6 space-y-7">
            {messages.map((m, idx) => (
              <MessageRow
                key={m.id}
                msg={m}
                accent={app.accent}
                streaming={
                  app.isStreaming && idx === messages.length - 1 && m.role === 'assistant'
                }
              />
            ))}
          </div>
        )}
      </div>

      {/* Entrada */}
      <div className="shrink-0 border-t border-white/[0.06] bg-[#0d1017] px-4 pb-3 pt-2.5">
        <div className="max-w-3xl mx-auto">
          <div className="flex items-center gap-1.5 mb-2 flex-wrap">
            <span className="text-[10px] uppercase tracking-widest text-zinc-600 font-semibold mr-1">
              Modelo
            </span>
            {app.settings.models.map((m) => (
              <button
                key={m}
                onClick={() => app.updateSettings({ model: m })}
                className={`px-2.5 h-6 rounded-md text-[11px] font-mono transition-colors ${
                  app.settings.model === m
                    ? app.accent.chip
                    : 'text-zinc-500 hover:text-zinc-200 hover:bg-white/[0.05]'
                }`}
              >
                {m}
              </button>
            ))}
            <span className="flex-1" />
            {app.isStreaming && (
              <button
                onClick={app.stopChat}
                className="flex items-center gap-1.5 px-2.5 h-6 rounded-md text-[11px] border border-rose-500/30 bg-rose-500/10 text-rose-300 hover:bg-rose-500/20 transition-colors"
              >
                <Square className="w-3 h-3" /> Interromper
              </button>
            )}
            {messages.length > 0 && !app.isStreaming && (
              <button
                onClick={app.clearChat}
                title="Limpar conversa"
                className="p-1.5 rounded-md text-zinc-500 hover:text-zinc-200 hover:bg-white/[0.05] transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          <div
            className={`flex items-end gap-2 rounded-xl border border-white/10 bg-[#12151d] transition-all focus-within:ring-1 ${app.accent.ring}`}
          >
            <textarea
              ref={taRef}
              rows={1}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder={
                project
                  ? `Fale com o LLM sobre o projeto ${project.name}…`
                  : 'Fale com o LLM… (selecione um projeto na barra lateral)'
              }
              className="flex-1 bg-transparent px-4 py-3 text-[13.5px] text-zinc-100 placeholder:text-zinc-600 outline-none resize-none max-h-[160px]"
            />
            <button
              onClick={submit}
              disabled={!value.trim() || app.isStreaming}
              className={`m-1.5 p-2.5 rounded-lg transition-all ${
                !value.trim() || app.isStreaming
                  ? 'bg-white/[0.05] text-zinc-600 cursor-not-allowed'
                  : `${app.accent.solid} shadow-lg ${app.accent.glow}`
              }`}
            >
              <Send className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center gap-3 mt-1.5 text-[10px] text-zinc-600 font-mono">
            <span>Enter envia · Shift+Enter nova linha</span>
            <span className="flex-1" />
            <span className="flex items-center gap-1">
              <Bot className="w-3 h-3" /> escopo: {project ? project.name : 'global'}
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}

function MessageRow({
  msg,
  accent,
  streaming,
}: {
  msg: ChatMessage;
  accent: AccentTheme;
  streaming: boolean;
}) {
  if (msg.role === 'user') {
    return (
      <div className="flex justify-end">
        <div
          className={`max-w-[85%] px-4 py-2.5 rounded-2xl rounded-br-sm text-[13.5px] leading-relaxed text-zinc-950 font-medium bg-gradient-to-br ${accent.gradient}`}
        >
          <p className="whitespace-pre-wrap break-words">{msg.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3">
      <div
        className={`w-7 h-7 shrink-0 rounded-lg bg-gradient-to-br ${accent.gradient} grid place-items-center text-[9px] font-extrabold text-zinc-950 shadow`}
      >
        FT
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 mb-1.5">
          <span className="text-[11px] font-semibold text-zinc-400">Ferreira Assistente</span>
          {msg.pending && !msg.content && (
            <span className="flex gap-1">
              <i className="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-bounce" />
              <i className="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-bounce [animation-delay:120ms]" />
              <i className="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-bounce [animation-delay:240ms]" />
            </span>
          )}
        </div>
        {msg.error && !msg.content ? (
          <p className="text-[13px] text-rose-400">não foi possível obter resposta do backend</p>
        ) : (
          <Markdown text={msg.content} streaming={streaming && !msg.pending} />
        )}
      </div>
    </div>
  );
}

function EmptyState({ onPick, accent }: { onPick: (t: string) => void; accent: AccentTheme }) {
  return (
    <div className="h-full flex flex-col items-center justify-center gap-7 px-6 py-10">
      <div className="relative">
        <div
          className={`absolute inset-0 rounded-3xl bg-gradient-to-br ${accent.gradient} opacity-20 blur-2xl`}
        />
        <div
          className={`relative w-16 h-16 rounded-2xl bg-gradient-to-br ${accent.gradient} grid place-items-center text-zinc-950 font-extrabold text-2xl shadow-xl ${accent.glow}`}
        >
          FT
        </div>
      </div>
      <div className="text-center max-w-md">
        <h2 className="text-lg font-bold text-white">Ferreira Technology — Shell Universal</h2>
        <p className="text-[13px] text-zinc-500 mt-2 leading-relaxed">
          Interface IDE universal para qualquer backend CLI. Conecte via REST/SSE e orquestre seus
          projetos conversando com o LLM embutido.
        </p>
      </div>
      <div className="grid sm:grid-cols-2 gap-2 w-full max-w-xl">
        {SUGGESTIONS.map((s) => {
          const Icon = s.icon;
          return (
            <button
              key={s.label}
              onClick={() => onPick(s.label)}
              className="flex items-center gap-3 px-3.5 py-3 rounded-xl border border-white/[0.07] bg-white/[0.02] text-left hover:bg-white/[0.05] hover:border-white/[0.12] transition-all group"
            >
              <Icon className={`w-4 h-4 shrink-0 ${accent.text}`} />
              <span className="text-[12px] text-zinc-300 group-hover:text-white leading-snug">
                {s.label}
              </span>
            </button>
          );
        })}
      </div>
      <p className="text-[10.5px] text-zinc-600 font-mono">
        POST /api/chat → SSE · CLI via POST /api/execute
      </p>
    </div>
  );
}
