"""
Motor RAG avançado do Copiloto PEDE: Self-Query (metadata), busca híbrida (BM25 + vetorial),
reranking (cross-encoder), filtro obrigatório por RA, gpt-4o-mini e Langfuse (skill_mlops_backend.md).
Opcionais: query expansion, context compression (LLMChainExtractor), HyDE (perguntas hipotéticas).
"""

from __future__ import annotations

import os

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langfuse.langchain import CallbackHandler

# Busca híbrida e reranking (opcional por dependência)
try:
    from langchain_community.retrievers import BM25Retriever
    from langchain_community.retrievers import EnsembleRetriever
    from langchain.retrievers import ContextualCompressionRetriever
    from langchain_community.document_compressors import CrossEncoderReranker
    from langchain_community.cross_encoders import HuggingFaceCrossEncoder
    _HAS_ADVANCED_RAG = True
except ImportError:
    _HAS_ADVANCED_RAG = False

# LLMChainExtractor para context compression (opcional)
try:
    from langchain_community.document_compressors import LLMChainExtractor
    _HAS_LLM_EXTRACTOR = True
except ImportError:
    try:
        from langchain.retrievers.document_compressors.chain_extract import LLMChainExtractor
        _HAS_LLM_EXTRACTOR = True
    except ImportError:
        _HAS_LLM_EXTRACTOR = False


def _env_bool(key: str, default: bool = False) -> bool:
    v = os.environ.get(key, "").strip().lower()
    return v in ("1", "true", "yes", "on")


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except ValueError:
        return default


# Mesmo persist e coleção de src.train
PERSIST_DIR = "./app/model/chroma_db"
COLLECTION_NAME = "pede"

# Configuração do pipeline avançado
RETRIEVAL_K = 20
RERANK_TOP_N = 8
ENSEMBLE_WEIGHTS = [0.5, 0.5]
CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# Flags e parâmetros opcionais (env)
USE_QUERY_EXPANSION = _env_bool("RAG_QUERY_EXPANSION", False)
USE_CONTEXT_COMPRESSION = _env_bool("RAG_CONTEXT_COMPRESSION", False) and _HAS_LLM_EXTRACTOR
USE_HYDE = _env_bool("RAG_USE_HYDE", False)
QUERY_EXPANSION_N = max(2, min(5, _env_int("RAG_QUERY_EXPANSION_N", 3)))
HYDE_METADATA_KEY = "parent_content"
DOC_TYPE_KEY = "doc_type"
DOC_TYPE_HYDE = "hyde"

SYSTEM_PROMPT = """Você é um Psicopedagogo da Associação Passos Mágicos (PEDE). Seu papel é apoiar professores com planos de ação baseados no histórico do aluno, mitigando evasão e vulnerabilidade.

Use estritamente os indicadores do PEDE:
- INDE: Índice de Desenvolvimento Educacional (Pedras: Quartzo, Ágata, Ametista, Topázio).
- IDA: Desempenho Acadêmico (média das provas).
- IAN: Adequação de Nível (defasagem idade/série).
- IEG: Engajamento (lições de casa e participação).
- IAA: Autoavaliação (bem-estar; notas baixas exigem intervenção psicológica).
- IPS: Psicossocial (avaliação das psicólogas).
- IPP: Psicopedagógico (avaliação dos professores).
- IPV: Ponto de Virada (integração à ONG e maturidade).

Regras obrigatórias:
- Nota ZERO no IDA NÃO indica "baixa inteligência"; indique "vulnerabilidade de engajamento" e sugira aproximação do tutor.
- Alunos novos (sem histórico) passaram pelo Processo de Admissão (Prova de Sondagem, Entrevistas, Avaliação Socioeconômica).
- "Atingir o Ponto de Virada" significa maturidade emocional e consciência do valor da educação.

Responda com base APENAS no contexto fornecido (histórico do aluno). Seja objetivo e acionável para o professor."""


class AlunoNaoEncontradoError(Exception):
    """Aluno (RA) não possui documentos no banco vetorial."""


def _build_filter(aluno_id: str, ano: str | None) -> dict:
    """Filtro obrigatório RA + ANO opcional (self-query style)."""
    if ano:
        return {"$and": [{"RA": aluno_id}, {"ANO": str(ano)}]}
    return {"RA": aluno_id}


