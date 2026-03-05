"""
Testes do carregamento de dados PEDE (CSV e Excel) em src/load_data.py.
"""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src.load_data import load_pede_data


def test_load_pede_data_csv_retorna_dataframe_com_colunas():
    """load_pede_data com .csv retorna DataFrame não vazio com colunas esperadas."""
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        path = f.name
    try:
        df_write = pd.DataFrame({
            "RA": ["1", "2"],
            "ANO_PESQUISA": ["2023", "2023"],
            "FASE": ["7", "7"],
            "INDE": [7.5, 8.0],
        })
        df_write.to_csv(path, index=False, decimal=",")
        result = load_pede_data(path)
        assert isinstance(result, pd.DataFrame)
        assert len(result) >= 2
        assert "RA" in result.columns
        assert "ANO_PESQUISA" in result.columns
    finally:
        Path(path).unlink(missing_ok=True)


def test_load_pede_data_xlsx_concatena_abas():
    """load_pede_data com .xlsx concatena todas as abas em um único DataFrame."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = f.name
    try:
        df1 = pd.DataFrame({"RA": ["1"], "ANO_PESQUISA": ["2022"]})
        df2 = pd.DataFrame({"RA": ["2"], "ANO_PESQUISA": ["2023"]})
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            df1.to_excel(writer, sheet_name="2022", index=False)
            df2.to_excel(writer, sheet_name="2023", index=False)
        result = load_pede_data(path)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert "RA" in result.columns
    finally:
        Path(path).unlink(missing_ok=True)


def test_load_pede_data_extensao_invalida_levanta_value_error():
    """load_pede_data com extensão não suportada (.txt) levanta ValueError."""
    with pytest.raises(ValueError, match="Extensão não suportada"):
        load_pede_data("arquivo.txt")


def test_load_pede_data_arquivo_inexistente_levanta_file_not_found():
    """load_pede_data com arquivo que não existe levanta FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="não encontrado"):
        load_pede_data("nao_existe_12345.csv")


def test_load_pede_data_lista_de_paths_concatena():
    """load_pede_data com lista de paths concatena os DataFrames."""
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f1:
        path1 = f1.name
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f2:
        path2 = f2.name
    try:
        pd.DataFrame({"RA": ["1"], "A": [1]}).to_csv(path1, index=False)
        pd.DataFrame({"RA": ["2"], "A": [2]}).to_csv(path2, index=False)
        result = load_pede_data([path1, path2])
        assert len(result) == 2
    finally:
        Path(path1).unlink(missing_ok=True)
        Path(path2).unlink(missing_ok=True)
