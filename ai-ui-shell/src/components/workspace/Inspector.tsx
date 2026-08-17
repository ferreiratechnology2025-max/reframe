import { useState } from 'react';
import {
  Boxes,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  File,
  FileCode,
  FileJson,
  FileText,
  Folder,
  FolderOpen,
  Play,
  Server,
  Square,
  Trash2,
} from 'lucide-react';
import { useApp } from '../../state/AppContext';
import { ENDPOINT_DOCS } from '../../config';
import type { FileNode } from '../../types';

const statusChip = (s: string) =>
  s === 'active'
    ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
    : s === 'error'
      ? 'border-rose-500/30 bg-rose-500/10 text-rose-300'
      : 'border-white/10 bg-white/[0.04] text-zinc-500';

export function Inspector({ compact = false }: { compact?: boolean }) {
  const app = useApp();
  const project = app.projects.find((p) => p.id === app.activeProjectId) ?? null;

  if (!project) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4 px-6 text-center">
        <Boxes className="w-8 h-8 text-zinc-700" />
        <div>
          <p className="text-sm font-medium text-zinc-300">Nenhum projeto selecionado</p>
          <p className="text-[12px] text-zinc-600 mt-1">
            Selecione um projeto na barra lateral ou crie um novo.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full min-h-0 flex flex-col overflow-hidden">
      {/* Cabeçalho do projeto */}
      <div className="shrink-0 px-4 py-3.5 border-b border-white/[0.06] space-y-3">
        <div className="flex items-start gap-3">
          <div
            className={`w-9 h-9 rounded-lg bg-gradient-to-br ${app.accent.gradient} grid place-items-center text-zinc-950 font-extrabold text-sm`}
          >
            {project.name.slice(0, 2).toUpperCase()}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h2 className="text-[14px] font-bold text-white truncate">{project.name}</h2>
              <span
                className={`text-[9px] font-mono uppercase px-1.5 py-px rounded border ${statusChip(project.status)}`}
              >
                {project.status}
              </span>
            </div>
            <p className="text-[11.5px] text-zinc-500 mt-0.5 line-clamp-2">{project.description}</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">
          <button
            onClick={() => app.toggleProject(project.id)}
            className={`flex items-center gap-1.5 px-2.5 h-7 rounded-lg text-[11px] font-medium transition-colors ${
              project.status === 'active'
                ? 'border border-amber-500/30 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20'
                : app.accent.solid
            }`}
          >
            {project.status === 'active' ? (
              <Square className="w-3 h-3" />
            ) : (
              <Play className="w-3 h-3" />
            )}
            {project.status === 'active' ? 'Parar' : 'Iniciar'}
          </button>
          {project.url && (
            <a
              href={project.url}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 px-2.5 h-7 rounded-lg border border-white/10 text-[11px] text-zinc-300 hover:bg-white/[0.05] transition-colors"
            >
              <ExternalLink className="w-3 h-3" /> Abrir URL
            </a>
          )}
          <button
            onClick={() => app.deleteProject(project.id)}
            className="flex items-center gap-1.5 px-2.5 h-7 rounded-lg border border-white/10 text-[11px] text-zinc-400 hover:border-rose-500/30 hover:text-rose-300 transition-colors"
          >
            <Trash2 className="w-3 h-3" /> Remover
          </button>
        </div>
      </div>

      <div className={`flex-1 min-h-0 ${compact ? '' : 'grid lg:grid-cols-[minmax(0,1fr)_300px]'}`}>
        {/* Árvore de arquivos */}
        <section className="min-h-0 flex flex-col">
          <p className="px-4 pt-3 pb-1.5 text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
            Arquivos
          </p>
          <div className="flex-1 min-h-0 overflow-y-auto px-2 pb-4">
            <Tree nodes={project.files} />
          </div>
        </section>

        {!compact && (
          <section className="min-h-0 overflow-y-auto border-t lg:border-t-0 lg:border-l border-white/[0.06] p-4 space-y-5">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500 mb-2">
                Metadados
              </p>
              <dl className="space-y-1.5 text-[11.5px]">
                <Meta k="Framework" v={project.framework ?? '—'} />
                <Meta k="Porta" v={project.port ? String(project.port) : '—'} />
                <Meta k="URL" v={project.url ?? '—'} />
                <Meta k="Criado em" v={project.createdAt} />
                <Meta k="ID" v={project.id.slice(0, 12)} />
              </dl>
            </div>

            <div>
              <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500 mb-2">
                Variáveis de ambiente
              </p>
              <div className="space-y-1">
                {['PORT', 'DATABASE_URL', 'LLM_API_KEY'].map((k) => (
                  <div
                    key={k}
                    className="flex items-center gap-2 px-2.5 py-1.5 rounded-md bg-white/[0.02] border border-white/[0.05]"
                  >
                    <Server className="w-3 h-3 text-zinc-600" />
                    <span className="text-[11px] font-mono text-zinc-400">{k}</span>
                    <span className="flex-1 text-right text-[10px] font-mono text-zinc-700">
                      ••••••••
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500 mb-2">
                Contrato de API
              </p>
              <div className="space-y-1">
                {ENDPOINT_DOCS.slice(0, 6).map((d) => (
                  <div
                    key={d.key}
                    className="flex items-center gap-2 px-2.5 py-1.5 rounded-md bg-white/[0.02] border border-white/[0.05]"
                  >
                    <span
                      className={`text-[9px] font-mono font-bold w-12 ${
                        d.method === 'GET'
                          ? 'text-emerald-400'
                          : d.method === 'POST'
                            ? 'text-sky-400'
                            : 'text-rose-400'
                      }`}
                    >
                      {d.method}
                    </span>
                    <span className="text-[10.5px] font-mono text-zinc-500 truncate">
                      {app.settings.endpoints[d.key]}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

function Meta({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-zinc-500 shrink-0">{k}</dt>
      <dd className="font-mono text-zinc-300 truncate">{v}</dd>
    </div>
  );
}

function fileIcon(name: string) {
  const ext = name.split('.').pop()?.toLowerCase() ?? '';
  if (['json', 'jsonc'].includes(ext)) return <FileJson className="w-3.5 h-3.5 text-amber-400/80" />;
  if (['ts', 'tsx', 'js', 'jsx', 'go', 'py', 'rs', 'java', 'rb', 'c', 'cpp', 'sh', 'toml', 'cfg'].includes(ext))
    return <FileCode className="w-3.5 h-3.5 text-sky-400/80" />;
  if (['md', 'txt', 'env', 'yml', 'yaml', 'lock', 'example', 'mod', 'gitignore'].includes(ext))
    return <FileText className="w-3.5 h-3.5 text-zinc-500" />;
  return <File className="w-3.5 h-3.5 text-zinc-600" />;
}

function Tree({ nodes, depth = 0 }: { nodes: FileNode[]; depth?: number }) {
  return (
    <ul>
      {nodes.map((n) => (
        <TreeNode key={`${depth}-${n.name}`} node={n} depth={depth} />
      ))}
    </ul>
  );
}

function TreeNode({ node, depth }: { node: FileNode; depth: number }) {
  const [open, setOpen] = useState(depth < 1);
  const isDir = node.type === 'dir';
  return (
    <li>
      <button
        onClick={() => isDir && setOpen((o) => !o)}
        className="flex w-full items-center gap-1.5 px-2 py-1 hover:bg-white/[0.04] text-left rounded"
        style={{ paddingLeft: 8 + depth * 14 }}
      >
        {isDir ? (
          open ? (
            <ChevronDown className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
          )
        ) : (
          <span className="w-3.5 shrink-0" />
        )}
        {isDir ? (
          open ? (
            <FolderOpen className="w-3.5 h-3.5 text-amber-400/70 shrink-0" />
          ) : (
            <Folder className="w-3.5 h-3.5 text-amber-400/70 shrink-0" />
          )
        ) : (
          fileIcon(node.name)
        )}
        <span className="text-[12.5px] font-mono text-zinc-300 truncate">{node.name}</span>
        {node.size && <span className="ml-auto text-[10px] text-zinc-600 shrink-0">{node.size}</span>}
      </button>
      {isDir && open && node.children && <Tree nodes={node.children} depth={depth + 1} />}
    </li>
  );
}
