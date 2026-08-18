// src/projects/reframe/pages/GenerationTracker.tsx
import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, useParams } from 'react-router-dom';
import { reframeApi, type Generation } from '../api/reframeApi';

export function GenerationTracker() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { id: generationId } = useParams<{ id: string }>();

  const leadId = searchParams.get('lead');
  const [generation, setGeneration] = useState<Generation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // CASO 1: URL direta com generationId
    if (generationId) {
      void loadGeneration(generationId);
      return;
    }

    // CASO 2: Novo fluxo com leadId
    if (leadId) {
      void startGeneration(leadId);
      return;
    }

    // CASO 3: Nenhum parâmetro
    setError('Nenhum lead ou geração especificada');
    setLoading(false);
  }, [generationId, leadId]);

  const loadGeneration = async (id: string) => {
    try {
      setLoading(true);
      const gen = await reframeApi.getGeneration(id);
      setGeneration(gen);
      setError(null);

      // Se ainda não terminou, inicia polling
      if (!['published', 'failed'].includes(gen.status)) {
        await reframeApi.pollGeneration(gen.id, (updated) => {
          setGeneration(updated);
          if (['published', 'failed'].includes(updated.status)) {
            setLoading(false);
          }
        });
      } else {
        setLoading(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha ao carregar geração');
      setLoading(false);
    }
  };

  const startGeneration = async (id: string) => {
    try {
      setLoading(true);
      // Cria a geração
      const gen = await reframeApi.createGeneration(id);

      // Redirecionar para a URL canônica (dispara loadGeneration via useEffect)
      navigate(`/generation/${gen.id}`, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha ao iniciar geração');
      setLoading(false);
    }
  };

  if (loading && !generation) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-zinc-400">Iniciando geração...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <div className="text-rose-400">Erro: {error}</div>
        <button
          onClick={() => navigate('/leads')}
          className="px-4 py-2 rounded-lg border border-white/[0.06] text-zinc-400 hover:text-white hover:border-white/[0.12] transition"
        >
          Voltar para Leads
        </button>
      </div>
    );
  }

  if (!generation) return null;

  return <GenerationStatus generation={generation} onBack={() => navigate('/leads')} />;
}

