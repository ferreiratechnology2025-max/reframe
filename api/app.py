from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

app = FastAPI(
    title="Reframe API",
    version="1.0.0",
    description="API de integração entre UI e pipeline Reframe"
)

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev
        "http://localhost:3000",   # Next dev
        "http://localhost:4000",   # Shell dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Pipeline ──────────────────────────────────────────────

from api.pipeline_adapter import run_pipeline_task
from api.errors import ErrorCode, get_user_message

# ─── Models ────────────────────────────────────────────────

class Lead(BaseModel):
    id: str
    name: str
    niche: str
    city: str
    phone: str
    place_id: Optional[str] = None
    created_at: datetime = datetime.now()

class LeadCreate(BaseModel):
    name: str
    niche: str
    city: str
    phone: str
    place_id: Optional[str] = None

class GenerationStatus(BaseModel):
    id: str
    lead_id: str
    status: str = "queued"  # queued | generating | validating | rendering | publishing | published | failed
    archetype_name: Optional[str] = None
    personality: Optional[str] = None  # VisualTemplate.id (VS-2)
    position: Optional[str] = None  # MarketPosition.value (VS-1/VS-2)
    primary_color: Optional[str] = None
    hero_image: Optional[str] = None
    proofs: List[str] = []
    headline: Optional[str] = None
    subheadline: Optional[str] = None
    cta: Optional[str] = None
    url: Optional[str] = None
    error: Optional[dict] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

class GenerationCreate(BaseModel):
    lead_id: str

class ProjectInfo(BaseModel):
    id: str = "reframe"
    name: str = "Reframe"
    status: str = "online"
    environment: str = "production"
    version: str = "1.0.0"

# ─── Store (in-memory para MVP) ──────────────────────────

# Será substituído por banco de dados depois
leads_db: List[Lead] = []
generations_db: List[GenerationStatus] = []

# ─── Routes ────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "message": "Reframe API",
        "version": "1.0.0",
        "endpoints": [
            "/api/health",
            "/api/project",
            "/api/leads",
            "/api/leads/{id}",
            "/api/generations",
            "/api/generations/{id}"
        ]
    }

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/project")
async def get_project():
    return ProjectInfo()

@app.get("/api/r2/test")
async def test_r2_connection():
    """Testa a conexão com R2 (config + upload mínimo)."""
    try:
        from publisher import diagnose_r2_config
    except ImportError:
        return {
            "status": "error",
            "message": "publisher.py não encontrado no caminho do módulo"
        }

    try:
        config = diagnose_r2_config()

        # Verifica se todas as credenciais estão presentes
        missing = [k for k, v in config.items() if v == "MISSING"]

        # Campo de diagnóstico: verifica permissões com operações de leitura
        permissions = {}
        try:
            import boto3
            from botocore.config import Config
            import os as _os

            ak = _os.getenv('R2_ACCESS_KEY') or _os.getenv('CLOUDFLARE_ACCESS_KEY')
            sk = _os.getenv('R2_SECRET_KEY') or _os.getenv('CLOUDFLARE_SECRET_KEY')
            endpoint = _os.getenv('R2_ENDPOINT') or _os.getenv('CLOUDFLARE_ENDPOINT')
            bucket = _os.getenv('R2_BUCKET') or _os.getenv('CLOUDFLARE_BUCKET')

            if ak and sk and endpoint and bucket:
                s3 = boto3.Session(
                    aws_access_key_id=ak,
                    aws_secret_access_key=sk,
                ).client(
                    's3',
                    endpoint_url=endpoint,
                    config=Config(signature_version='s3v4'),
                    region_name='auto',
                )
                try:
                    s3.head_bucket(Bucket=bucket)
                    permissions['head_bucket'] = True
                except Exception as e:
                    permissions['head_bucket'] = str(e).split('\n')[0][:200]
                try:
                    s3.list_objects_v2(Bucket=bucket, MaxKeys=1)
                    permissions['list_objects'] = True
                except Exception as e:
                    permissions['list_objects'] = str(e).split('\n')[0][:200]
            else:
                permissions['error'] = "credenciais S3-compatible ausentes"
        except ImportError:
            permissions['error'] = "boto3 não instalado"
        except Exception as e:
            permissions['error'] = str(e)[:200]

        return {
            "status": "ok" if not missing else "error",
            "missing": missing,
            "account_id": config.get('CLOUDFLARE_ACCOUNT_ID')[:12] + "..." if config.get('CLOUDFLARE_ACCOUNT_ID') != 'MISSING' else None,
            "bucket": config.get('R2_BUCKET'),
            "endpoint": config.get('R2_ENDPOINT') if config.get('R2_ENDPOINT') != 'MISSING' else None,
            "permissions": permissions,
            "message": (
                f"Credenciais faltando: {', '.join(missing)}" if missing
                else "Config OK. Execute api/test_r2_upload.py para o teste de escrita."
            )
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/api/leads")
async def get_leads():
    return leads_db

@app.post("/api/leads")
async def create_lead(lead: LeadCreate):
    new_lead = Lead(
        id=f"lead_{uuid.uuid4().hex[:8]}",
        name=lead.name,
        niche=lead.niche,
        city=lead.city,
        phone=lead.phone,
        place_id=lead.place_id
    )
    leads_db.append(new_lead)
    return new_lead

@app.get("/api/leads/{lead_id}")
async def get_lead(lead_id: str):
    for lead in leads_db:
        if lead.id == lead_id:
            return lead
    raise HTTPException(status_code=404, detail="Lead not found")

@app.get("/api/generations")
async def get_generations():
    return generations_db

@app.post("/api/generations")
async def create_generation(
    gen: GenerationCreate,
    background_tasks: BackgroundTasks
):
    # Busca o lead
    lead = next((l for l in leads_db if l.id == gen.lead_id), None)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Valida os dados do lead antes de gerar
    invalid_fields = []
    if len(lead.name.strip()) < 3:
        invalid_fields.append("name")
    if len(lead.phone.strip()) < 8:
        invalid_fields.append("phone")
    if invalid_fields:
        raise HTTPException(
            status_code=400,
            detail={
                "code": ErrorCode.INVALID_LEAD,
                "message": get_user_message(ErrorCode.INVALID_LEAD),
                "fields": invalid_fields,
            }
        )
    
    # Cria geração
    new_gen = GenerationStatus(
        id=f"gen_{uuid.uuid4().hex[:8]}",
        lead_id=gen.lead_id,
        status="queued"
    )
    generations_db.append(new_gen)
    
    # Adiciona tarefa em background
    background_tasks.add_task(run_pipeline_task, new_gen.id)
    
    return new_gen

@app.get("/api/generations/{gen_id}")
async def get_generation(gen_id: str):
    for gen in generations_db:
        if gen.id == gen_id:
            return gen
    raise HTTPException(status_code=404, detail="Generation not found")

# ─── Para desenvolvimento ─────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)