// src/projects/reframe/api/reframeApi.ts
const BASE_URL = import.meta.env.VITE_REFRAME_API_URL || import.meta.env.VITE_REFAME_API_URL || 'http://localhost:8000';

export class ApiError extends Error {
  code: string;
  detail?: string;

  constructor(message: string, code = 'PIPELINE_ERROR', detail?: string) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.detail = detail;
  }
}

async function parseError(res: Response): Promise<ApiError> {
  try {
    const body = await res.json();
    const detail = body?.detail;

    if (detail && typeof detail === 'object') {
      return new ApiError(
        detail.message || `HTTP ${res.status}`,
        detail.code || 'VALIDATION_ERROR',
        detail.fields ? `Campos inválidos: ${detail.fields.join(', ')}` : undefined
      );
    }
    if (typeof detail === 'string') return new ApiError(detail);
    if (typeof body?.message === 'string') {
      return new ApiError(body.message, body.code || 'PIPELINE_ERROR');
    }
  } catch {
    /* corpo não-JSON */
  }
  return new ApiError(`HTTP ${res.status}`);
}

export interface Lead {
  id: string;
  name: string;
  niche: string;
  city: string;
  phone: string;
  place_id?: string;
  created_at: string;
}

export interface Generation {
  id: string;
  lead_id: string;
  status: 'queued' | 'generating' | 'rendering' | 'publishing' | 'published' | 'failed';
  archetype_name?: string;
  personality?: string;
  position?: string;
  primary_color?: string;
  hero_image?: string;
  proofs: string[];
  headline?: string;
  subheadline?: string;
  cta?: string;
  url?: string;
  error?: { code: string; message: string; detail?: string };
  created_at: string;
  updated_at: string;
}

export interface ProjectInfo {
  id: string;
  name: string;
  status: string;
  environment: string;
  version: string;
}

export const reframeApi = {
  // Project
  async getProject(): Promise<ProjectInfo> {
    const res = await fetch(`${BASE_URL}/api/project`);
    if (!res.ok) throw new Error('Failed to fetch project');
    return res.json();
  },

  // Leads
  async getLeads(): Promise<Lead[]> {
    const res = await fetch(`${BASE_URL}/api/leads`);
    if (!res.ok) throw new Error('Failed to fetch leads');
    return res.json();
  },

  async createLead(lead: Omit<Lead, 'id' | 'created_at'>): Promise<Lead> {
    const res = await fetch(`${BASE_URL}/api/leads`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(lead),
    });
    if (!res.ok) throw new Error('Failed to create lead');
    return res.json();
  },

  async getLead(id: string): Promise<Lead> {
    const res = await fetch(`${BASE_URL}/api/leads/${id}`);
    if (!res.ok) throw new Error('Failed to fetch lead');
    return res.json();
  },

  // Demo: cria lead + geração em um único passo (contrato real da API: 2 chamadas)
  async generateDemo(data: {
    name: string;
    niche: string;
    city: string;
    phone: string;
    place_id?: string;
  }): Promise<{ lead: Lead; generation: Generation }> {
    const lead = await this.createLead(data);
    const generation = await this.createGeneration(lead.id);
    return { lead, generation };
  },

  // Generations
  async getGenerations(): Promise<Generation[]> {
    const res = await fetch(`${BASE_URL}/api/generations`);
    if (!res.ok) throw new Error('Failed to fetch generations');
    return res.json();
  },

  async createGeneration(leadId: string): Promise<Generation> {
    const res = await fetch(`${BASE_URL}/api/generations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lead_id: leadId }),
    });
    if (!res.ok) throw await parseError(res);
    return res.json();
  },

  async getGeneration(id: string): Promise<Generation> {
    try {
      const res = await fetch(`${BASE_URL}/api/generations/${id}`);
      if (!res.ok) {
        throw await parseError(res);
      }
      return res.json();
    } catch (err) {
      if (err instanceof ApiError) throw err;
      throw new ApiError(err instanceof Error ? err.message : 'Falha ao buscar geração', 'PIPELINE_ERROR');
    }
  },

  // Polling com retry e backoff
  async pollGeneration(
    id: string,
    onUpdate: (gen: Generation) => void,
    intervalMs: number = 1500,
    maxAttempts: number = 100
  ): Promise<void> {
    let attempts = 0;
    let isComplete = false;

    while (!isComplete && attempts < maxAttempts) {
      try {
        const gen = await this.getGeneration(id);
        onUpdate(gen);

        if (['published', 'failed'].includes(gen.status)) {
          isComplete = true;
          break;
        }

        attempts++;
        await new Promise((resolve) => setTimeout(resolve, intervalMs));
      } catch (err) {
        // Se falhar, espera e tenta novamente
        attempts++;
        await new Promise((resolve) => setTimeout(resolve, intervalMs * 2));
      }
    }
  },
};
