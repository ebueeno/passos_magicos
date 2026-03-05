"""
Testes da API POST /predict (skill_qa_tester.md).
Mock do RAG para não consumir tokens OpenAI; valida HTTP 200 e estrutura da resposta.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from src.rag_engine import AlunoNaoEncontradoError

RESPOSTA_MOCK = "Resposta mockada para avaliação."
DOCUMENTOS_MOCK = ["Chunk 2023: INDE Ágata, IDA 6.5.", "Chunk 2024: IAA em evolução."]


@pytest.fixture
def client():
    return TestClient(app)


@patch("app.routes.get_rag")
def test_predict_retorna_200_e_estrutura_correta(mock_get_rag, client):
    """POST /predict retorna 200 e body com 'resposta' e 'documentos_usados' (mock do RAG, sem OpenAI)."""
    mock_rag = MagicMock()
    mock_rag.query.return_value = (RESPOSTA_MOCK, DOCUMENTOS_MOCK)
    mock_get_rag.return_value = mock_rag

    response = client.post(
        "/predict",
        json={"aluno_id": "123", "pergunta": "Como está o aluno?"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "resposta" in data
    assert data["resposta"] == RESPOSTA_MOCK
    assert "documentos_usados" in data
    assert data["documentos_usados"] == DOCUMENTOS_MOCK
    mock_rag.query.assert_called_once_with(aluno_id="123", pergunta="Como está o aluno?")


@patch("app.routes.get_rag")
def test_predict_retorna_404_quando_aluno_nao_encontrado(mock_get_rag, client):
    """POST /predict retorna 404 quando RAG levanta AlunoNaoEncontradoError."""
    mock_rag = MagicMock()
    mock_rag.query.side_effect = AlunoNaoEncontradoError("Nenhum documento para RA 999")
    mock_get_rag.return_value = mock_rag

    response = client.post(
        "/predict",
        json={"aluno_id": "999", "pergunta": "Histórico do aluno?"},
    )

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Aluno não encontrado no banco."


def test_predict_valida_body(client):
    """POST /predict com body inválido (falta aluno_id ou pergunta) retorna 422."""
    response = client.post("/predict", json={})
    assert response.status_code == 422

    response = client.post("/predict", json={"aluno_id": "1"})
    assert response.status_code == 422

    response = client.post("/predict", json={"pergunta": "Só pergunta"})
    assert response.status_code == 422
