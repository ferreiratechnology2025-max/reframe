// src/projects/reframe/pages/Dashboard.tsx
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { reframeApi, type Generation } from '../api/reframeApi';

const STATUS_LABELS: Record<Generation['status'], string> = {
  queued: 'Na fila',
  generating: 'Gerando',
  rendering: 'Renderizando',
  publishing: 'Publicando',
  published: 'Publicado',
  failed: 'Falhou',
};

const STATUS_STYLES: Record<Generation['status'], string> = {
  queued: 'bg-zinc-500/10 text-zinc-400 border-zinc-500/20',
  generating: 'bg-sky-500/10 text-sky-400 border-sky-500/20',
  rendering: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  publishing: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  published: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  failed: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
};

export function Dashboard() {
  const [generations, setGenerations] = useState<Generation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadGenerations();
  }, []);

  const loadGenerations = async () => {
    try {
      setLoading(true);
      const data = await reframeApi.getGenerations();
      setGenerations([...data].reverse());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha ao carregar gerações');
    } finally {
      setLoading(false);
    }
  };

  const published = generations.filter((g) => g.status === 'published').length;
  const failed = generations.filter((g) => g.status === 'failed').length;
  const inProgress = generations.filter((g) => !['published', 'failed'].includes(g.status)).length;

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-white">Dashboard</h1>
          <p className="text-sm text-zinc-500 mt-1">Gerações de demo</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => navigate('/leads')}
            className="px-4 py-2 rounded-lg bg-white/[0.03] text-zinc-300 border border-white/[0.06] hover:bg-white/[0.06] transition"
          >
            Leads
          </button>
          <button
            onClick={() => navigate('/leads/new')}
            className="px-4 py-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 transition"
          >
            + Nova Demo
          </button>
        </div>
      </div>

      {generations.length > 0 && (
        <div className="grid grid-cols-3 gap-3 mb-6">
          <div className="p-4 rounded-lg bg-white/[0.03] border border-white/[0.06]">
            <div className="text-2xl font-semibold text-white">{generations.length}</div>
            <div className="text-xs text-zinc-500 mt-1">Total</div>
          </div>
          <div className="p-4 rounded-lg bg-white/[0.03] border border-white/[0.06]">
            <div className="text-2xl font-semibold text-emerald-400">{published}</div>
            <div className="text-xs text-zinc-500 mt-1">Publicados</div>
          </div>
          <div className="p-4 rounded-lg bg-white/[0.03] border border-white/[0.06]">
            <div className="text-2xl font-semibold text-rose-400">{failed}</div>
            <div className="text-xs text-zinc-500 mt-1">Falhas</div>
          </div>
        </div>
      )}

      {loading && (
        <div className="text-zinc-400">Carregando gerações...</div>
      )}

      {error && <div className="text-rose-400">Erro: {error}</div>}

      {!loading && !error && generations.length === 0 && (
        <div className="text-center py-12 text-zinc-500">
          <p>Nenhuma geração ainda.</p>
          <p className="text-sm mt-1">Clique em "+ Nova Demo" para gerar a primeira landing.</p>
        </div>
      )}

      {!loading && generations.length > 0 && (
        <div className="grid gap-3">
          {generations.map((gen) => (
            <GenerationCard key={gen.id} generation={gen} onClick={() => navigate(`/generation/${gen.id}`)} />
          ))}
        </div>
      )}
    </div>
  );
}

function GenerationCard({ generation, onClick }: { generation: Generation; onClick: () => void }) {
  return (
    <div
      onClick={onClick}
      className="flex items-center justify-between p-4 rounded-lg bg-white/[0.03] border border-white/[0.06] hover:bg-white/[0.06] transition cursor-pointer"
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-mono text-sm text-zinc-400">{generation.id}</span>
          <span className={`px-2 py-0.5 rounded-md border text-xs ${STATUS_STYLES[generation.status]}`}>
            {STATUS_LABELS[generation.status]}
          </span>
        </div>
        <div className="flex items-center gap-3 text-sm text-zinc-500 flex-wrap mt-1">
          {generation.personality && (
            <>
              <span className="text-zinc-300">Template: {generation.personality}</span>
              <span>•</span>
            </>
          )}
          {generation.position && (
            <>
              <span className="capitalize">Posição: {generation.position}</span>
              <span>•</span>
            </>
          )}
          {generation.archetype_name && (
            <>
              <span className="capitalize">Arquétipo: {generation.archetype_name}</span>
              <span>•</span>
            </>
          )}
          <span>{new Date(generation.created_at).toLocaleString('pt-BR')}</span>
        </div>
        {generation.error && (
          <div className="text-xs text-rose-400/70 mt-1 truncate">{generation.error.message}</div>
        )}
      </div>
      {generation.status === 'published' && generation.url && (
        <a
          href={generation.url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="ml-4 px-3 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 text-sm transition whitespace-nowrap"
        >
          Abrir ↗
        </a>
      )}
      {generation.status === 'failed' && (
        <span className="ml-4 px-3 py-1.5 rounded-lg text-sm text-zinc-500 whitespace-nowrap">
          {generation.error?.code || 'Erro'}
        </span>
      )}
      {!['published', 'failed'].includes(generation.status) && (
        <span className="ml-4 px-3 py-1.5 rounded-lg text-sm text-zinc-500 whitespace-nowrap">
          {inProgressLabel(generation.status)}
        </span>
      )}
    </div>
  );
}

function inProgressLabel(status: Generation['status']): string {
  return status === 'queued' ? 'Na fila' : 'Processando…';
}