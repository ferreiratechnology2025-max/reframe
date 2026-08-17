import { useEffect, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import { SquareTerminal, Trash2 } from 'lucide-react';
import { useApp } from '../../state/AppContext';
import type { TerminalKind } from '../../types';

const KIND_CLASS: Record<TerminalKind, string> = {
  input: 'text-zinc-100',
  output: 'text-zinc-300',
  error: 'text-rose-400',
  info: 'text-zinc-500',
  success: 'text-emerald-400',
  system: 'text-cyan-300',
};

export function Terminal() {
  const app = useApp();
  const [value, setValue] = useState('');
  const [history, setHistory] = useState<string[]>([]);
  const [histIdx, setHistIdx] = useState(-1);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [app.terminal]);

  const submit = () => {
    const cmd = value.trim();
    if (!cmd) return;
    setHistory((h) => [...h, cmd]);
    setHistIdx(-1);
    setValue('');
    app.runCommand(cmd);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      submit();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      const idx = histIdx === -1 ? history.length - 1 : Math.max(0, histIdx - 1);
      if (history[idx] != null) {
        setHistIdx(idx);
        setValue(history[idx]);
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      const idx = histIdx + 1;
      if (idx >= history.length) {
        setHistIdx(-1);
        setValue('');
      } else {
        setHistIdx(idx);
        setValue(history[idx]);
      }
    } else if (e.key === 'l' && e.ctrlKey) {
      e.preventDefault();
      app.clearTerminal();
    }
  };

  return (
    <div className="h-full min-h-0 flex flex-col bg-[#0a0c11]">
      {/* Cabeçalho */}
      <div className="flex items-center gap-2 px-3 h-9 border-b border-white/[0.06] bg-[#0d1017] shrink-0">
        <span className="flex gap-1.5">
          <i className="w-2.5 h-2.5 rounded-full bg-rose-500/60" />
          <i className="w-2.5 h-2.5 rounded-full bg-amber-500/60" />
          <i className="w-2.5 h-2.5 rounded-full bg-emerald-500/60" />
        </span>
        <SquareTerminal className="w-3.5 h-3.5 text-zinc-500 ml-1" />
        <span className="text-[11px] font-mono text-zinc-400">terminal — ft@shell</span>
        <span className="flex-1" />
        <button
          onClick={app.clearTerminal}
          title="Limpar terminal (Ctrl+L)"
          className="p-1.5 rounded-md text-zinc-500 hover:text-white hover:bg-white/[0.06]"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Linhas */}
      <div
        ref={scrollRef}
        className="flex-1 min-h-0 overflow-y-auto px-4 py-3 cursor-text"
        onClick={() => inputRef.current?.focus()}
      >
        {app.terminal.map((line) => (
          <div key={line.id} className="flex gap-2 text-[12px] font-mono leading-relaxed">
            {line.kind === 'input' && (
              <span className="text-cyan-400 shrink-0">ft@shell:~$</span>
            )}
            <span className={`whitespace-pre-wrap break-words ${KIND_CLASS[line.kind]}`}>
              {line.text}
            </span>
          </div>
        ))}
      </div>

      {/* Entrada */}
      <div className="flex items-center gap-2 px-4 py-2.5 border-t border-white/[0.06] bg-[#0a0c11] shrink-0">
        <span className="text-cyan-400 text-[12px] font-mono shrink-0">ft@shell:~$</span>
        <input
          ref={inputRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="digite help…"
          autoFocus
          className="flex-1 bg-transparent text-[12px] font-mono text-zinc-100 outline-none placeholder:text-zinc-700 caret-emerald-400"
        />
      </div>
    </div>
  );
}
