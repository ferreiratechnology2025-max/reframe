// src/projects/reframe/pages/Leads.tsx
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { reframeApi, type Lead } from '../api/reframeApi';

export function Leads() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadLeads();
  }, []);

  const loadLeads = async () => {
    try {
      setLoading(true);
      const data = await reframeApi.getLeads();
      setLeads(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load leads');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = (leadId: string) => {
    navigate(`/generation/new?lead=${leadId}`);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-zinc-400">Carregando leads...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-rose-400">Erro: {error}</div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-white">Leads</h1>
          <p className="text-sm text-zinc-500 mt-1">
            {leads.length} leads cadastrados
          </p>
        </div>
        <button
          onClick={() => navigate('/leads/new')}
          className="px-4 py-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 transition"
        >
          + Novo Lead
        </button>
      </div>

      {leads.length === 0 ? (
        <div className="text-center py-12 text-zinc-500">
          <p>Nenhum lead cadastrado.</p>
          <p className="text-sm">Clique em "Novo Lead" para começar.</p>
        </div>
      ) : (
        <div className="grid gap-3">
          {leads.map((lead) => (
            <LeadCard key={lead.id} lead={lead} onGenerate={handleGenerate} />
          ))}
        </div>
      )}
    </div>
  );
}

function LeadCard({ lead, onGenerate }: { lead: Lead; onGenerate: (id: string) => void }) {
  return (
    <div className="flex items-center justify-between p-4 rounded-lg bg-white/[0.03] border border-white/[0.06] hover:bg-white/[0.06] transition">
      <div className="min-w-0 flex-1">
        <h3 className="font-medium text-white truncate">{lead.name}</h3>
        <div className="flex items-center gap-3 text-sm text-zinc-500 flex-wrap">
          <span className="capitalize">{lead.niche}</span>
          <span>•</span>
          <span>{lead.city}</span>
          <span>•</span>
          <span className="font-mono">{lead.phone}</span>
        </div>
      </div>
      <button
        onClick={() => onGenerate(lead.id)}
        className="ml-4 px-4 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 text-sm transition whitespace-nowrap"
      >
        Gerar Landing
      </button>
    </div>
  );
}
