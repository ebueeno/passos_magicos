"""
Rotas da API Copiloto PEDE. Endpoints: POST /predict, POST /upload.
"""

import logging
import os
import uuid
from pathlib import Path

from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, UploadFile

from src.preprocessing import process_uploaded_file
from src.rag_engine import AlunoNaoEncontradoError, RAG
from src.train import ingest_dataframe_to_chroma

router = APIRouter()
logger = logging.getLogger(__name__)

# Diretório físico para uploads (bind mount no Docker: /app/data)
UPLOAD_DIR = Path("/app/data")
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}

# Instância única do RAG (Chromadb carregado uma vez)
_rag: RAG | None = None


def get_rag() -> RAG:
    global _rag
    if _rag is None:
        _rag = RAG()
    return _rag


class PredictRequest(BaseModel):
    """Body do POST /predict (skill_mlops_backend.md)."""

    aluno_id: str
    pergunta: str


class PredictResponse(BaseModel):
    """Resposta do POST /predict (resposta do LLM + documentos usados para rastreabilidade)."""

    resposta: str
    documentos_usados: list[str]


class UploadResponse(BaseModel):
    """Resposta do POST /upload."""

    message: str
    rows_ingested: int


@router.post("/upload", response_model=UploadResponse)
def upload(file: UploadFile) -> UploadResponse:
    """
    Recebe planilha (.csv ou .xlsx/.xls), salva em /app/data, aplica o Data Contract
    e faz upsert no ChromaDB via HTTP.
    """
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Extensão inválida. Permitidas: {', '.join(ALLOWED_EXTENSIONS)}",
        )
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}{suffix}"
    file_path = UPLOAD_DIR / safe_name
    try:
        contents = file.file.read()
        file_path.write_bytes(contents)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao salvar arquivo: {e!s}",
        ) from e
    try:
        df = process_uploaded_file(str(file_path))
        count = ingest_dataframe_to_chroma(df)
        return UploadResponse(
            message="Upload e ingestão concluídos.",
            rows_ingested=count,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar ou ingerir dados: {e!s}",
        ) from e


@router.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest) -> PredictResponse:
    """
    Invoca o RAG com o RA do aluno e a pergunta do professor.
    Retorna 404 se o aluno não existir no banco vetorial.
    """
    try:
        rag = get_rag()
        resposta, documentos_usados = rag.query(
            aluno_id=request.aluno_id, pergunta=request.pergunta
        )
        return PredictResponse(resposta=resposta, documentos_usados=documentos_usados)
    except AlunoNaoEncontradoError:
        raise HTTPException(
            status_code=404,
            detail="Aluno não encontrado no banco.",
        )
    except Exception as e:
        logger.exception("Erro ao processar POST /predict")
        detail = "Erro interno ao processar a solicitação."
        if os.getenv("ENVIRONMENT") == "development":
            detail += f" ({e!s})"
        raise HTTPException(
            status_code=500,
            detail=detail,
        ) from e
