# Copiloto PEDE — GCP Deployment Guide

This guide covers deploying the full stack (FastAPI + ChromaDB + Langfuse + PostgreSQL)
to a single **Google Compute Engine** VM using Docker Compose via the `gcloud` CLI.

---

## Architecture

```
Internet
  │  TCP 8001 → FastAPI /predict, /upload
  │  TCP 3000 → Langfuse dashboard
  ▼
GCP Firewall (passos-magicos-allow)
  ▼
GCE VM: e2-standard-2 · 2 vCPU · 8 GB RAM · 50 GB SSD (us-central1-a)
  ├── api          :8001  FastAPI (uvicorn --workers 4)
  ├── chromadb     :8000  ChromaDB HTTP server   [internal only]
  ├── langfuse-server :3000  Langfuse v2 dashboard
  └── langfuse-db         PostgreSQL 15           [internal only]
```

**Sizing rationale:**

| Component | RAM estimate |
|---|---|
| sentence-transformers cross-encoder reranker | ~1.2 GB |
| ChromaDB in-memory index (~3 600 PEDE chunks) | ~500 MB |
| Langfuse Next.js server | ~512 MB |
| FastAPI (4 workers) + PostgreSQL | ~750 MB |
| **Total** | **~3 GB** → `e2-standard-2` (8 GB) gives 2× headroom |

---

## Prerequisites

### 1. Google Cloud SDK

```bash
# Install: https://cloud.google.com/sdk/docs/install
gcloud --version   # must be ≥ 400.0.0
gcloud auth login
```

### 2. GCP Project with billing

```bash
gcloud projects list           # find your project ID
gcloud config set project YOUR_PROJECT_ID
```

### 3. API keys

| Variable | Where to get it | Required |
|---|---|---|
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys | **Yes** |
| `LANGFUSE_PUBLIC_KEY` | Langfuse dashboard → Settings → API Keys | No (traces show "pending") |
| `LANGFUSE_SECRET_KEY` | Same as above | No |

---

## Quick Deploy (single command)

```bash
# Clone / enter project
cd passos_magicos

# Export required secrets
export GCP_PROJECT_ID="your-project-id"
export OPENAI_API_KEY="sk-..."
export LANGFUSE_PUBLIC_KEY=""   # optional
export LANGFUSE_SECRET_KEY=""   # optional

# Deploy — takes ~5–8 min on first run (Docker image build + Langfuse migrations)
bash scripts/deploy_gcp.sh

# With data ingestion in one go:
bash scripts/deploy_gcp.sh --data-file "BASE DE DADOS PEDE 2024 - DATATHON.xlsx"
```

The script prints the external IP and all useful URLs at the end.

---

## What the Script Does (step by step)

| Step | Action |
|---|---|
| 1 | Sets GCP project, enables Compute Engine API |
| 2 | Creates firewall rule opening TCP 8001 and 3000 |
| 3 | Creates `e2-standard-2` VM with Ubuntu 22.04 and a startup script that installs Docker |
| Wait | Polls SSH until Docker is available (≤5 min) |
| 4 | Retrieves the VM's external IP |
| 5 | Generates cryptographically random Langfuse secrets (`NEXTAUTH_SECRET`, `SALT`, `ENCRYPTION_KEY`) |
| 6 | Tarballs the project (excluding `.env`, `__pycache__`, `chroma_db` binaries, `.git`) and SCPs the archive to the VM |
| 7 | Writes `.env` directly to the VM via SCP — **the file never sits on disk locally** |
| 8 | Runs `docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.gcp.yml up -d --build` |
| Wait | Polls `http://localhost:8001/docs` until the API responds (≤8 min) |
| Optional | If `--data-file` is provided, SCPs the file and runs `run_pipeline.py` inside the container |

---

## Docker Compose Layering

```
docker-compose.yml          # base: services, networks, volumes, healthchecks
docker-compose.prod.yml     # prod: --workers 4, restart: always
docker-compose.gcp.yml      # gcp:  NEXTAUTH_URL with real IP, hardened secrets,
                            #       chromadb bound to 127.0.0.1 only
```

