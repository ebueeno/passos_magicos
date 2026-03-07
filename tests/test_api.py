"""
Testes da API POST /predict e POST /upload (skill_qa_tester.md).
Mock do RAG e do ChromaDB/ingest para não consumir OpenAI nem rede.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from src.rag_engine import AlunoNaoEncontradoError

RESPOSTA_MOCK = "Resposta mockada para avaliação."
DOCUMENTOS_MOCK = ["Chunk 2023: INDE Ágata, IDA 6.5.", "Chunk 2024: IAA em evolução."]

# CSV mínimo para POST /upload (colunas que process_uploaded_file mapeia)
CSV_MINIMO = b"RA,Idade,INDE 22\n1,14,5.5\n"


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


# --- POST /upload (mock de ingest_dataframe_to_chroma para não bater no ChromaDB) ---


@patch("app.routes.ingest_dataframe_to_chroma", return_value=1)
@patch("app.routes.UPLOAD_DIR", new_callable=lambda: Path(tempfile.mkdtemp()))
def test_upload_retorna_200_e_estrutura_correta(mock_upload_dir, mock_ingest, client):
    """POST /upload com CSV válido retorna 200, message e rows_ingested (mock do ChromaDB)."""
    response = client.post(
        "/upload",
        files={"file": ("planilha.csv", CSV_MINIMO, "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Upload e ingestão concluídos."
    assert "rows_ingested" in data
    assert data["rows_ingested"] == 1
    mock_ingest.assert_called_once()


def test_upload_retorna_422_extensao_invalida(client):
    """POST /upload com extensão não permitida (.txt) retorna 422."""
    response = client.post(
        "/upload",
        files={"file": ("arquivo.txt", b"conteudo", "text/plain")},
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert "Extensão inválida" in data["detail"] or "extensão" in data["detail"].lower()


@patch("app.routes.ingest_dataframe_to_chroma", side_effect=Exception("Chroma indisponível"))
@patch("app.routes.UPLOAD_DIR", new_callable=lambda: Path(tempfile.mkdtemp()))
def test_upload_retorna_500_quando_ingestao_falha(mock_upload_dir, mock_ingest, client):
    """POST /upload retorna 500 quando ingest_dataframe_to_chroma levanta exceção."""
    response = client.post(
        "/upload",
        files={"file": ("planilha.csv", CSV_MINIMO, "text/csv")},
    )
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
