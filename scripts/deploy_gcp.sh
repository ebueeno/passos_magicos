#!/usr/bin/env bash
# =============================================================================
# deploy_gcp.sh — Copiloto PEDE  |  GCP Compute Engine deployment
# =============================================================================
# Deploys the full stack (FastAPI + ChromaDB + Langfuse + PostgreSQL) to a
# single GCE VM using Docker Compose. Run from the project root.
#
# Usage:
#   export GCP_PROJECT_ID="your-project-id"
#   export OPENAI_API_KEY="sk-..."
#   export LANGFUSE_PUBLIC_KEY="pk-lf-..."   # optional — monitoring only
#   export LANGFUSE_SECRET_KEY="sk-lf-..."   # optional — monitoring only
#   bash scripts/deploy_gcp.sh [--data-file path/to/planilha.xlsx]
#
# Optional flags:
#   --data-file FILE   Upload FILE and run the ingestion pipeline after deploy.
#   --zone ZONE        GCE zone (default: us-central1-a).
#   --machine-type MT  Machine type (default: e2-standard-2 / 2vCPU 8GB).
#   --vm-name NAME     VM instance name (default: passos-magicos-vm).
#   --skip-vm          Skip VM creation (redeploy to an existing VM).
#   --skip-build       Skip docker image rebuild (--no-build flag).
# =============================================================================

set -euo pipefail

# ── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'
BOLD='\033[1m'; RESET='\033[0m'

log()  { echo -e "${CYAN}[deploy]${RESET} $*"; }
ok()   { echo -e "${GREEN}[ok]${RESET}    $*"; }
warn() { echo -e "${YELLOW}[warn]${RESET}  $*"; }
die()  { echo -e "${RED}[error]${RESET} $*" >&2; exit 1; }

# ── Defaults ─────────────────────────────────────────────────────────────────
ZONE="${GCP_ZONE:-us-central1-a}"
MACHINE_TYPE="${GCP_MACHINE_TYPE:-e2-standard-2}"
VM_NAME="${GCP_VM_NAME:-passos-magicos-vm}"
DISK_SIZE="50GB"
DISK_TYPE="pd-balanced"
FIREWALL_RULE="passos-magicos-allow"
DATA_FILE=""
SKIP_VM=false
SKIP_BUILD=false

# ── Arg parse ────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --data-file)   DATA_FILE="$2";      shift 2 ;;
    --zone)        ZONE="$2";           shift 2 ;;
    --machine-type) MACHINE_TYPE="$2";  shift 2 ;;
    --vm-name)     VM_NAME="$2";        shift 2 ;;
    --skip-vm)     SKIP_VM=true;        shift   ;;
    --skip-build)  SKIP_BUILD=true;     shift   ;;
    *) die "Unknown flag: $1. Run 'bash scripts/deploy_gcp.sh --help' for usage." ;;
  esac
done

# ── Pre-flight checks ────────────────────────────────────────────────────────
echo -e "\n${BOLD}╔══════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║   Copiloto PEDE — GCP Deploy                 ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════════╝${RESET}\n"

command -v gcloud  >/dev/null 2>&1 || die "gcloud CLI not found. Install: https://cloud.google.com/sdk/docs/install"
command -v openssl >/dev/null 2>&1 || die "openssl not found (needed for secret generation)."
command -v tar     >/dev/null 2>&1 || die "tar not found."

[[ -z "${GCP_PROJECT_ID:-}" ]] && die "GCP_PROJECT_ID is not set. Export it before running this script."
[[ -z "${OPENAI_API_KEY:-}" ]] && die "OPENAI_API_KEY is not set. Export it before running this script."

LANGFUSE_PUBLIC_KEY="${LANGFUSE_PUBLIC_KEY:-}"
LANGFUSE_SECRET_KEY="${LANGFUSE_SECRET_KEY:-}"
[[ -z "$LANGFUSE_PUBLIC_KEY" ]] && warn "LANGFUSE_PUBLIC_KEY not set — Langfuse traces will show as 'pending'."
[[ -z "$LANGFUSE_SECRET_KEY" ]] && warn "LANGFUSE_SECRET_KEY not set — Langfuse traces will show as 'pending'."

if [[ -n "$DATA_FILE" && ! -f "$DATA_FILE" ]]; then
  die "Data file not found: $DATA_FILE"
fi

