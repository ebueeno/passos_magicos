# OBJETIVO GERAL: COPILOTO PEDAGÓGICO E PSICOLÓGICO (RAG)
Construir um sistema de ML capaz de ler o histórico qualitativo (pareceres) e quantitativo (notas e índices) de alunos da ONG Passos Mágicos (2020-2024) para sugerir planos de ação aos professores, mitigando o risco de evasão e vulnerabilidade. 

# ROADMAP DE EXECUÇÃO

## Fase 1: Setup MLOps e DevOps
- [ ] Criar estrutura modular (`app/`, `src/`, `tests/`) e pasta de persistência `app/model/chroma_db`.
- [ ] Configurar `requirements.txt` (FastAPI, Pandas, Langchain, ChromaDB, OpenAI, Langfuse, Pytest).
- [ ] Criar `Dockerfile` focado em produção e `.env.example`.

## Fase 2: Ingestão e Data Contract (Data Engineering)
- [ ] Em `src/preprocessing.py`, criar validação para padronizar as colunas das planilhas de 2022, 2023 e 2024.
- [ ] Tratar nulos: Dados qualitativos vazios = "Sem registro histórico". Notas/Índices vazios = `0.0`. Remover colunas duplicadas.

## Fase 3: RAG Feature Engineering (Chunking)
- [ ] Em `src/feature_engineering.py`, criar função que recebe a linha do DataFrame limpo e gera um "Chunk Semântico" (um parágrafo narrativo contando a história acadêmica e psicológica do aluno naquele ano).

## Fase 4: Treinamento e Serialização (Vector DB)
- [ ] Em `src/train.py`, gerar Embeddings via OpenAI e persistir o ChromaDB em `app/model/chroma_db`. É obrigatório injetar os metadados `RA` e `ANO_PESQUISA` em cada documento para filtro.

## Fase 5: O Motor de IA e Monitoramento (LLMOps)
- [ ] Em `src/rag_engine.py`, criar a Chain de Retrieval filtrando obrigatoriamente por `RA`.
- [ ] Integrar o `CallbackHandler` do Langfuse para registrar rastreabilidade e drift.

## Fase 6: Deploy e Qualidade (API e Testes)
- [ ] Em `app/main.py` e `app/routes.py`, expor o endpoint `POST /predict`.
- [ ] Em `tests/`, criar testes unitários para a ingestão de dados e para a API mockando o LLM.