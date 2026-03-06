"""
Testes unitários do motor RAG avançado (Self-Query, híbrido, reranking, opcionais).
Mock de Chroma/LLM para não depender de banco ou OpenAI em CI.
"""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

from src.rag_engine import (
    AlunoNaoEncontradoError,
    RAG,
    _build_filter,
    _merge_and_dedupe_docs,
    _resolve_hyde_content,
)


def test_build_filter_somente_ra():
    """Filtro sem ano deve retornar apenas RA."""
    assert _build_filter("123", None) == {"RA": "123"}


def test_build_filter_ra_e_ano():
    """Filtro com ano deve retornar $and com RA e ANO."""
    got = _build_filter("456", "2024")
    assert got == {"$and": [{"RA": "456"}, {"ANO": "2024"}]}


def test_merge_and_dedupe_docs_deduplica_por_conteudo():
    """_merge_and_dedupe_docs junta listas e deduplica por page_content."""
    d1 = Document(page_content="chunk A", metadata={})
    d2 = Document(page_content="chunk B", metadata={})
    d3 = Document(page_content="chunk A", metadata={"x": 1})
    list1 = [d1, d2]
    list2 = [d3, d2]
    got = _merge_and_dedupe_docs([list1, list2], max_docs=10)
    assert len(got) == 2
    assert got[0].page_content == "chunk A"
    assert got[1].page_content == "chunk B"


def test_merge_and_dedupe_docs_respeita_max_docs():
    """_merge_and_dedupe_docs limita ao max_docs."""
    list1 = [Document(page_content=f"c{i}", metadata={}) for i in range(3)]
    list2 = [Document(page_content=f"d{i}", metadata={}) for i in range(3)]
    got = _merge_and_dedupe_docs([list1, list2], max_docs=4)
    assert len(got) == 4


def test_resolve_hyde_content_retorna_parent_content_quando_presente():
    """Com USE_HYDE, doc com parent_content retorna o chunk pai."""
    with patch("src.rag_engine.USE_HYDE", True):
        doc = Document(
            page_content="Pergunta hipotética?",
            metadata={"parent_content": "Conteúdo do chunk pai.", "doc_type": "hyde"},
        )
        assert _resolve_hyde_content(doc) == "Conteúdo do chunk pai."


def test_resolve_hyde_content_retorna_page_content_sem_hyde():
    """Sem parent_content, retorna page_content."""
    with patch("src.rag_engine.USE_HYDE", True):
        doc = Document(page_content="Chunk normal", metadata={})
        assert _resolve_hyde_content(doc) == "Chunk normal"
    with patch("src.rag_engine.USE_HYDE", False):
        doc = Document(page_content="Chunk", metadata={"parent_content": "Parent"})
        assert _resolve_hyde_content(doc) == "Chunk"


@patch("src.rag_engine.Chroma")
def test_rag_query_levanta_aluno_nao_encontrado_quando_sem_docs(mock_chroma_cls):
    """RAG.query deve levantar AlunoNaoEncontradoError quando não há documentos para o RA."""
    mock_vs = MagicMock()
    mock_vs.get.return_value = {"ids": [], "metadatas": [], "documents": []}
    mock_chroma_cls.return_value = mock_vs

    with patch("src.rag_engine.OpenAIEmbeddings"), patch(
        "src.rag_engine.ChatOpenAI"
    ) as mock_llm_cls:
        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm
        rag = RAG()

    with pytest.raises(AlunoNaoEncontradoError) as exc_info:
        rag.query(aluno_id="999", pergunta="Como está o aluno?")

    assert "999" in str(exc_info.value)


@patch("src.rag_engine.Chroma")
@patch("src.rag_engine.USE_HYDE", True)
def test_rag_query_usa_parent_content_em_documentos_usados_quando_hyde(mock_chroma_cls):
    """Quando retriever retorna doc HyDE (parent_content), documentos_usados usa o chunk pai."""
    mock_vs = MagicMock()
    mock_vs.get.return_value = {
        "ids": ["id1"],
        "metadatas": [{"RA": "1", "ANO": "2024", "doc_type": "hyde", "parent_content": "Histórico 2024 do aluno."}],
        "documents": ["Pergunta que bate com o chunk?"],
    }
    mock_chroma_cls.return_value = mock_vs

    with patch("src.rag_engine.OpenAIEmbeddings"), patch(
        "src.rag_engine.ChatOpenAI"
    ) as mock_llm_cls:
        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm
        rag = RAG()

    base_retriever = MagicMock()
    base_retriever.invoke.return_value = [
        Document(
            page_content="Pergunta que bate com o chunk?",
            metadata={"RA": "1", "doc_type": "hyde", "parent_content": "Histórico 2024 do aluno."},
        ),
    ]
    msg_resposta = MagicMock()
    msg_resposta.content = "Resposta baseada no histórico."
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = msg_resposta
    rag._chain = mock_chain
    with patch.object(rag, "_build_retriever", return_value=base_retriever), patch(
        "src.rag_engine._extract_ano_from_query", return_value=None
    ):
        resposta, documentos_usados = rag.query(aluno_id="1", pergunta="Como está em 2024?")
    assert documentos_usados == ["Histórico 2024 do aluno."]
    assert resposta == "Resposta baseada no histórico."
