"""
Testes de ingestão e Data Contract (skill_qa_tester.md).
Valida limpeza de nulos: numérico -> 0.0, qualitativo -> "Sem registro no período".
"""

import pandas as pd
import pytest

from src.preprocessing import (
    COLUNAS_OFICIAIS,
    COLUNAS_NUMERICAS,
    COLUNAS_QUALITATIVAS,
    TEXTO_NULOS,
    clean_and_standardize_pede,
)


def test_nulos_numericos_preenchidos_com_zero():
    """DataFrame com nulos em colunas numéricas deve sair com 0.0 (Data Contract)."""
    df = pd.DataFrame(
        {
            "RA": ["123"],
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
