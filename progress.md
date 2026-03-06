# REGISTRO DE PROGRESSO

## Status Atual
- **Fase Atual:** Concluído. RAG opcionais implementados como flags configuráveis (query expansion, context compression, HyDE).
- **Última Ação:** Implementação das três opcionais como flags env (RAG_QUERY_EXPANSION, RAG_CONTEXT_COMPRESSION, RAG_USE_HYDE); HyDE no treino e retrieval; testes 12/12 passando.

## Tarefas Concluídas
- [x] Configuração base do `.cursorrules` e sistema Manus.
- [x] Mapeamento das regras de negócio do PEDE.
- [x] Criar estrutura modular (`app/`, `src/`, `tests/`) e pasta `app/model/chroma_db`.
- [x] Configurar `requirements.txt` (FastAPI, Pandas, Langchain, ChromaDB, OpenAI, Langfuse, Pytest).
- [x] Criar `Dockerfile` focado em produção e `.env.example`.
- [x] Em `src/preprocessing.py`, criar validação para padronizar colunas 2022/2023/2024.
- [x] Tratar nulos (qualitativos = "Sem registro no período", notas/índices = 0.0) e remover colunas duplicadas.
- [x] Em `src/feature_engineering.py`, criar função que recebe a linha do DataFrame limpo e gera o Chunk Semântico (parágrafo narrativo).
- [x] Em `src/train.py`, gerar embeddings via OpenAI e persistir ChromaDB em `app/model/chroma_db` com metadados RA e ANO_PESQUISA.
- [x] Em `src/rag_engine.py`, criar chain de retrieval com filtro por RA e integrar CallbackHandler do Langfuse no invoke.
- [x] Em `app/main.py` e `app/routes.py`, expor o endpoint POST /predict (aluno_id, pergunta); 404 quando aluno não existe no banco.
- [x] Em `tests/`, criar testes unitários para a ingestão de dados e para a API mockando o LLM.
- [x] Estender RAG e POST /predict com `documentos_usados` (rastreabilidade MLOps); criar `API_REFERENCE.md` (item 4 do edital do Datathon).
- [x] Suporte a CSV e XLSX: `src/load_data.py` (load_pede_data), `run_pipeline.py` (CLI), openpyxl no requirements; testes em test_load_data.py.
- [x] RAG avançado: Self-Query (extração de ANO da pergunta + filtro RA obrigatório), busca híbrida (EnsembleRetriever: BM25 + Chroma por aluno), reranking (CrossEncoderReranker + ContextualCompressionRetriever); dependências langchain-community, rank_bm25, sentence-transformers, lark; testes test_rag_engine.py (_build_filter, AlunoNaoEncontradoError).
- [x] RAG opcionais configuráveis: query expansion (_expand_query, _merge_and_dedupe_docs via RAG_QUERY_EXPANSION), context compression (LLMChainExtractor wrap via RAG_CONTEXT_COMPRESSION), HyDE (treino: _generate_hyde_questions_for_chunk + parent_content; retrieval: _resolve_hyde_content via RAG_USE_HYDE); flag --hyde no run_pipeline.py; testes test_rag_engine.py (helpers + hyde), test_train.py (hyde docs), todos 12/12 passando.

## Vitória
**Projeto concluído com sucesso.** Todas as fases do task_plan foram implementadas; a API POST /predict está operacional com RAG, ChromaDB e Langfuse; os testes de preprocessing (limpeza de nulos e contrato) e de API (TestClient + mock do RAG, HTTP 200 e estrutura da resposta) estão aprovados. O sistema está pronto para avaliação da banca.

