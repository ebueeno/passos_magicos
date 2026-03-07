"""
Testes de ingestão e Data Contract (skill_qa_tester.md).
Valida limpeza de nulos: numérico -> 0.0, qualitativo -> "Sem registro no período".
Testes de process_uploaded_file: mapeamento dinâmico, IPP ausente, decimais BR, idade corrompida, duplicatas.
"""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src.preprocessing import (
    COLUNAS_OFICIAIS,
    COLUNAS_NUMERICAS,
    COLUNAS_QUALITATIVAS,
    TEXTO_NULOS,
    clean_and_standardize_pede,
    process_uploaded_file,
)


def test_nulos_numericos_preenchidos_com_zero():
    """DataFrame com nulos em colunas numéricas deve sair com 0.0 (Data Contract)."""
    df = pd.DataFrame(
        {
            "RA": ["123"],
            "NOME_ANONIMIZADO": ["Aluno X"],
            "ANO_PESQUISA": ["2022"],
            "FASE": ["7"],
            "TURMA": ["A"],
            "IDADE": [pd.NA],
            "INSTITUICAO_ENSINO": ["EE"],
            "PEDRA": ["Quartzo"],
            "INDE": [pd.NA],
            "IDA": [pd.NA],
            "IAN": [pd.NA],
            "IEG": [pd.NA],
            "IAA": [pd.NA],
            "IPS": [pd.NA],
            "IPP": [pd.NA],
            "IPV": [pd.NA],
            "ATINGIU_PV": [pd.NA],
            "NOTA_MAT": [pd.NA],
            "NOTA_PORT": [pd.NA],
            "NOTA_ING": [pd.NA],
            "REC_PSICOLOGIA": ["Ok"],
            "REC_AVALIACAO": ["Promovido"],
            "DESTAQUE_IEG": ["Destaque: bom"],
            "DESTAQUE_IDA": ["Destaque: esforço"],
            "DESTAQUE_IPV": ["Melhorar: participação"],
        }
    )
    out = clean_and_standardize_pede(df)
    assert out.shape[0] == 1
    for col in COLUNAS_NUMERICAS:
        if col in out.columns:
            assert out[col].iloc[0] == 0.0, f"Coluna numérica {col} deveria ser 0.0"


def test_nulos_qualitativos_preenchidos_com_sem_registro():
    """DataFrame com nulos em colunas qualitativas deve sair com TEXTO_NULOS."""
    df = pd.DataFrame(
        {
            "RA": [pd.NA],
            "NOME_ANONIMIZADO": [pd.NA],
            "ANO_PESQUISA": [pd.NA],
            "FASE": [pd.NA],
            "TURMA": [pd.NA],
            "IDADE": [10],
            "INSTITUICAO_ENSINO": [pd.NA],
            "PEDRA": [pd.NA],
            "INDE": [5.5],
            "IDA": [6.0],
            "IAN": [0.0],
            "IEG": [7.0],
            "IAA": [6.5],
            "IPS": [5.0],
            "IPP": [6.0],
            "IPV": [0.0],
            "ATINGIU_PV": [0.0],
            "NOTA_MAT": [0.0],
            "NOTA_PORT": [0.0],
            "NOTA_ING": [0.0],
            "REC_PSICOLOGIA": [pd.NA],
            "REC_AVALIACAO": [pd.NA],
            "DESTAQUE_IEG": [pd.NA],
            "DESTAQUE_IDA": [pd.NA],
            "DESTAQUE_IPV": [pd.NA],
        }
    )
    out = clean_and_standardize_pede(df)
    assert out.shape[0] == 1
    for col in COLUNAS_QUALITATIVAS:
        if col in out.columns:
            assert out[col].iloc[0] == TEXTO_NULOS, (
                f"Coluna qualitativa {col} deveria ser '{TEXTO_NULOS}'"
            )


def test_dataframe_vazio_retorna_vazio():
    """DataFrame vazio deve retornar DataFrame vazio com COLUNAS_OFICIAIS."""
    df = pd.DataFrame()
    out = clean_and_standardize_pede(df)
    assert list(out.columns) == COLUNAS_OFICIAIS
    assert len(out) == 0


