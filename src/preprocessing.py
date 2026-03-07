"""
Ingestão e padronização dos dados PEDE (Passos Mágicos).
Data Contract: colunas oficiais 2022/2023/2024, nulos e decimais BR.
Leitura recomendada: pd.read_csv(..., decimal=',')
"""

import pandas as pd

from src.load_data import load_pede_data

# --- Contrato de dados (skill_data_engineer.md) ---
COLUNAS_OFICIAIS = [
    "RA",
    "NOME_ANONIMIZADO",
    "ANO_PESQUISA",
    "FASE",
    "TURMA",
    "IDADE",
    "INSTITUICAO_ENSINO",
    "PEDRA",
    "INDE",
    "IDA",
    "IAN",
    "IEG",
    "IAA",
    "IPS",
    "IPP",
    "IPV",
    "ATINGIU_PV",
    "NOTA_MAT",
    "NOTA_PORT",
    "NOTA_ING",
    "REC_PSICOLOGIA",
    "REC_AVALIACAO",
    "DESTAQUE_IEG",
    "DESTAQUE_IDA",
    "DESTAQUE_IPV",
]

COLUNAS_NUMERICAS = [
    "IDADE",
    "INDE",
    "IDA",
    "IAN",
    "IEG",
    "IAA",
    "IPS",
    "IPP",
    "IPV",
    "ATINGIU_PV",
    "NOTA_MAT",
    "NOTA_PORT",
    "NOTA_ING",
]

COLUNAS_QUALITATIVAS = [
    "RA",
    "NOME_ANONIMIZADO",
    "ANO_PESQUISA",
    "FASE",
    "TURMA",
    "INSTITUICAO_ENSINO",
    "PEDRA",
    "REC_PSICOLOGIA",
    "REC_AVALIACAO",
    "DESTAQUE_IEG",
    "DESTAQUE_IDA",
    "DESTAQUE_IPV",
]

# Mapeamento dinâmico: nome padrão -> primeira coluna encontrada entre candidatos
# (variações históricas 2022/2023/2024)
MAPEAMENTO_DINAMICO = {
    "NOME_ANONIMIZADO": ["Nome", "Nome Anonimizado"],
    "IDADE": ["Idade 22", "Idade"],
    "INSTITUICAO_ENSINO": ["Instituição de ensino", "Escola", "Instituição de Ensino", "Instituicao de Ensino", "Instituição Ensino"],
    "PEDRA": ["Pedra 20", "Pedra 21", "Pedra 22", "Pedra 23", "Pedra 2024", "Pedra"],
    "INDE": ["INDE 22", "INDE 2023", "INDE 2024"],
    "NOTA_MAT": ["Matem", "Mat"],
    "NOTA_PORT": ["Portug", "Por"],
    "NOTA_ING": ["Inglês", "Ing"],
    "REC_PSICOLOGIA": ["Rec Psicologia"],
    "REC_AVALIACAO": ["Rec Av1"],
}

# Variantes de nomes nas planilhas 2022, 2023, 2024 -> nome oficial
MAPEAMENTO_VARIANTES = {
    "Destaque IPV": "DESTAQUE_IPV",
    "Destaque IEG": "DESTAQUE_IEG",
    "Destaque IDA": "DESTAQUE_IDA",
    "REC PSICOLOGIA": "REC_PSICOLOGIA",
    "REC_PSICO": "REC_PSICOLOGIA",
    "REC AVALIACAO": "REC_AVALIACAO",
    "Ano Pesquisa": "ANO_PESQUISA",
    "Ano": "ANO_PESQUISA",
    "Instituição de Ensino": "INSTITUICAO_ENSINO",
    "Instituicao de Ensino": "INSTITUICAO_ENSINO",
    "Instituição Ensino": "INSTITUICAO_ENSINO",
    "Pedra": "PEDRA",
    "Atingiu PV": "ATINGIU_PV",
    "Atingiu Ponto de Virada": "ATINGIU_PV",
}

TEXTO_NULOS = "Sem registro no período"


def _coerce_decimal_br(series: pd.Series) -> pd.Series:
    """Converte coluna com decimal vírgula (BR) para numérico."""
    if series.dtype in ("float64", "Int64", "int64"):
        return series
    s = series.astype(str).str.replace(",", ".", regex=False)
    return pd.to_numeric(s, errors="coerce")


