// src/projects/reframe/pages/NewLead.tsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { reframeApi } from '../api/reframeApi';

export function NewLead() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: '',
    niche: '',
    city: '',
    phone: '',
    place_id: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError(null);
      const lead = await reframeApi.createLead(form);
      navigate(`/generation/new?lead=${lead.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha ao criar lead');
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  return (
    <div className="p-6 max-w-md mx-auto">
      <button
        onClick={() => navigate('/leads')}
        className="text-sm text-zinc-500 hover:text-zinc-300 transition mb-6"
      >
        ← Voltar
      </button>

      <h1 className="text-xl font-semibold text-white mb-6">Novo Lead</h1>

      {error && (
        <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm mb-4">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm text-zinc-400 mb-1">Nome do negócio *</label>
          <input
            type="text"
            name="name"
            value={form.name}
            onChange={handleChange}
            required
            className="w-full px-4 py-2 rounded-lg bg-white/[0.03] border border-white/[0.06] text-white placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500/40 transition"
            placeholder="Ex: Padaria Central"
          />
        </div>

        <div>
          <label className="block text-sm text-zinc-400 mb-1">Nichos *</label>
          <input
            type="text"
            name="niche"
            value={form.niche}
            onChange={handleChange}
            required
            className="w-full px-4 py-2 rounded-lg bg-white/[0.03] border border-white/[0.06] text-white placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500/40 transition"
            placeholder="Ex: padaria, mecânica, café"
          />
        </div>

        <div>
          <label className="block text-sm text-zinc-400 mb-1">Cidade *</label>
          <input
            type="text"
            name="city"
            value={form.city}
            onChange={handleChange}
            required
            className="w-full px-4 py-2 rounded-lg bg-white/[0.03] border border-white/[0.06] text-white placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500/40 transition"
            placeholder="Ex: Goiânia"
          />
        </div>

        <div>
          <label className="block text-sm text-zinc-400 mb-1">Telefone *</label>
          <input
            type="text"
            name="phone"
            value={form.phone}
            onChange={handleChange}
            required
            className="w-full px-4 py-2 rounded-lg bg-white/[0.03] border border-white/[0.06] text-white placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500/40 transition"
            placeholder="Ex: (62) 9999-9999"
          />
        </div>

        <div>
          <label className="block text-sm text-zinc-400 mb-1">Place ID (opcional)</label>
          <input
            type="text"
            name="place_id"
            value={form.place_id}
            onChange={handleChange}
            className="w-full px-4 py-2 rounded-lg bg-white/[0.03] border border-white/[0.06] text-white placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500/40 transition"
            placeholder="Ex: ChIJWzV..."
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full px-4 py-2 rounded-lg bg-emerald-500 text-zinc-950 font-medium hover:bg-emerald-400 transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Criando...' : 'Criar Lead e Gerar Landing'}
        </button>
      </form>
    </div>
  );
}