function GenerationStatus({ generation, onBack }: { generation: Generation; onBack: () => void }) {
  const steps = [
    { key: 'queued', label: 'Na fila', icon: '⏳' },
    { key: 'generating', label: 'Gerando conteúdo', icon: '✍️' },
    { key: 'rendering', label: 'Renderizando', icon: '🎨' },
    { key: 'publishing', label: 'Publicando', icon: '🚀' },
    { key: 'published', label: 'Publicado', icon: '✅' },
  ];

  const currentStepIndex = steps.findIndex((s) => s.key === generation.status);
  const isFailed = generation.status === 'failed';
  const isPublished = generation.status === 'published';

  return (
    <div className="p-6 max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <button
            onClick={onBack}
            className="text-sm text-zinc-500 hover:text-zinc-300 transition"
          >
            ← Voltar
          </button>
          <h1 className="text-xl font-semibold text-white mt-2">Gerando Landing</h1>
          <p className="text-sm text-zinc-500 mt-1">
            {generation.id} • {generation.status}
          </p>
        </div>
        {isPublished && generation.url && (
          <a
            href={generation.url}
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 transition"
          >
            Abrir Landing ↗
          </a>
        )}
      </div>

      {/* Pipeline Steps */}
      <div className="space-y-4 mb-8">
        {steps.map((step, index) => {
          const isActive = index === currentStepIndex && !isFailed;
          const isDone = index < currentStepIndex && !isFailed;
          const isPending = index > currentStepIndex || (isFailed && index > currentStepIndex);

          return (
            <div
              key={step.key}
              className={`flex items-center gap-4 p-3 rounded-lg border transition ${
                isActive
                  ? 'border-emerald-500/30 bg-emerald-500/5'
                  : isDone
                    ? 'border-white/[0.06] bg-white/[0.03]'
                    : 'border-white/[0.03] bg-white/[0.01]'
              } ${isPending ? 'opacity-30' : ''}`}
            >
              <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0">
                {isDone && !isFailed && (
                  <span className="text-emerald-400 text-lg">✓</span>
                )}
                {isActive && !isFailed && (
                  <div className="w-5 h-5 rounded-full border-2 border-emerald-400 animate-spin border-t-transparent" />
                )}
                {isPending && !isFailed && (
                  <span className="text-zinc-600 text-lg">{step.icon}</span>
                )}
                {isFailed && (
                  <span className="text-rose-400 text-lg">✗</span>
                )}
              </div>
              <div>
                <div
                  className={`text-sm ${
                    isActive ? 'text-white' : isDone ? 'text-zinc-300' : 'text-zinc-500'
                  }`}
                >
                  {step.label}
                </div>
                {isActive && !isFailed && (
                  <div className="text-xs text-emerald-400/60 animate-pulse">
                    Processando...
                  </div>
                )}
                {isDone && !isFailed && (
                  <div className="text-xs text-emerald-400/60">Concluído</div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Result - Published */}
      {isPublished && (
        <div className="p-4 rounded-lg border border-emerald-500/20 bg-emerald-500/5">
          <h3 className="text-sm font-medium text-emerald-400 mb-3">✅ Landing publicada!</h3>

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-zinc-500">Arquétipo</span>
              <p className="text-white font-medium">{generation.archetype_name || '-'}</p>
            </div>
            <div>
              <span className="text-zinc-500">Posição de mercado</span>
              <p className="text-white font-medium capitalize">{generation.position || '-'}</p>
            </div>
            <div>
              <span className="text-zinc-500">Template visual</span>
              <p className="text-white font-medium">{generation.personality || '-'}</p>
            </div>
            <div>
              <span className="text-zinc-500">Cor primária</span>
              <div className="flex items-center gap-2 mt-0.5">
                <div
                  className="w-5 h-5 rounded-full border border-white/[0.1]"
                  style={{ backgroundColor: generation.primary_color || '#34d399' }}
                />
                <span className="text-white font-mono text-xs">
                  {generation.primary_color || '#34d399'}
                </span>
              </div>
            </div>
          </div>

          <div className="mt-3">
            <span className="text-zinc-500 text-sm">Trust Signals</span>
            <div className="flex flex-wrap gap-2 mt-1">
              {generation.proofs.length > 0 ? (
                generation.proofs.map((proof, i) => (
                  <span
                    key={i}
                    className="px-2 py-1 rounded-md bg-white/[0.05] border border-white/[0.06] text-xs text-zinc-300"
                  >
                    {proof}
                  </span>
                ))
              ) : (
                <span className="text-xs text-zinc-500">Nenhum</span>
              )}
            </div>
          </div>

          {generation.headline && (
            <div className="mt-3 pt-3 border-t border-white/[0.06]">
              <span className="text-zinc-500 text-sm">Headline</span>
              <p className="text-sm text-white mt-0.5">{generation.headline}</p>
              {generation.subheadline && (
                <p className="text-xs text-zinc-400 mt-0.5">{generation.subheadline}</p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Result - Failed */}
      {isFailed && (
        <div className="p-4 rounded-lg border border-rose-500/20 bg-rose-500/5">
          <h3 className="text-sm font-medium text-rose-400">❌ Falha na geração</h3>
          <p className="text-sm text-rose-300/70 mt-1">
            {generation.error?.message || 'Erro desconhecido'}
          </p>
          {generation.error && (
            <details className="mt-2">
              <summary className="text-xs text-zinc-500 cursor-pointer hover:text-zinc-300 transition">
                Detalhes técnicos
              </summary>
              <pre className="mt-1 p-2 rounded bg-black/40 border border-white/[0.06] text-xs text-zinc-500 overflow-x-auto whitespace-pre-wrap">
                {generation.error.detail || generation.error.code}
              </pre>
            </details>
          )}
          <button
            onClick={() => window.location.reload()}
            className="mt-3 px-4 py-1.5 rounded-lg border border-rose-500/20 text-rose-400 text-sm hover:bg-rose-500/10 transition"
          >
            Tentar novamente
          </button>
        </div>
      )}
    </div>
  );
}