def clean_and_standardize_pede(df: pd.DataFrame) -> pd.DataFrame:
    """
    Padroniza e limpa o DataFrame PEDE para o contrato de dados oficial.

    Aplica: remoção de colunas duplicadas (primeira ocorrência), renomeação
    de variantes para colunas oficiais, conversão de decimais BR (vírgula),
    FASE como string, preenchimento de nulos (numérico -> 0.0, qualitativo ->
    "Sem registro no período"). Recomenda-se ler CSV com decimal=','.

    Returns
    -------
    pd.DataFrame
        DataFrame apenas com COLUNAS_OFICIAIS, nulos tratados.
    """
    if df.empty:
        return pd.DataFrame(columns=COLUNAS_OFICIAIS)

    # 1. Remover colunas duplicadas (keep first) — findings: 2023 Destaque IPV, 2024 Ativo/Inativo
    df = df.loc[:, ~df.columns.duplicated(keep="first")].copy()

    # 2. Renomear variantes para oficiais (apenas colunas que existem)
    rename = {k: v for k, v in MAPEAMENTO_VARIANTES.items() if k in df.columns}
    df = df.rename(columns=rename)

    # 3. Alinhar ao contrato: só colunas oficiais; criar faltantes com NaN
    for col in COLUNAS_OFICIAIS:
        if col not in df.columns:
            df[col] = pd.NA
    df = df[COLUNAS_OFICIAIS]

    # 4. Decimais BR: colunas numéricas em object -> substituir , por . e converter
    for col in COLUNAS_NUMERICAS:
        if col not in df.columns:
            continue
        if df[col].dtype == object or df[col].dtype.name == "string":
            df[col] = _coerce_decimal_br(df[col])
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 5. FASE como string (findings: mistura 7 e "ALFA") — preencher nulos antes para não virar "nan"
    if "FASE" in df.columns:
        df["FASE"] = df["FASE"].fillna(TEXTO_NULOS).astype(str)

    # 6. Nulos numéricos -> 0.0 (Nota Zero no IDA permanece 0.0; interpretação é no LLM)
    for col in COLUNAS_NUMERICAS:
        if col in df.columns:
            df[col] = df[col].fillna(0.0)

    # 7. Nulos qualitativos -> "Sem registro no período"
    for col in COLUNAS_QUALITATIVAS:
        if col in df.columns:
            df[col] = df[col].fillna(TEXTO_NULOS).astype(str)

    return df


def _build_dynamic_rename(df: pd.DataFrame) -> dict:
    """Constrói dicionário de renomeação: primeira coluna encontrada por nome padrão."""
    rename = {}
    for std_name, candidates in MAPEAMENTO_DINAMICO.items():
        for cand in candidates:
            if cand in df.columns:
                rename[cand] = std_name
                break
    return rename


def process_uploaded_file(file_path: str) -> pd.DataFrame:
    """
    Carrega planilha (.csv ou .xlsx) e aplica o Data Contract completo.

    Ordem: remoção de colunas duplicadas, mapeamento dinâmico de variantes
    históricas, garantia de IPP (0.0 se ausente, ex.: 2022), decimais BR,
    correção de idade corrompida (datas 1/7/1900 -> 0), então clean_and_standardize_pede.

    Parameters
    ----------
    file_path : str
        Caminho para arquivo .csv ou .xlsx/.xls.

    Returns
    -------
    pd.DataFrame
        DataFrame com COLUNAS_OFICIAIS, nulos tratados, IDADE como int.
    """
    df = load_pede_data(file_path)
    if df.empty:
        return pd.DataFrame(columns=COLUNAS_OFICIAIS)

    # 1. Remover colunas duplicadas (findings: Destaque IPV, Ativo/Inativo)
    df = df.loc[:, ~df.columns.duplicated(keep="first")].copy()

    # 2. Mapeamento dinâmico (variações por ano)
    rename = _build_dynamic_rename(df)
    df = df.rename(columns=rename)
    # Variantes fixas (Destaque IPV, Ano Pesquisa, etc.)
    rename_var = {k: v for k, v in MAPEAMENTO_VARIANTES.items() if k in df.columns}
    df = df.rename(columns=rename_var)

    # 3. IPP ausente (base 2022)
    if "IPP" not in df.columns:
        df["IPP"] = 0.0

    # 4. Decimais BR: indicadores numéricos
    for col in COLUNAS_NUMERICAS:
        if col not in df.columns:
            continue
        if df[col].dtype == object or df[col].dtype.name == "string":
            df[col] = _coerce_decimal_br(df[col])
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    # 5. Idade corrompida (findings: 1/7/1900 em 2023) -> coerce, fill 0, int
    if "IDADE" in df.columns:
        df["IDADE"] = pd.to_numeric(df["IDADE"], errors="coerce").fillna(0).astype(int)

    # 6. Contrato e nulos
    df = clean_and_standardize_pede(df)

    # 7. Garantir IDADE como int na saída (clean preenche como float)
    if "IDADE" in df.columns:
        df["IDADE"] = pd.to_numeric(df["IDADE"], errors="coerce").fillna(0).astype(int)

    return df
