"""
API Copiloto PEDE — Passos Mágicos.
Endpoint: POST /predict (RAG com filtro por RA e Langfuse).
"""

from fastapi import FastAPI

from app import routes

app = FastAPI(
    title="API Copiloto PEDE",
    description="Copiloto pedagógico e psicológico para professores da Passos Mágicos (RAG).",
    version="0.1.0",
)

app.include_router(routes.router, prefix="", tags=["predict"])
