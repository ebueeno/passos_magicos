"""
Rotas da API Copiloto PEDE. Endpoint obrigatório: POST /predict.
"""

from pydantic import BaseModel

from fastapi import APIRouter, HTTPException

from src.rag_engine import AlunoNaoEncontradoError, RAG

router = APIRouter()

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
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao processar a solicitação.",
        ) from e