def test_colunas_oficiais_presentes():
    """Após limpeza, resultado tem exatamente COLUNAS_OFICIAIS e sem NaN em numéricos/qualitativos."""
    df = pd.DataFrame(
        {
            "RA": ["456"],
            "NOME_ANONIMIZADO": ["Aluno Y"],
            "ANO_PESQUISA": ["2023"],
            "FASE": ["ALFA"],
            "TURMA": ["B"],
            "IDADE": [12],
            "INSTITUICAO_ENSINO": ["EM"],
            "PEDRA": ["Ágata"],
            "INDE": [7.2],
            "IDA": [6.5],
            "IAN": [0.0],
            "IEG": [8.0],
            "IAA": [7.0],
            "IPS": [6.5],
            "IPP": [7.0],
            "IPV": [5.0],
            "ATINGIU_PV": [0.0],
            "NOTA_MAT": [8.0],
            "NOTA_PORT": [7.5],
            "NOTA_ING": [6.0],
            "REC_PSICOLOGIA": ["Sem limitações"],
            "REC_AVALIACAO": ["Mantido na Fase atual"],
            "DESTAQUE_IEG": ["Destaque: entrega"],
            "DESTAQUE_IDA": ["Melhorar: provas"],
            "DESTAQUE_IPV": ["Destaque: integração"],
        }
    )
    out = clean_and_standardize_pede(df)
    assert list(out.columns) == COLUNAS_OFICIAIS
    assert out.shape[0] == 1
    for col in COLUNAS_NUMERICAS:
        assert not out[col].isna().any(), f"Não deveria haver NaN em {col}"
    for col in COLUNAS_QUALITATIVAS:
        assert not out[col].isna().any(), f"Não deveria haver NaN em {col}"


# --- process_uploaded_file ---


def test_process_uploaded_file_mapeamento_dinamico():
    """process_uploaded_file renomeia variantes históricas para colunas padronizadas."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(
            "RA,Idade 22,INDE 22,Pedra 22,Escola,Rec Psicologia,Rec Av1,Matem,Portug,Inglês,Nome Anonimizado\n"
            "1,14,6,Quartzo,EE X,Ok,Promovido,7,8,6,Aluno A\n"
        )
        path = f.name
    try:
        out = process_uploaded_file(path)
        assert "IDADE" in out.columns
        assert "INDE" in out.columns
        assert "PEDRA" in out.columns
        assert "INSTITUICAO_ENSINO" in out.columns
        assert "REC_PSICOLOGIA" in out.columns
        assert "REC_AVALIACAO" in out.columns
        assert "NOTA_MAT" in out.columns
        assert "NOTA_PORT" in out.columns
        assert "NOTA_ING" in out.columns
        assert "NOME_ANONIMIZADO" in out.columns
        assert out["IDADE"].iloc[0] == 14
        assert out["INDE"].iloc[0] == 6.0
        assert out["INSTITUICAO_ENSINO"].iloc[0] == "EE X"
        assert out["NOME_ANONIMIZADO"].iloc[0] == "Aluno A"
    finally:
        Path(path).unlink(missing_ok=True)


def test_process_uploaded_file_ipp_ausente():
    """Planilha sem coluna IPP (ex.: 2022) ganha coluna IPP com 0.0."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("RA,Idade,INDE\n1,15,5.5\n")
        path = f.name
    try:
        out = process_uploaded_file(path)
        assert "IPP" in out.columns
        assert out["IPP"].iloc[0] == 0.0
    finally:
        Path(path).unlink(missing_ok=True)


def test_process_uploaded_file_decimais_br_e_idade_corrompida():
    """Valores com vírgula viram float; idade corrompida (1/7/1900) vira 0 int."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write('RA,Idade,INDE,IDA\n1,"1/7/1900",5,6\n2,14,7,2\n')
        path = f.name
    try:
        out = process_uploaded_file(path)
        assert out["IDADE"].dtype == int or (hasattr(out["IDADE"].dtype, "kind") and out["IDADE"].dtype.kind in "iu")
        assert out["IDADE"].iloc[0] == 0
        assert out["IDADE"].iloc[1] == 14
    finally:
        Path(path).unlink(missing_ok=True)


def test_process_uploaded_file_virgula_decimal():
    """Valores numéricos com vírgula (ex: 5,6) viram float."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write('RA,Idade,INDE\n1,12,"5,6"\n')
        path = f.name
    try:
        out = process_uploaded_file(path)
        assert out["INDE"].iloc[0] == 5.6
    finally:
        Path(path).unlink(missing_ok=True)


def test_process_uploaded_file_remove_duplicatas():
    """Coluna duplicada (ex: duas 'Destaque IPV') resulta em uma só."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write('RA,Idade,INDE,Destaque IPV,Destaque IPV\n1,12,5,a,b\n')
        path = f.name
    try:
        out = process_uploaded_file(path)
        assert list(out.columns).count("DESTAQUE_IPV") == 1
    finally:
        Path(path).unlink(missing_ok=True)