# ── Step 1: GCP project + API ─────────────────────────────────────────────────
log "Step 1/8 — Configuring GCP project: ${BOLD}$GCP_PROJECT_ID${RESET}"
gcloud config set project "$GCP_PROJECT_ID"
gcloud services enable compute.googleapis.com --quiet
ok "Compute Engine API enabled."

# ── Step 2: Firewall rule ─────────────────────────────────────────────────────
log "Step 2/8 — Firewall rules (ports 8001=API, 3000=Langfuse)…"
if gcloud compute firewall-rules describe "$FIREWALL_RULE" --quiet 2>/dev/null; then
  ok "Firewall rule '$FIREWALL_RULE' already exists, skipping."
else
  gcloud compute firewall-rules create "$FIREWALL_RULE" \
    --allow=tcp:8001,tcp:3000 \
    --target-tags=passos-magicos \
    --description="Copiloto PEDE: FastAPI (8001) and Langfuse dashboard (3000)" \
    --quiet
  ok "Firewall rule created."
fi

# ── Step 3: VM creation ───────────────────────────────────────────────────────
if [[ "$SKIP_VM" == "true" ]]; then
  log "Step 3/8 — Skipping VM creation (--skip-vm flag set)."
else
  log "Step 3/8 — Creating VM: ${BOLD}$VM_NAME${RESET} ($MACHINE_TYPE, $ZONE, $DISK_SIZE $DISK_TYPE)…"

  if gcloud compute instances describe "$VM_NAME" --zone="$ZONE" --quiet 2>/dev/null; then
    warn "VM '$VM_NAME' already exists. Skipping creation. Use --skip-vm to suppress this warning."
  else
    # Write startup script to a temp file so multi-line content is preserved
    STARTUP_SCRIPT=$(mktemp /tmp/startup_script.XXXX.sh)
    cat > "$STARTUP_SCRIPT" << 'STARTUP_EOF'
#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive

apt-get update -y
apt-get install -y ca-certificates curl gnupg lsb-release

# Docker official repo
mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io \
                   docker-buildx-plugin docker-compose-plugin

systemctl enable docker
systemctl start docker

# Add default GCE user to docker group so we can run docker without sudo
# (GCE creates a user with UID 1000 on first SSH login; we patch both common names)
usermod -aG docker ubuntu 2>/dev/null || true
# Mark completion
touch /var/lib/cloud/instance/startup_done
STARTUP_EOF

    gcloud compute instances create "$VM_NAME" \
      --machine-type="$MACHINE_TYPE" \
      --zone="$ZONE" \
      --image-family=ubuntu-2204-lts \
      --image-project=ubuntu-os-cloud \
      --boot-disk-size="$DISK_SIZE" \
      --boot-disk-type="$DISK_TYPE" \
      --tags=passos-magicos \
      --metadata-from-file=startup-script="$STARTUP_SCRIPT" \
      --quiet

    rm -f "$STARTUP_SCRIPT"
    ok "VM created."
  fi
fi

# ── Wait for VM SSH + Docker ──────────────────────────────────────────────────
log "Waiting for VM to accept SSH and Docker to be installed (up to 5 min)…"
ATTEMPTS=0
MAX_ATTEMPTS=20
until gcloud compute ssh "$VM_NAME" --zone="$ZONE" \
    --command="docker --version" \
    --ssh-flag="-o StrictHostKeyChecking=no" \
    --ssh-flag="-o ConnectTimeout=10" \
    --quiet 2>/dev/null; do
  ATTEMPTS=$((ATTEMPTS + 1))
  [[ $ATTEMPTS -ge $MAX_ATTEMPTS ]] && die "VM did not become ready after $((MAX_ATTEMPTS * 15))s. Check startup logs: gcloud compute instances get-serial-port-output $VM_NAME --zone=$ZONE"
  echo "  Attempt $ATTEMPTS/$MAX_ATTEMPTS — waiting 15s…"
  sleep 15
done
ok "VM is ready. Docker is installed."

# ── Step 4: Get external IP ───────────────────────────────────────────────────
log "Step 4/8 — Retrieving VM external IP…"
VM_EXTERNAL_IP=$(gcloud compute instances describe "$VM_NAME" \
  --zone="$ZONE" \
  --format="get(networkInterfaces[0].accessConfigs[0].natIP)")
[[ -z "$VM_EXTERNAL_IP" ]] && die "Could not retrieve external IP for VM '$VM_NAME'."
ok "External IP: ${BOLD}$VM_EXTERNAL_IP${RESET}"

