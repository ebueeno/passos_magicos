"""
Feature engineering para RAG: transforma linha padronizada PEDE em chunk semântico.
Template humanizado para embeddings e retrieval (skill_rag_nlp.md).
"""

import pandas as pd


def _str_val(row: pd.Series, col: str, default: str = "") -> str:
    """Extrai valor da row como string; numérico formatado sem '.0' desnecessário."""
    val = row.get(col, default)
    if pd.isna(val):
        return default
    if isinstance(val, (int, float)):
        return str(int(val)) if isinstance(val, float) and val == int(val) else str(val)
    return str(val)


def build_semantic_chunk(row: pd.Series) -> str:
    """
    Gera o chunk semântico (parágrafo narrativo) a partir de uma linha do DataFrame
    padronizado por clean_and_standardize_pede (src/preprocessing.py).

    O texto segue o template da skill_rag_nlp.md para que o LLM interprete
    emoções e notas do aluno como narrativa orgânica. Usado nos embeddings (Fase 4)
    e no RAG (Fase 5).

    Parameters
    ----------
    row : pd.Series
        Uma linha do DataFrame com colunas oficiais PEDE (RA, ANO_PESQUISA, FASE, etc.).

    Returns
    -------
    str
        Três parágrafos em português: ano/classificação, avaliação psicológica,
        avaliação acadêmica e engajamento.
    """
    # Extração segura (fallback para coluna ausente ou NaN)
    def g(col: str, default: str = "") -> str:
        return _str_val(row, col, default)

    p1 = (
        f"No ano letivo de {g('ANO_PESQUISA')}, o aluno {g('RA')} "
        f"(Idade: {g('IDADE')}, Fase: {g('FASE')}, Instituição: {g('INSTITUICAO_ENSINO')}) "
        f"foi classificado com a Pedra {g('PEDRA')} possuindo INDE geral de {g('INDE')}. "
        f"Atingiu o Ponto de Virada: {g('ATINGIU_PV')}."
    )
    p2 = (
        f"Avaliação Psicológica (IPS: {g('IPS')}): O parecer da equipe foi '{g('REC_PSICOLOGIA')}'. "
        f"O aluno se autoavaliou com nota {g('IAA')} de bem-estar."
    )
    p3 = (
        f"Avaliação Acadêmica e Engajamento (IDA: {g('IDA')}, IAN: {g('IAN')}, IEG: {g('IEG')}, IPP: {g('IPP')}): "
        f"A recomendação do conselho foi '{g('REC_AVALIACAO')}'. "
        f"O destaque acadêmico foi '{g('DESTAQUE_IDA')}', e de engajamento '{g('DESTAQUE_IEG')}'. "
        f"Sobre sua integração e valores: '{g('DESTAQUE_IPV')}'."
    )
    return "\n".join([p1, p2, p3])
