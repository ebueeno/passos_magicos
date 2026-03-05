"""
Treinamento e serialização do RAG: DataFrame processado -> chunks -> Document -> ChromaDB.
Persiste em app/model/chroma_db com metadados RA e ANO para filtro (skill_mlops_backend.md).
"""

from pathlib import Path

import pandas as pd
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from src.feature_engineering import build_semantic_chunk

# Diretório de persistência obrigatório (Datathon / skill)
PERSIST_DIR = "./app/model/chroma_db"
COLLECTION_NAME = "pede"


def _ensure_persist_dir() -> None:
    """Garante que o diretório de persistência existe."""
    Path(PERSIST_DIR).mkdir(parents=True, exist_ok=True)


def build_and_persist_chroma(df: pd.DataFrame) -> Chroma:
    """
    Gera chunks a partir do DataFrame processado, cria Documents com metadados RA e ANO,
    vetoriza com OpenAI e persiste o ChromaDB em app/model/chroma_db.

    O DataFrame deve ser o retorno de clean_and_standardize_pede (src/preprocessing.py).
    Metadados em cada documento: {"RA": row['RA'], "ANO": row['ANO_PESQUISA']}.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame já padronizado (colunas oficiais PEDE, nulos tratados).

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

    documents: list[Document] = []
    for _, row in df.iterrows():
        text = build_semantic_chunk(row)
        metadata = {
            "RA": str(row.get("RA", "")),
            "ANO": str(row.get("ANO_PESQUISA", "")),
        }
        documents.append(Document(page_content=text, metadata=metadata))

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