# ── Step 5: Generate production secrets ──────────────────────────────────────
log "Step 5/8 — Generating Langfuse production secrets…"
NEXTAUTH_SECRET=$(openssl rand -base64 32)
SALT=$(openssl rand -base64 32)
ENCRYPTION_KEY=$(openssl rand -hex 32)   # must be exactly 64 hex chars
ok "Secrets generated."

# ── Step 6: Build & transfer deployment package ───────────────────────────────
log "Step 6/8 — Packaging project (excluding .env, __pycache__, chroma_db binaries, .git)…"
DEPLOY_ARCHIVE=$(mktemp /tmp/passos_magicos_deploy.XXXX.tar.gz)

tar czf "$DEPLOY_ARCHIVE" \
  --exclude='./.env' \
  --exclude='./.env.*' \
  --exclude='./__pycache__' \
  --exclude='*/__pycache__' \
  --exclude='*/*.pyc' \
  --exclude='*.pyc' \
  --exclude='./.pytest_cache' \
  --exclude='*/.pytest_cache' \
  --exclude='./.git' \
  --exclude='./.cursor' \
  --exclude='./app/model/chroma_db' \
  --exclude='./venv' \
  --exclude='./.venv' \
  --exclude='*.xlsx' \
  --exclude='*.xls' \
  --exclude='./htmlcov' \
  --exclude='./.coverage' \
  -C "$(pwd)" .

ok "Archive created: $(du -sh "$DEPLOY_ARCHIVE" | cut -f1)"

log "  Uploading archive to VM…"
gcloud compute scp "$DEPLOY_ARCHIVE" "$VM_NAME":~/passos_magicos_deploy.tar.gz \
  --zone="$ZONE" --quiet
rm -f "$DEPLOY_ARCHIVE"

log "  Extracting archive on VM…"
gcloud compute ssh "$VM_NAME" --zone="$ZONE" --quiet --command="
  set -e
  rm -rf ~/passos_magicos
  mkdir -p ~/passos_magicos
  tar xzf ~/passos_magicos_deploy.tar.gz -C ~/passos_magicos
  rm ~/passos_magicos_deploy.tar.gz
  mkdir -p ~/passos_magicos/app/model/chroma_db
  mkdir -p ~/passos_magicos/data
  echo 'Extraction complete.'
"
ok "Project files deployed."

# ── Step 7: Inject .env on VM ─────────────────────────────────────────────────
log "Step 7/8 — Writing .env to VM (secrets never stored locally)…"
ENV_TMPFILE=$(mktemp /tmp/.env_pede.XXXX)
cat > "$ENV_TMPFILE" << ENVEOF
# Copiloto PEDE — production .env (generated by deploy_gcp.sh)
OPENAI_API_KEY=${OPENAI_API_KEY}

LANGFUSE_PUBLIC_KEY=${LANGFUSE_PUBLIC_KEY}
LANGFUSE_SECRET_KEY=${LANGFUSE_SECRET_KEY}

# Langfuse self-hosted secrets — do NOT reuse dev values
NEXTAUTH_SECRET=${NEXTAUTH_SECRET}
SALT=${SALT}
ENCRYPTION_KEY=${ENCRYPTION_KEY}

# VM external IP — used by docker-compose.gcp.yml for NEXTAUTH_URL
VM_EXTERNAL_IP=${VM_EXTERNAL_IP}

ENVIRONMENT=production
ENVEOF

gcloud compute scp "$ENV_TMPFILE" "$VM_NAME":~/passos_magicos/.env \
  --zone="$ZONE" --quiet
# Restrict permissions immediately after transfer
gcloud compute ssh "$VM_NAME" --zone="$ZONE" --quiet --command="chmod 600 ~/passos_magicos/.env"
rm -f "$ENV_TMPFILE"
ok ".env written to VM (local temp file deleted)."

# ── Step 8: Start stack ───────────────────────────────────────────────────────
BUILD_FLAG="--build"
[[ "$SKIP_BUILD" == "true" ]] && BUILD_FLAG=""

log "Step 8/8 — Starting Docker Compose stack (this may take 3–5 min on first run)…"
gcloud compute ssh "$VM_NAME" --zone="$ZONE" --quiet --command="
  cd ~/passos_magicos
  sudo docker compose \
    -f docker-compose.yml \
    -f docker-compose.prod.yml \
    -f docker-compose.gcp.yml \
    up -d $BUILD_FLAG
"
ok "Stack started."

