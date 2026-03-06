"""
Treinamento e serialização do RAG: DataFrame processado -> chunks -> Document -> ChromaDB.
Persiste em app/model/chroma_db com metadados RA e ANO para filtro (skill_mlops_backend.md).
Opcional: HyDE — gera perguntas hipotéticas por chunk e indexa com parent_content.
"""

import os
from pathlib import Path

import pandas as pd
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from src.feature_engineering import build_semantic_chunk

# Diretório de persistência obrigatório (Datathon / skill)
PERSIST_DIR = "./app/model/chroma_db"
COLLECTION_NAME = "pede"

# Metadados HyDE (alinhado com src/rag_engine.py)
DOC_TYPE_KEY = "doc_type"
DOC_TYPE_HYDE = "hyde"
HYDE_PARENT_CONTENT_KEY = "parent_content"


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except ValueError:
        return default


HYDE_QUESTIONS_PER_CHUNK = max(1, min(5, _env_int("RAG_HYDE_QUESTIONS_PER_CHUNK", 2)))


def _ensure_persist_dir() -> None:
    """Garante que o diretório de persistência existe."""
    Path(PERSIST_DIR).mkdir(parents=True, exist_ok=True)


def _generate_hyde_questions_for_chunk(
    llm: ChatOpenAI,
    chunk_text: str,
    n: int,
) -> list[str]:
    """Gera n perguntas hipotéticas que o chunk poderia responder (uma por linha)."""
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "Com base no seguinte trecho sobre um aluno, gere exatamente {n} perguntas "
            "que um professor poderia fazer e que este trecho responderia. Uma pergunta por linha, sem numeração.",
        ),
        ("human", "{chunk}"),
    ])
    chain = prompt | llm
    out = chain.invoke({"chunk": chunk_text[:8000], "n": n})
    text = (out.content if hasattr(out, "content") else str(out)).strip()
    return [ln.strip() for ln in text.splitlines() if ln.strip()][:n]


def build_and_persist_chroma(
    df: pd.DataFrame,
    use_hyde: bool = False,
    hyde_questions_per_chunk: int | None = None,
) -> Chroma:
    """
    Gera chunks a partir do DataFrame processado, cria Documents com metadados RA e ANO,
    vetoriza com OpenAI e persiste o ChromaDB em app/model/chroma_db.
    Se use_hyde=True, gera perguntas hipotéticas por chunk e adiciona documentos HyDE (doc_type, parent_content).

    O DataFrame deve ser o retorno de clean_and_standardize_pede (src/preprocessing.py).
    Metadados em cada documento: {"RA": row['RA'], "ANO": row['ANO_PESQUISA']}.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame já padronizado (colunas oficiais PEDE, nulos tratados).
    use_hyde : bool
        Se True, gera perguntas hipotéticas por chunk e indexa no Chroma com parent_content.
    hyde_questions_per_chunk : int, optional
        Número de perguntas por chunk quando use_hyde=True. Default: RAG_HYDE_QUESTIONS_PER_CHUNK ou 2.

    Returns
    -------
    Chroma
        Instância do vectorstore persistido (para uso no RAG).

    Raises
    ------
    ValueError
        Se o DataFrame estiver vazio.
    """
    if df is None or df.empty:
        raise ValueError("DataFrame processado não pode ser vazio para construir o ChromaDB.")

    n_hyde = hyde_questions_per_chunk if hyde_questions_per_chunk is not None else HYDE_QUESTIONS_PER_CHUNK
    documents: list[Document] = []
    for _, row in df.iterrows():
        text = build_semantic_chunk(row)
        metadata = {
            "RA": str(row.get("RA", "")),
            "ANO": str(row.get("ANO_PESQUISA", "")),
        }
        documents.append(Document(page_content=text, metadata=metadata))

    if use_hyde and documents:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        original_docs = list(documents)
        for doc in original_docs:
            questions = _generate_hyde_questions_for_chunk(llm, doc.page_content or "", n_hyde)
            for q in questions:
                if not q:
                    continue
                hyde_meta = {
                    **doc.metadata,
                    DOC_TYPE_KEY: DOC_TYPE_HYDE,
                    HYDE_PARENT_CONTENT_KEY: doc.page_content or "",
                }
                documents.append(Document(page_content=q, metadata=hyde_meta))

    if not documents:
        raise ValueError("Nenhum documento gerado a partir do DataFrame.")

    _ensure_persist_dir()
    embedding = OpenAIEmbeddings()
    # persist_directory conforme skill_mlops_backend.md (Datathon)
    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embedding,
        persist_directory=PERSIST_DIR,
        collection_name=COLLECTION_NAME,
    )
    return vectorstore