## Arquivos Criados/Editados
- `requirements.txt` — dependências do projeto (incl. langchain-core, langchain-chroma, pytest-cov).
- `Dockerfile` — imagem de produção (Python 3.11-slim, uvicorn).
- `.env.example` — template de variáveis de ambiente (OpenAI, Langfuse).
- `.gitignore` — exclusão de .env, __pycache__, chroma_db/*, venv, etc.
- Estrutura: `app/`, `app/model/`, `app/model/chroma_db/` (com `.gitkeep`), `src/`, `tests/`.
- `src/preprocessing.py` — clean_and_standardize_pede (contrato PEDE, decimais BR, FASE string, duplicadas, nulos).
- `src/feature_engineering.py` — build_semantic_chunk (template narrativo PEDE para embeddings/RAG).
- `src/train.py` — build_and_persist_chroma (Document com RA/ANO, OpenAIEmbeddings, Chroma em app/model/chroma_db).
- `src/rag_engine.py` — classe RAG (retriever filter RA, system prompt Psicopedagogo, gpt-4o-mini, Langfuse no invoke); `query()` retorna `(resposta, documentos_usados)`.
- `app/__init__.py`, `app/main.py`, `app/routes.py` — API FastAPI e POST /predict (PredictRequest, PredictResponse com resposta + documentos_usados, 404 para aluno não encontrado).
- `tests/test_preprocessing.py` — testes de nulos (0.0 e "Sem registro no período") e colunas oficiais.
- `tests/test_api.py` — TestClient, mock de get_rag, HTTP 200, estrutura da resposta (resposta e documentos_usados), 404 e 422.
- `API_REFERENCE.md` — documentação oficial da API (item 4 do edital: visão geral, URL/autenticação, POST /predict, schemas, exemplos cURL/Python/Postman, códigos HTTP).
- `requirements.txt` — adicionado openpyxl para leitura de Excel.
- `src/load_data.py` — load_pede_data(path_or_paths): carrega .csv (decimal=,) ou .xlsx/.xls (todas as abas), retorna DataFrame bruto.
- `run_pipeline.py` — CLI: load_pede_data → clean_and_standardize_pede → build_and_persist_chroma (uso: python run_pipeline.py arquivo.xlsx ou arquivos.csv).
- `tests/test_load_data.py` — testes para CSV, XLSX (concat abas), extensão inválida e arquivo inexistente.
- `progress.md` — registro desta fase e declaração de conclusão.
- `requirements.txt` — langchain-community, rank_bm25, sentence-transformers, lark para RAG avançado.
- `src/rag_engine.py` — RAG avançado: _build_filter (RA + ANO opcional), _extract_ano_from_query (LLM), _get_docs_for_aluno (Chroma.get), _build_retriever (vetorial ou Ensemble + CrossEncoderReranker), query() com fallback quando filtro ANO não retorna docs.
- `tests/test_rag_engine.py` — testes unitários para _build_filter e AlunoNaoEncontradoError com Chroma mockado.
- `.env.example` — adicionadas flags RAG_QUERY_EXPANSION, RAG_CONTEXT_COMPRESSION, RAG_USE_HYDE, RAG_QUERY_EXPANSION_N, RAG_HYDE_QUESTIONS_PER_CHUNK.
- `src/rag_engine.py` — opcionais: _env_bool/_env_int (leitura de flags), _expand_query (variantes via LLM), _merge_and_dedupe_docs (merge deduplicado), _resolve_hyde_content (mapeamento HyDE→chunk pai), _build_retriever com wrap LLMChainExtractor opcional, query() com branch de query expansion e fallback hyde.
- `src/train.py` — HyDE: _generate_hyde_questions_for_chunk (LLM por chunk), build_and_persist_chroma(use_hyde, hyde_questions_per_chunk) com iteração sobre cópia de docs para evitar loop infinito.
- `run_pipeline.py` — flag --hyde para ativar geração HyDE no treino.
- `tests/test_rag_engine.py` — testes de _merge_and_dedupe_docs, _resolve_hyde_content e mapeamento HyDE na query().
- `tests/test_train.py` — novo arquivo; testa geração de docs HyDE com RA/ANO/parent_content via mock de _generate_hyde_questions_for_chunk.