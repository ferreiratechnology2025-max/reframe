import { useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import { Check, Download, Globe, KeyRound, RotateCcw, X } from 'lucide-react';
import { useApp } from '../../state/AppContext';
import { ACCENTS, BRAND, ENDPOINT_DOCS, SSE_FORMAT_DOC } from '../../config';
import type { AccentKey } from '../../types';

type Section = 'conexao' | 'contrato' | 'modelos' | 'provedores' | 'aparencia';

const SECTIONS: { key: Section; label: string }[] = [
  { key: 'conexao', label: 'Conexão' },
  { key: 'contrato', label: 'Contrato de API' },
  { key: 'modelos', label: 'Modelos' },
  { key: 'provedores', label: 'Provedores' },
  { key: 'aparencia', label: 'Aparência' },
];

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="space-y-1.5">
      <p className="text-[11px] font-medium text-zinc-400">{label}</p>
      {children}
    </div>
  );
}

function InfoBox({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-lg border border-white/[0.07] bg-white/[0.02] px-3.5 py-3 text-[12px] leading-relaxed text-zinc-400">
      {children}
    </div>
  );
}

export function SettingsPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const app = useApp();
  const [section, setSection] = useState<Section>('conexao');
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null);
  const [newModel, setNewModel] = useState('');
  const [providerKeys, setProviderKeys] = useState<Record<string, string>>({});
  const [savedProvider, setSavedProvider] = useState<string | null>(null);

  const test = async () => {
    setTesting(true);
    setResult(null);
    const ok = await app.testConnection();
    setResult(
      ok
        ? { ok: true, msg: `Backend conectado em ${app.health?.latency ?? '?'} ms` }
        : { ok: false, msg: 'Backend não respondeu — modo demo ativado automaticamente' }
    );
    setTesting(false);
  };

  const addModel = (e: FormEvent) => {
    e.preventDefault();
    const m = newModel.trim();
    setNewModel('');
    if (!m || app.settings.models.includes(m)) return;
    app.updateSettings({ models: [...app.settings.models, m] });
  };

  const saveKey = (id: string) => {
    setSavedProvider(id);
    setTimeout(() => setSavedProvider((cur) => (cur === id ? null : cur)), 1800);
  };

  const downloadContract = () => {
    const data = {
      name: `${BRAND.name} — Contrato de API (${BRAND.product})`,
      version: BRAND.version,
      baseUrl: app.settings.apiUrl,
      auth: app.settings.apiToken ? 'Authorization: Bearer <token>' : 'nenhuma',
      transport: 'REST + SSE (text/event-stream)',
      endpoints: ENDPOINT_DOCS.map((d) => ({
        name: d.key,
        method: d.method,
        path: app.settings.endpoints[d.key],
        description: d.description,
      })),
      streaming: {
        chat: 'data: {"content":"<delta>"} … data: [DONE]',
        execute: 'chunks de texto bruto (stdout)',
      },
      types: {
        Project: 'id, name, description, status, port, url, framework, createdAt',
        ChatMessage: 'id, role (user|assistant), content, timestamp',
      },
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'ferreira-shell-contract.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      {open && (
        <div className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      )}
      <aside
        className={`fixed inset-y-0 right-0 z-50 w-full max-w-md flex flex-col bg-[#0d1017] border-l border-white/[0.08] shadow-2xl transition-transform duration-300 ${
          open ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {/* Cabeçalho */}
        <div className="flex items-center gap-3 px-5 h-14 border-b border-white/[0.06] shrink-0">
          <h2 className="text-[15px] font-bold text-white">Configurações</h2>
          <span className="text-[10px] font-mono text-zinc-600">{BRAND.name} · Shell</span>
          <button
            onClick={onClose}
            className="ml-auto p-1.5 rounded-md text-zinc-500 hover:text-white hover:bg-white/[0.06]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Abas */}
        <div className="flex gap-1 px-3 py-2 border-b border-white/[0.06] overflow-x-auto shrink-0">
          {SECTIONS.map((s) => (
            <button
              key={s.key}
              onClick={() => setSection(s.key)}
              className={`px-3 h-7 rounded-lg text-[11.5px] whitespace-nowrap transition-colors ${
                section === s.key ? app.accent.chip : 'text-zinc-500 hover:text-zinc-200'
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto px-5 py-4 space-y-5">
          {section === 'conexao' && (
            <>
              <Field label="URL do backend (REST + SSE)">
                <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-[#12151d] px-3">
                  <Globe className="w-3.5 h-3.5 text-zinc-600 shrink-0" />
                  <input
                    value={app.settings.apiUrl}
                    onChange={(e) => app.updateSettings({ apiUrl: e.target.value })}
                    placeholder="http://localhost:4000"
                    className="w-full bg-transparent py-2.5 text-[13px] font-mono text-zinc-100 outline-none placeholder:text-zinc-600"
                  />
                </div>
              </Field>
              <Field label="Token de acesso (Authorization: Bearer — opcional)">
                <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-[#12151d] px-3">
                  <KeyRound className="w-3.5 h-3.5 text-zinc-600 shrink-0" />
                  <input
                    type="password"
                    value={app.settings.apiToken}
                    onChange={(e) => app.updateSettings({ apiToken: e.target.value })}
                    placeholder="sk-…"
                    className="w-full bg-transparent py-2.5 text-[13px] font-mono text-zinc-100 outline-none placeholder:text-zinc-600"
                  />
                </div>
              </Field>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => void test()}
                  disabled={testing}
                  className={`px-3.5 h-8 rounded-lg text-[12px] font-medium transition-colors ${
                    testing ? 'bg-white/[0.05] text-zinc-500' : app.accent.solid
                  }`}
                >
                  {testing ? 'Testando…' : 'Testar conexão'}
                </button>
                <button
                  onClick={app.resetSettings}
                  className="flex items-center gap-1.5 px-3 h-8 rounded-lg border border-white/10 text-[12px] text-zinc-400 hover:bg-white/[0.05]"
                >
                  <RotateCcw className="w-3 h-3" /> Restaurar padrões
                </button>
              </div>
              {result && (
                <p className={`text-[12px] ${result.ok ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {result.ok ? '✓ ' : '⚠ '}
                  {result.msg}
                </p>
              )}
              <InfoBox>
                O shell testa <code className="font-mono text-emerald-300">/health</code> a cada 30s.
                Sem resposta, ativa o <b className="text-zinc-200">modo demo</b> automaticamente para
                você experimentar a interface. Cada endpoint pode ser remapeado na aba{' '}
                <b className="text-zinc-200">Contrato de API</b> — a UI é 100% agnóstica de backend.
              </InfoBox>
            </>
          )}

          {section === 'contrato' && (
            <>
              <p className="text-[12px] text-zinc-500 leading-relaxed">
                Remapeie os caminhos para casar com seu backend. Use{' '}
                <code className="font-mono text-emerald-300 px-1 py-0.5 rounded bg-white/[0.06]">
                  {'{id}'}
                </code>{' '}
                para parâmetros. As respostas são normalizadas por adaptadores com fallbacks.
              </p>
              <div className="space-y-3">
                {ENDPOINT_DOCS.map((d) => (
                  <div
                    key={d.key}
                    className="rounded-lg border border-white/[0.07] bg-white/[0.02] p-3 space-y-1.5"
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-[9px] font-mono font-bold px-1.5 py-px rounded ${
                          d.method === 'GET'
                            ? 'bg-emerald-500/15 text-emerald-300'
                            : d.method === 'POST'
                              ? 'bg-sky-500/15 text-sky-300'
                              : 'bg-rose-500/15 text-rose-300'
                        }`}
                      >
                        {d.method}
                      </span>
                      <span className="text-[11.5px] text-zinc-300 font-medium">{d.key}</span>
                      <span className="ml-auto text-[10px] text-zinc-600 text-right">{d.description}</span>
                    </div>
                    <input
                      value={app.settings.endpoints[d.key]}
                      onChange={(e) =>
                        app.updateSettings({
                          endpoints: { ...app.settings.endpoints, [d.key]: e.target.value },
                        })
                      }
                      className="w-full rounded-md border border-white/10 bg-[#12151d] px-2.5 py-1.5 text-[12px] font-mono text-zinc-200 outline-none focus:border-white/20"
                    />
                  </div>
                ))}
              </div>
              <pre className="rounded-lg border border-white/[0.07] bg-[#0a0c12] p-3 text-[10.5px] font-mono text-zinc-500 overflow-x-auto leading-relaxed">
                {SSE_FORMAT_DOC}
              </pre>
              <button
                onClick={downloadContract}
                className={`w-full flex items-center justify-center gap-2 h-9 rounded-lg text-[12.5px] font-medium ${app.accent.solid}`}
              >
                <Download className="w-3.5 h-3.5" /> Baixar contrato.json
              </button>
            </>
          )}

          {section === 'modelos' && (
            <>
              <p className="text-[12px] text-zinc-500">
                Modelos enviados no payload do chat ({' '}
                <code className="font-mono text-emerald-300">{'{ model }'}</code> ). Clique para
                ativar.
              </p>
              <div className="space-y-1.5">
                {app.settings.models.map((m) => (
                  <div
                    key={m}
                    onClick={() => app.updateSettings({ model: m })}
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg border cursor-pointer transition-colors ${
                      app.settings.model === m
                        ? app.accent.chip
                        : 'border-white/[0.07] bg-white/[0.02] text-zinc-400 hover:bg-white/[0.05]'
                    }`}
                  >
                    <span className="text-[12.5px] font-mono">{m}</span>
                    {app.settings.model === m && <Check className="w-3.5 h-3.5 ml-auto" />}
                    {app.settings.model !== m && app.settings.models.length > 1 && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          app.updateSettings({
                            models: app.settings.models.filter((x) => x !== m),
                          });
                        }}
                        className="ml-auto text-[11px] text-zinc-600 hover:text-rose-400"
                      >
                        remover
                      </button>
                    )}
                  </div>
                ))}
              </div>
              <form onSubmit={addModel} className="flex gap-2">
                <input
                  value={newModel}
                  onChange={(e) => setNewModel(e.target.value)}
                  placeholder="novo modelo (ex.: llama-3.1)"
                  className="flex-1 rounded-lg border border-white/10 bg-[#12151d] px-3 py-2 text-[12.5px] font-mono text-zinc-100 outline-none placeholder:text-zinc-600"
                />
                <button
                  type="submit"
                  className={`px-3.5 rounded-lg text-[12px] font-medium ${app.accent.solid}`}
                >
                  Adicionar
                </button>
              </form>
            </>
          )}

          {section === 'provedores' && (
            <>
              <p className="text-[12px] text-zinc-500">
                Chaves enviadas via{' '}
                <code className="font-mono text-emerald-300">
                  POST /api/providers/{'{id}'}/configure
                </code>
                . No modo demo, nada é persistido.
              </p>
              <div className="space-y-3">
                {app.providers.map((p) => (
                  <div
                    key={p.id}
                    className="rounded-lg border border-white/[0.07] bg-white/[0.02] p-3 space-y-2"
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className={`w-1.5 h-1.5 rounded-full ${
                          p.configured ? 'bg-emerald-400' : 'bg-zinc-600'
                        }`}
                      />
                      <span className="text-[12.5px] font-medium text-zinc-200">{p.name}</span>
                      <span
                        className={`ml-auto text-[10px] font-mono ${
                          p.configured ? 'text-emerald-400' : 'text-zinc-600'
                        }`}
                      >
                        {p.configured ? 'configurado' : 'sem chave'}
                      </span>
                    </div>
                    <div className="flex gap-2">
                      <input
                        type="password"
                        value={providerKeys[p.id] ?? ''}
                        onChange={(e) =>
                          setProviderKeys((k) => ({ ...k, [p.id]: e.target.value }))
                        }
                        placeholder="chave da API"
                        className="flex-1 rounded-md border border-white/10 bg-[#12151d] px-2.5 py-1.5 text-[12px] font-mono text-zinc-100 outline-none placeholder:text-zinc-600"
                      />
                      <button
                        onClick={() => saveKey(p.id)}
                        className="px-3 rounded-md border border-white/10 text-[11.5px] text-zinc-300 hover:bg-white/[0.05]"
                      >
                        {savedProvider === p.id ? '✓ salvo' : 'Salvar'}
                      </button>
                    </div>
                  </div>
                ))}
                {app.providers.length === 0 && (
                  <p className="text-[12px] text-zinc-600">
                    Nenhum provedor — o backend não retornou /api/providers/status.
                  </p>
                )}
              </div>
            </>
          )}

          {section === 'aparencia' && (
            <>
              <p className="text-[12px] text-zinc-500">Cor de destaque do shell.</p>
              <div className="grid grid-cols-3 gap-2">
                {(Object.keys(ACCENTS) as AccentKey[]).map((k) => {
                  const a = ACCENTS[k];
                  const active = app.settings.accent === k;
                  return (
                    <button
                      key={k}
                      onClick={() => app.updateSettings({ accent: k })}
                      className={`rounded-xl border p-3 text-center transition-all ${
                        active
                          ? 'border-white/25 bg-white/[0.05]'
                          : 'border-white/[0.07] bg-white/[0.02] hover:bg-white/[0.04]'
                      }`}
                    >
                      <span
                        className={`mx-auto block w-7 h-7 rounded-full bg-gradient-to-br ${a.gradient}`}
                      />
                      <span className="mt-2 block text-[11px] text-zinc-300">{a.label}</span>
                    </button>
                  );
                })}
              </div>
              <InfoBox>
                Sobre: {BRAND.tagline}. Este shell é clonável e reutilizável com qualquer backend —
                basta apontar a URL e remapear o contrato de endpoints. Nenhuma lógica de negócio
                vive na UI.
              </InfoBox>
            </>
          )}
        </div>
      </aside>
    </>
  );
}
