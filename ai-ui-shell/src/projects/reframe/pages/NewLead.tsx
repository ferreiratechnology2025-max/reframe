// src/projects/reframe/pages/NewLead.tsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { reframeApi } from '../api/reframeApi';

export const VS2_NICHES = ['estetica', 'academia', 'barbearia'];

export function isValidWhatsApp(phone: string): boolean {
  // Aceita +55, DDD + número, com espaços/parenteses/hífens opcionais
  const digits = phone.replace(/\D/g, '');
  return digits.length >= 10 && digits.length <= 13;
}

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
    if (!isValidWhatsApp(form.phone)) {
      setError('WhatsApp inválido. Use o formato com DDD, ex: (62) 99999-9999.');
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const { generation } = await reframeApi.generateDemo(form);
      navigate(`/generation/${generation.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha ao criar lead');
      setLoading(false);
    }
  };

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
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

      <h1 className="text-xl font-semibold text-white mb-6">Nova Demo</h1>

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
            placeholder="Ex: Clínica Dra. Andrielle"
          />
        </div>

        <div>
          <label className="block text-sm text-zinc-400 mb-1">Nicho *</label>
          <select
            name="niche"
            value={form.niche}
            onChange={handleChange}
            required
            className="w-full px-4 py-2 rounded-lg bg-white/[0.03] border border-white/[0.06] text-white focus:outline-none focus:border-emerald-500/40 transition"
          >
            <option value="" disabled className="text-zinc-600">
              Selecione um nicho comercial
            </option>
            {VS2_NICHES.map((niche) => (
              <option key={niche} value={niche} className="text-zinc-200 bg-[#0b0d12]">
                {niche}
              </option>
            ))}
          </select>
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
          <label className="block text-sm text-zinc-400 mb-1">WhatsApp *</label>
          <input
            type="tel"
            name="phone"
            value={form.phone}
            onChange={handleChange}
            required
            className="w-full px-4 py-2 rounded-lg bg-white/[0.03] border border-white/[0.06] text-white placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500/40 transition"
            placeholder="Ex: (62) 99999-9999"
          />
          {form.phone && !isValidWhatsApp(form.phone) && (
            <p className="text-xs text-rose-400 mt-1">
              WhatsApp com DDD e 8-9 dígitos, ex: (62) 99999-9999
            </p>
          )}
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
          {loading ? 'Gerando demo...' : 'Gerar Demo'}
        </button>
      </form>
    </div>
  );
}