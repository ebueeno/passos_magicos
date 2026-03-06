"""
Testes do pipeline de treino (build_and_persist_chroma). HyDE: documentos com parent_content.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.train import (
    DOC_TYPE_HYDE,
    DOC_TYPE_KEY,
    HYDE_PARENT_CONTENT_KEY,
    build_and_persist_chroma,
)


@pytest.fixture
def df_mini():
    """DataFrame mínimo com colunas obrigatórias PEDE."""
    return pd.DataFrame([
        {"RA": "1", "ANO_PESQUISA": "2024", "FASE": "8", "INDE": "Ágata", "IDA": 6.5},
    ])


@patch("src.train.Chroma.from_documents")
@patch("src.train.OpenAIEmbeddings")
@patch("src.train.ChatOpenAI")
@patch("src.train._generate_hyde_questions_for_chunk")
def test_build_and_persist_chroma_hyde_adiciona_docs_com_parent_content(mock_hyde_gen, mock_llm_cls, mock_emb_cls, mock_from_docs, df_mini):
    """Com use_hyde=True, Chroma recebe documentos HyDE com RA, ANO, doc_type e parent_content."""
    mock_hyde_gen.return_value = ["Qual o desempenho em 2024?", "Como está o INDE?"]
    mock_emb_cls.return_value = MagicMock()

    captured_docs = []

    def capture_docs(documents, **kwargs):
        captured_docs.extend(documents)
        return MagicMock()

    mock_from_docs.side_effect = capture_docs

    build_and_persist_chroma(df_mini, use_hyde=True, hyde_questions_per_chunk=2)

    chunk_docs = [d for d in captured_docs if d.metadata.get(DOC_TYPE_KEY) != DOC_TYPE_HYDE]
    hyde_docs = [d for d in captured_docs if d.metadata.get(DOC_TYPE_KEY) == DOC_TYPE_HYDE]
    assert len(chunk_docs) >= 1
    assert len(hyde_docs) >= 1
    for d in hyde_docs:
        assert d.metadata.get("RA") is not None
        assert d.metadata.get("ANO") is not None
        assert d.metadata.get(DOC_TYPE_KEY) == DOC_TYPE_HYDE
        assert d.metadata.get(HYDE_PARENT_CONTENT_KEY, "").strip() != ""
