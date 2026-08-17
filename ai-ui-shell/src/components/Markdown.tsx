// Renderizador Markdown leve (sem dependências) com destaque de
// blocos de código, listas, citações, links e cursor de streaming.

import { useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { Check, Copy } from 'lucide-react';

function renderInline(src: string): ReactNode[] {
  const out: ReactNode[] = [];
  const regex = /(`[^`\n]+`)|(\*\*[^*\n]+\*\*)|(\*[^*\n]+\*)|(\[[^\]]+\]\([^)\s]+\))/g;
  let last = 0;
  let key = 0;
  let m: RegExpExecArray | null;

  while ((m = regex.exec(src)) !== null) {
    if (m.index > last) out.push(src.slice(last, m.index));
    const tok = m[0];
    const k = `i${key++}`;
    if (tok.startsWith('`')) {
      out.push(
        <code
          key={k}
          className="px-1 py-0.5 rounded bg-white/[0.07] border border-white/[0.06] text-[0.85em] font-mono text-emerald-300"
        >
          {tok.slice(1, -1)}
        </code>
      );
    } else if (tok.startsWith('**')) {
      out.push(
        <strong key={k} className="font-semibold text-zinc-100">
          {tok.slice(2, -2)}
        </strong>
      );
    } else if (tok.startsWith('[')) {
      const mm = /^\[([^\]]+)\]\(([^)\s]+)\)/.exec(tok);
      if (mm) {
        out.push(
          <a
            key={k}
            href={mm[2]}
            target="_blank"
            rel="noreferrer"
            className="text-sky-400 underline decoration-sky-400/40 underline-offset-2 hover:text-sky-300"
          >
            {mm[1]}
          </a>
        );
      } else {
        out.push(tok);
      }
    } else {
      out.push(
        <em key={k} className="italic text-zinc-300">
          {tok.slice(1, -1)}
        </em>
      );
    }
    last = m.index + tok.length;
  }
  if (last < src.length) out.push(src.slice(last));
  return out;
}

function CodeBlock({ lang, code }: { lang: string; code: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* ignore */
    }
  };
  return (
    <div className="rounded-lg border border-white/[0.07] bg-[#0a0c12] overflow-hidden my-3">
      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-white/[0.06] bg-white/[0.02]">
        <span className="flex gap-1.5">
          <i className="w-2.5 h-2.5 rounded-full bg-rose-500/70" />
          <i className="w-2.5 h-2.5 rounded-full bg-amber-500/70" />
          <i className="w-2.5 h-2.5 rounded-full bg-emerald-500/70" />
        </span>
        <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider">
          {lang || 'bash'}
        </span>
        <button
          onClick={copy}
          className="ml-auto flex items-center gap-1 text-[10px] text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
          {copied ? 'copiado' : 'copiar'}
        </button>
      </div>
      <pre className="p-3 overflow-x-auto text-[12px] leading-relaxed font-mono text-zinc-300 whitespace-pre">
        {code}
      </pre>
    </div>
  );
}

function parse(text: string): ReactNode[] {
  const lines = text.split('\n');
  const nodes: ReactNode[] = [];
  let i = 0;
  let k = 0;
  const next = () => `b${k++}`;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trimStart();

    // Código em fenda (```)
    if (trimmed.startsWith('```')) {
      const lang = trimmed.slice(3).trim();
      const buf: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trimStart().startsWith('```')) {
        buf.push(lines[i]);
        i++;
      }
      if (i < lines.length) i++;
      nodes.push(<CodeBlock key={next()} lang={lang} code={buf.join('\n')} />);
      continue;
    }

    if (!line.trim()) {
      i++;
      continue;
    }

    // Títulos
    const heading = /^(#{1,4})\s+(.*)$/.exec(line);
    if (heading) {
      const level = heading[1].length;
      const cls =
        level === 1
          ? 'text-lg font-bold text-white'
          : level === 2
            ? 'text-[15px] font-semibold text-zinc-100'
            : level === 3
              ? 'text-[14px] font-semibold text-zinc-200'
              : 'text-[13px] font-semibold text-zinc-300';
      nodes.push(
        <div key={next()} className={`${cls} pt-2`}>
          {renderInline(heading[2])}
        </div>
      );
      i++;
      continue;
    }

    // Divisor
    if (/^\s*(-{3,}|\*{3,})\s*$/.test(line)) {
      nodes.push(<hr key={next()} className="border-white/[0.07]" />);
      i++;
      continue;
    }

    // Citação
    if (/^\s*>/.test(line)) {
      const buf: string[] = [];
      while (i < lines.length && /^\s*>/.test(lines[i])) {
        buf.push(lines[i].replace(/^\s*>\s?/, ''));
        i++;
      }
      nodes.push(
        <blockquote
          key={next()}
          className="border-l-2 border-amber-400/50 bg-amber-400/[0.04] px-3 py-2 rounded-r-md text-[12.5px] text-amber-100/80 space-y-1"
        >
          {buf.map((l, idx) => (
            <p key={idx}>{renderInline(l)}</p>
          ))}
        </blockquote>
      );
      continue;
    }

    // Listas
    const isUl = /^\s*[-*+]\s+/.test(line);
    const isOl = /^\s*\d+[.)]\s+/.test(line);
    if (isUl || isOl) {
      const items: string[] = [];
      while (i < lines.length) {
        const l = lines[i];
        if (isUl ? /^\s*[-*+]\s+/.test(l) : /^\s*\d+[.)]\s+/.test(l)) {
          items.push(l.replace(/^\s*(?:[-*+]|\d+[.)])\s+/, ''));
          i++;
        } else if (!l.trim()) {
          i++;
          break;
        } else {
          break;
        }
      }
      if (isUl) {
        nodes.push(
          <ul key={next()} className="space-y-1 pl-5 list-disc marker:text-emerald-400/70">
            {items.map((it, idx) => (
              <li key={idx}>{renderInline(it)}</li>
            ))}
          </ul>
        );
      } else {
        nodes.push(
          <ol key={next()} className="space-y-1 pl-5 list-decimal marker:text-emerald-400/70">
            {items.map((it, idx) => (
              <li key={idx}>{renderInline(it)}</li>
            ))}
          </ol>
        );
      }
      continue;
    }

    // Parágrafo
    const buf: string[] = [line];
    i++;
    while (
      i < lines.length &&
      lines[i].trim() &&
      !lines[i].trimStart().startsWith('```') &&
      !/^(#{1,4}\s)/.test(lines[i]) &&
      !/^\s*>/.test(lines[i]) &&
      !/^\s*([-*+]\s|\d+[.)]\s)/.test(lines[i]) &&
      !/^\s*(-{3,}|\*{3,})\s*$/.test(lines[i])
    ) {
      buf.push(lines[i]);
      i++;
    }
    nodes.push(
      <p key={next()}>
        {buf.map((l, idx) => (
          <span key={idx}>
            {idx > 0 && <br />}
            {renderInline(l)}
          </span>
        ))}
      </p>
    );
  }

  return nodes;
}

export function Markdown({ text, streaming = false }: { text: string; streaming?: boolean }) {
  const nodes = useMemo(() => parse(text), [text]);
  if (!text.trim()) return null;
  return (
    <div className="text-[13.5px] leading-relaxed text-zinc-300 space-y-2.5 break-words min-w-0">
      {nodes}
      {streaming && <span className="cursor-blink" />}
    </div>
  );
}