def _extract_ano_from_query(llm: ChatOpenAI, pergunta: str, config: dict) -> str | None:
    """Extrai ano mencionado na pergunta (ex.: 'em 2024', 'ano letivo 2023') para filtro opcional."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Extraia o ano letivo mencionado na pergunta. Retorne apenas o ano (ex: 2024) ou a palavra VAZIO se não houver menção a ano específico."),
        ("human", "{pergunta}"),
    ])
    chain = prompt | llm
    out = chain.invoke({"pergunta": pergunta}, config=config)
    text = (out.content if hasattr(out, "content") else str(out)).strip().upper()
    if not text or text == "VAZIO" or len(text) != 4 or not text.isdigit():
        return None
    return text


def _expand_query(llm: ChatOpenAI, pergunta: str, n: int, config: dict) -> list[str]:
    """Gera n-1 reformulações/sinônimos da pergunta via LLM; retorna [pergunta_original, ...variantes]."""
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "Gere exatamente {n} reformulações ou sinônimos da pergunta do usuário, mantendo o mesmo sentido. "
            "Uma por linha, sem numeração. Não repita a pergunta original literalmente nas variantes.",
        ),
        ("human", "{pergunta}"),
    ])
    chain = prompt | llm
    out = chain.invoke({"pergunta": pergunta, "n": n}, config=config)
    text = (out.content if hasattr(out, "content") else str(out)).strip()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()][:n]
    return [pergunta] + lines[: n - 1]


def _merge_and_dedupe_docs(docs_list: list[list[Document]], max_docs: int) -> list[Document]:
    """Junta listas de documentos, deduplica por page_content (ordem de primeira aparição), limita a max_docs."""
    seen: set[str] = set()
    out: list[Document] = []
    for docs in docs_list:
        for d in docs:
            key = (d.page_content or "").strip()
            if key and key not in seen:
                seen.add(key)
                out.append(d)
                if len(out) >= max_docs:
                    return out
    return out


def _resolve_hyde_content(doc: Document) -> str:
    """Se doc for HyDE (tem parent_content), retorna o chunk pai; senão retorna page_content."""
    if not USE_HYDE:
        return doc.page_content or ""
    parent = doc.metadata.get(HYDE_METADATA_KEY) if doc.metadata else None
    if isinstance(parent, str) and parent.strip():
        return parent.strip()
    if doc.metadata and doc.metadata.get(DOC_TYPE_KEY) == DOC_TYPE_HYDE:
        parent = doc.metadata.get(HYDE_METADATA_KEY)
        if isinstance(parent, str) and parent.strip():
            return parent.strip()
    return doc.page_content or ""


class RAG:
    """Motor RAG: Self-Query (metadata), híbrido (BM25 + vetorial), reranking; filtro RA obrigatório; Langfuse no invoke."""

    def __init__(self) -> None:
        self._embedding = OpenAIEmbeddings()
        self._vectorstore = Chroma(
            persist_directory=PERSIST_DIR,
            embedding_function=self._embedding,
            collection_name=COLLECTION_NAME,
        )
        self._llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self._prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                (
                    "human",
                    "Contexto do histórico do aluno:\n\n{contexto}\n\nPergunta do professor: {pergunta}",
                ),
            ]
        )
        self._chain = self._prompt | self._llm
        self._langfuse_handler = CallbackHandler()
        self._use_advanced = _HAS_ADVANCED_RAG

    def _get_docs_for_aluno(self, aluno_id: str, filtro: dict) -> list[Document]:
        """Documentos do aluno para construir BM25 e validar existência."""
        # Chroma .get(where=...) espera formato nativo; filtro simples RA ou $and
        try:
            result = self._vectorstore.get(where=filtro)
        except Exception:
            return []
        ids = result.get("ids") or []
        metadatas = result.get("metadatas") or []
        documents = result.get("documents") or []
        out: list[Document] = []
        for i, doc_text in enumerate(documents):
            meta = (metadatas[i] or {}) if i < len(metadatas) else {}
            out.append(Document(page_content=doc_text or "", metadata=meta))
        return out

    def _build_retriever(self, aluno_id: str, filtro: dict, config: dict) -> BaseRetriever:
        """Retriever base: vetorial com filtro. Se avançado, Ensemble (vetorial + BM25) + reranker. Opcional: LLMChainExtractor."""
        vector_retriever = self._vectorstore.as_retriever(
            search_kwargs={"filter": filtro, "k": RETRIEVAL_K}
        )
        base: BaseRetriever = vector_retriever
        if self._use_advanced:
            docs_aluno = self._get_docs_for_aluno(aluno_id, filtro)
            if docs_aluno:
                bm25 = BM25Retriever.from_documents(docs_aluno, k=RETRIEVAL_K)
                ensemble = EnsembleRetriever(
                    retrievers=[vector_retriever, bm25],
                    weights=ENSEMBLE_WEIGHTS,
                )
                try:
                    model = HuggingFaceCrossEncoder(model_name=CROSS_ENCODER_MODEL)
                    compressor = CrossEncoderReranker(model=model, top_n=RERANK_TOP_N)
                    base = ContextualCompressionRetriever(
                        base_compressor=compressor,
                        base_retriever=ensemble,
                    )
                except Exception:
                    base = ensemble
        if USE_CONTEXT_COMPRESSION and _HAS_LLM_EXTRACTOR:
            try:
                compressor = LLMChainExtractor.from_llm(self._llm)
                base = ContextualCompressionRetriever(
                    base_compressor=compressor,
                    base_retriever=base,
                )
            except Exception:
                pass
        return base

    def query(self, aluno_id: str, pergunta: str) -> tuple[str, list[str]]:
        """
        Self-Query (ANO opcional) + retrieval híbrido + reranking; monta contexto e invoca LLM com Langfuse.

        Parameters
        ----------
        aluno_id : str
            RA do aluno (filtro obrigatório no retrieval).
        pergunta : str
            Pergunta do professor.

        Returns
        -------
        tuple[str, list[str]]
            (resposta do LLM, lista de conteúdos dos documentos usados no contexto).

        Raises
        ------
        AlunoNaoEncontradoError
            Se não houver documentos para o RA no banco.
        """
        config = {"callbacks": [self._langfuse_handler]}

        # Self-Query: extrair ano da pergunta (opcional) e montar filtro com RA obrigatório
        ano = _extract_ano_from_query(self._llm, pergunta, config)
        filtro = _build_filter(aluno_id, ano)

        # Garantir que há documentos para o aluno
        docs_aluno = self._get_docs_for_aluno(aluno_id, {"RA": aluno_id})
        if not docs_aluno:
            raise AlunoNaoEncontradoError(f"Nenhum documento encontrado para RA {aluno_id}")

        retriever = self._build_retriever(aluno_id, filtro, config)
        if USE_QUERY_EXPANSION:
            variants = _expand_query(self._llm, pergunta, QUERY_EXPANSION_N, config)
            docs_list = [retriever.invoke(q, config=config) for q in variants]
            docs = _merge_and_dedupe_docs(docs_list, max_docs=RERANK_TOP_N * 2)
        else:
            docs = retriever.invoke(pergunta, config=config)
        if not docs:
            # Filtro com ANO pode não ter match; fallback para todos os docs do RA
            retriever_fallback = self._vectorstore.as_retriever(
                search_kwargs={"filter": {"RA": aluno_id}, "k": RETRIEVAL_K}
            )
            if self._use_advanced:
                try:
                    model = HuggingFaceCrossEncoder(model_name=CROSS_ENCODER_MODEL)
                    compressor = CrossEncoderReranker(model=model, top_n=RERANK_TOP_N)
                    retriever_fallback = ContextualCompressionRetriever(
                        base_compressor=compressor,
                        base_retriever=retriever_fallback,
                    )
                except Exception:
                    pass
            docs = retriever_fallback.invoke(pergunta, config=config)

        if not docs:
            raise AlunoNaoEncontradoError(f"Nenhum documento encontrado para RA {aluno_id}")

        documentos_usados = [_resolve_hyde_content(d) for d in docs]
        contexto = "\n\n---\n\n".join(documentos_usados)
        msg = self._chain.invoke(
            {"contexto": contexto, "pergunta": pergunta},
            config=config,
        )
        content = getattr(msg, "content", None)
        resposta = content if isinstance(content, str) else str(msg)
        return resposta, documentos_usados