# ── Wait for API to be healthy ────────────────────────────────────────────────
log "Waiting for API to be reachable (up to 8 min — Langfuse migrations take ~2–3 min)…"
ATTEMPTS=0
MAX_ATTEMPTS=32
until gcloud compute ssh "$VM_NAME" --zone="$ZONE" --quiet \
    --command="curl -sf http://localhost:8001/docs > /dev/null 2>&1"; do
  ATTEMPTS=$((ATTEMPTS + 1))
  [[ $ATTEMPTS -ge $MAX_ATTEMPTS ]] && {
    warn "API did not become healthy in time. Check logs with:"
    warn "  gcloud compute ssh $VM_NAME --zone=$ZONE --command='sudo docker compose -f ~/passos_magicos/docker-compose.yml logs --tail=50'"
    break
  }
  echo "  Attempt $ATTEMPTS/$MAX_ATTEMPTS — waiting 15s…"
  sleep 15
done
ok "API is reachable."

# ── Optional: data ingestion ─────────────────────────────────────────────────
if [[ -n "$DATA_FILE" ]]; then
  log "Uploading data file and running ingestion via POST /upload…"
  DATA_BASENAME=$(basename "$DATA_FILE")
  gcloud compute scp "$DATA_FILE" "$VM_NAME":~/passos_magicos/data/"$DATA_BASENAME" \
    --zone="$ZONE" --quiet
  ok "Data file transferred to VM."
  log "  Calling POST /upload on the API (may take 1–2 min for embeddings)…"
  INGEST_RESULT=$(gcloud compute ssh "$VM_NAME" --zone="$ZONE" --quiet --command="
    curl -sf -X POST http://localhost:8001/upload \
      -F \"file=@\$HOME/passos_magicos/data/$DATA_BASENAME\"
  " 2>&1)
  echo "$INGEST_RESULT"
  ok "Data ingestion complete."
else
  warn "No --data-file provided. Run ingestion manually after deploy:"
  warn "  gcloud compute scp planilha.xlsx $VM_NAME:~/passos_magicos/data/ --zone=$ZONE"
  warn "  curl -X POST http://$VM_EXTERNAL_IP:8001/upload -F 'file=@planilha.xlsx'"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║   Deploy Complete!                                           ║${RESET}"
echo -e "${BOLD}╠══════════════════════════════════════════════════════════════╣${RESET}"
echo -e "${BOLD}║${RESET}  VM:          ${BOLD}$VM_NAME${RESET} ($ZONE)"
echo -e "${BOLD}║${RESET}  API:         ${GREEN}http://$VM_EXTERNAL_IP:8001${RESET}"
echo -e "${BOLD}║${RESET}  Docs:        ${GREEN}http://$VM_EXTERNAL_IP:8001/docs${RESET}"
echo -e "${BOLD}║${RESET}  Langfuse:    ${GREEN}http://$VM_EXTERNAL_IP:3000${RESET}"
echo -e "${BOLD}╠══════════════════════════════════════════════════════════════╣${RESET}"
echo -e "${BOLD}║${RESET}  Quick test:"
echo -e "${BOLD}║${RESET}    curl -X POST http://$VM_EXTERNAL_IP:8001/predict \\"
echo -e "${BOLD}║${RESET}      -H 'Content-Type: application/json' \\"
echo -e "${BOLD}║${RESET}      -d '{\"aluno_id\": \"123\", \"pergunta\": \"Como está este aluno?\"}'"
echo -e "${BOLD}╠══════════════════════════════════════════════════════════════╣${RESET}"
echo -e "${BOLD}║${RESET}  Useful commands:"
echo -e "${BOLD}║${RESET}    # Tail logs"
echo -e "${BOLD}║${RESET}    gcloud compute ssh $VM_NAME --zone=$ZONE --command='cd ~/passos_magicos && sudo docker compose logs -f api'"
echo -e "${BOLD}║${RESET}"
echo -e "${BOLD}║${RESET}    # Stop stack"
echo -e "${BOLD}║${RESET}    gcloud compute ssh $VM_NAME --zone=$ZONE --command='cd ~/passos_magicos && sudo docker compose down'"
echo -e "${BOLD}║${RESET}"
echo -e "${BOLD}║${RESET}    # SSH directly"
echo -e "${BOLD}║${RESET}    gcloud compute ssh $VM_NAME --zone=$ZONE"
echo -e "${BOLD}╚══════════════════════════════════════════════════════════════╝${RESET}"
echo ""