---

## Manual Operations After Deploy

### Ingest data

```bash
# Copy data file to VM
gcloud compute scp "planilha.xlsx" passos-magicos-vm:~/passos_magicos/data/ --zone=us-central1-a

# Run pipeline inside API container
gcloud compute ssh passos-magicos-vm --zone=us-central1-a \
  --command="cd ~/passos_magicos && sudo docker compose exec api python run_pipeline.py data/planilha.xlsx"
```

### Upload via API (alternative)

```bash
curl -X POST http://EXTERNAL_IP:8001/upload \
  -F "file=@planilha.xlsx"
```

### Test a prediction

```bash
curl -X POST http://EXTERNAL_IP:8001/predict \
  -H "Content-Type: application/json" \
  -d '{"aluno_id": "123", "pergunta": "Quais indicadores devo priorizar com este aluno?"}'
```

### View logs

```bash
gcloud compute ssh passos-magicos-vm --zone=us-central1-a \
  --command="cd ~/passos_magicos && sudo docker compose logs -f api"
```

### Redeploy after code changes

```bash
# Re-run the script with --skip-vm to skip VM creation
bash scripts/deploy_gcp.sh --skip-vm
```

### Stop / restart stack

```bash
# SSH in
gcloud compute ssh passos-magicos-vm --zone=us-central1-a

# On the VM:
cd ~/passos_magicos
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.gcp.yml down
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.gcp.yml up -d
```

---

## Script Flags Reference

```
bash scripts/deploy_gcp.sh [OPTIONS]

Options:
  --data-file FILE     Upload FILE and run ingestion after deploy
  --zone ZONE          GCE zone (default: us-central1-a)
  --machine-type TYPE  Machine type (default: e2-standard-2)
  --vm-name NAME       Instance name (default: passos-magicos-vm)
  --skip-vm            Skip VM creation (use for redeployments)
  --skip-build         Skip docker image rebuild

Environment variables:
  GCP_PROJECT_ID       (required)
  OPENAI_API_KEY       (required)
  LANGFUSE_PUBLIC_KEY  (optional)
  LANGFUSE_SECRET_KEY  (optional)
  GCP_ZONE             Override default zone
  GCP_MACHINE_TYPE     Override default machine type
  GCP_VM_NAME          Override default VM name
```

---

## Cost Estimate (GCP us-central1)

| Resource | Monthly cost |
|---|---|
| `e2-standard-2` VM (730 h) | ~$49 |
| 50 GB `pd-balanced` SSD | ~$5 |
| Network egress (light usage) | ~$1 |
| **Total** | **~$55/month** |

GCP credits are applied automatically. The VM can be stopped when not in use to save costs:

```bash
gcloud compute instances stop passos-magicos-vm --zone=us-central1-a
gcloud compute instances start passos-magicos-vm --zone=us-central1-a
```

---

## Troubleshooting

**API container exits immediately**

```bash
gcloud compute ssh passos-magicos-vm --zone=us-central1-a \
  --command="cd ~/passos_magicos && sudo docker compose logs api"
# Most likely cause: OPENAI_API_KEY missing or invalid in .env
```

**Langfuse shows "pending" traces**

Set `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` in your environment and redeploy with `--skip-vm`.

**ChromaDB connection refused inside API**

The ChromaDB service is only accessible on the internal `rag_network`. Check `CHROMA_HOST=chromadb` is set in the running container:

```bash
gcloud compute ssh passos-magicos-vm --zone=us-central1-a \
  --command="cd ~/passos_magicos && sudo docker compose exec api env | grep CHROMA"
```

**Langfuse 404 on span export (SDK version mismatch)**

Ensure `requirements.txt` has `langfuse>=2.0.0,<3.0.0`. The Langfuse v2 server does not expose the OTEL endpoint required by SDK v3.

**sentence-transformers first-start is slow**

The cross-encoder reranker model (~420 MB) is downloaded on the first container start. This is normal and only happens once (Docker volume cache persists across restarts).
