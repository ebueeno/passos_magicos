"""
Script para rodar o pipeline PEDE: carrega CSV ou Excel, limpa e persiste ChromaDB.
Uso: python run_pipeline.py <arquivo.csv ou arquivo.xlsx> [outros_arquivos...]
"""

import argparse
import sys
import traceback

from src.load_data import load_pede_data
from src.preprocessing import clean_and_standardize_pede
from src.train import build_and_persist_chroma


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Carrega dados PEDE (CSV ou Excel), padroniza e persiste o ChromaDB."
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="Um ou mais arquivos .csv, .xlsx ou .xls (Excel: todas as abas são usadas).",
    )
    parser.add_argument(
        "--hyde",
        action="store_true",
        help="Gera perguntas hipotéticas por chunk (HyDE) e indexa no Chroma (requer RAG_USE_HYDE no app).",
    )
    args = parser.parse_args()

    try:
        df_raw = load_pede_data(args.paths)
        df_clean = clean_and_standardize_pede(df_raw)
        build_and_persist_chroma(df_clean, use_hyde=args.hyde)
        print("ChromaDB persistido em app/model/chroma_db" + (" (com HyDE)" if args.hyde else ""))
        return 0
    except Exception:
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
