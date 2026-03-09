# Copiloto PEDE — Passos Mágicos (Datathon FIAP)

## 1) Visão Geral do Projeto

Este projeto implementa um **Copiloto Pedagógico e Psicológico** para a Associação Passos Mágicos. Utilizamos **RAG (Retrieval-Augmented Generation)** com Langchain, ChromaDB e um LLM (OpenAI) para **prever e estimar o risco de defasagem escolar** dos alunos com base no histórico do programa PEDE (indicadores INDE, IDA, **IAN**, IEG, IPS, entre outros). O indicador **IAN** (Adequação de Nível) é usado estritamente para classificar o risco em BAIXO (IAN=10), MODERADO (IAN=5) ou ALTO (IAN≤2,5). A primeira frase da resposta do modelo é sempre a estimativa do risco de defasagem; em seguida, a justificativa com dados qualitativos (Destaques, IPS, IEG) e um plano de ação sugerido. O sistema apoia professores e tutores na mitigação de evasão e vulnerabilidade.

---

## 2) Estrutura do Projeto (Diretórios e Arquivos)

- **`app/`** — API FastAPI: `main.py`, `routes.py` (POST /predict, POST /upload).
- **`app/model/`** — Modelos e artefatos: ChromaDB (vetores), `contrato_dados.joblib` (contrato serializado).
- **`src/`** — Lógica de negócio: `preprocessing.py` (Data Contract e joblib), `load_data.py`, `feature_engineering.py`, `train.py` (embeddings e ingestão no ChromaDB), `rag_engine.py` (chain RAG e System Prompt).
- **`tests/`** — Testes Pytest: `test_preprocessing.py`, `test_api.py`, `test_rag_engine.py`, `test_train.py`, `test_load_data.py`.
- **`data/`** — Planilhas enviadas via POST /upload (bind mount no Docker).
- **Raiz:** `requirements.txt`, `Dockerfile`, `docker-compose.yml`, `run_pipeline.py` (CLI de ingestão), `API_REFERENCE.md`, `progress.md`, `findings.md`.

---

## 3) Instruções de Deploy (como subir o ambiente)

### Local (desenvolvimento)

1. Configure as variáveis de ambiente (copie `.env.example` para `.env` e preencha `OPENAI_API_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`).
2. Na raiz do projeto, execute:
   ```bash
   docker compose up -d
   ```
3. Aguarde os healthchecks (Langfuse pode levar ~1–2 min). Serviços e portas:
   - **API (Copiloto):** `http://localhost:8001` (porta 8001 no host; 8000 no container).
   - **Langfuse (observabilidade):** `http://localhost:3000`.

Para produção local: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`.

### GCP (Google Compute Engine)

Deploy automatizado via CLI — cria VM `e2-standard-2` (2 vCPU, 8 GB RAM, 50 GB SSD) e sobe toda a stack com Docker Compose:

```bash
export GCP_PROJECT_ID="seu-projeto"
export OPENAI_API_KEY="sk-..."
bash scripts/deploy_gcp.sh
```

Documentação completa, flags e troubleshooting: [`DEPLOY.md`](DEPLOY.md).

---

## 4) Exemplos de Chamadas à API

**POST /predict** (recomendação por aluno):

```bash
curl -X POST "http://localhost:8001/predict" \
  -H "Content-Type: application/json" \
  -d '{"aluno_id": "123", "pergunta": "Quais indicadores devo priorizar com este aluno?"}'
```

Resposta esperada (200): `{"resposta": "...", "documentos_usados": ["..."]}`. A primeira frase de `resposta` contém o **Risco de Defasagem Escolar** (BAIXO/MODERADO/ALTO) com base no IAN.

**POST /upload** (envio de planilha para ingestão):

```bash
curl -X POST "http://localhost:8001/upload" \
  -F "file=@planilha.csv"
```

Resposta esperada (200): `{"message": "Upload e ingestão concluídos.", "rows_ingested": N}`.

Documentação completa: `API_REFERENCE.md`.

---

## 5) Etapas do Pipeline de Machine Learning

1. **Ingestão e Data Contract** — Planilhas PEDE (CSV/XLSX) são carregadas por `load_pede_data`; `process_uploaded_file` e `clean_and_standardize_pede` aplicam o **Data Contract blindado**: mapeamento dinâmico de colunas (2022/2023/2024), tratamento de nulos (numérico → 0.0, qualitativo → "Sem registro no período"), decimais BR (vírgula), correção de idade corrompida (ex.: 1/7/1900 → 0). O contrato (colunas padronizadas) é **serializado com joblib** em `app/model/contrato_dados.joblib` (requisito edital).
2. **Chunking e Embeddings** — Cada linha limpa vira um chunk semântico em `feature_engineering.build_semantic_chunk`; embeddings são gerados via OpenAI.
3. **Injeção no VectorDB** — Os documentos são indexados no **ChromaDB** (persistido em `app/model/chroma_db` ou via serviço HTTP no Docker) com metadados RA, ANO, IDADE, FASE. A ingestão é feita por `train.ingest_dataframe_to_chroma` (usado no pipeline CLI e no POST /upload).
4. **RAG e Inferência** — Em cada POST /predict, o RAG (`rag_engine.RAG`) recupera o contexto do aluno por RA (e opcionalmente por ano), monta o prompt com a diretriz de Risco de Defasagem (IAN) e invoca o LLM; a resposta e os documentos usados são retornados. Langfuse registra traces (latência, tokens, groundedness).

Testes e cobertura (>80%): `pytest --cov=src --cov=app --cov-report=term-missing`.
