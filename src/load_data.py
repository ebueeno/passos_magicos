"""
Carregamento de dados PEDE a partir de arquivo(s) CSV ou Excel.
Suporta um único path ou lista de paths; Excel: todas as abas concatenadas.
"""

from pathlib import Path

import pandas as pd

SUPPORTED_CSV = (".csv",)
SUPPORTED_EXCEL = (".xlsx", ".xls")


def load_pede_data(path_or_paths: str | list[str]) -> pd.DataFrame:
    """
    Carrega dados PEDE a partir de arquivo(s) CSV ou Excel (.xlsx/.xls).

    - CSV: usa decimal=',' e encoding utf-8 (findings.md). Múltiplos arquivos são concatenados.
    - Excel: lê todas as abas de cada arquivo e concatena. Múltiplos arquivos são concatenados.

    Parameters
    ----------
    path_or_paths : str | list[str]
        Caminho único ou lista de caminhos (relativos ao CWD).

    Returns
    -------
    pd.DataFrame
        DataFrame bruto (sem limpeza). Use clean_and_standardize_pede em seguida.

    Raises
    ------
    ValueError
        Se a extensão não for .csv, .xlsx ou .xls (case-insensitive).
    FileNotFoundError
        Se algum arquivo não existir (propagado do pandas/pathlib).
    """
    paths = [path_or_paths] if isinstance(path_or_paths, str) else list(path_or_paths)
    if not paths:
        return pd.DataFrame()

    frames: list[pd.DataFrame] = []
    for path in paths:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {path}")
        ext = p.suffix.lower()
        if ext in SUPPORTED_CSV:
            df = pd.read_csv(path, decimal=",", encoding="utf-8")
            frames.append(df)
        elif ext in SUPPORTED_EXCEL:
            # Todas as abas
            sheets = pd.read_excel(path, sheet_name=None)
            for sheet_df in sheets.values():
                frames.append(sheet_df)
        else:
            raise ValueError(
                f"Extensão não suportada: {ext}. Use .csv, .xlsx ou .xls."
            )

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)
