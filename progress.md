# REGISTRO DE PROGRESSO

## Status Atual
- **Fase Atual:** Concluído. Infraestrutura de produção LLMOps do Datathon finalizada (Step 4).
- **Última Ação:** Refatoração do System Prompt (Step 2): motor RAG em src/rag_engine.py atualizado para respostas dinâmicas — novo prompt (Psicopedagogo Sênior, REGRAS DE OURO por intenção, risco de defasagem orgânico no primeiro parágrafo, sem formatos robóticos); temperatura 0.3; regras de negócio PEDE mantidas. progress.md atualizado.

## Tarefas Concluídas
- [x] Refatoração System Prompt (Step 2): src/rag_engine.py — System Prompt substituído por texto que prioriza intenção da pergunta (IAA/IPS emocional, IDA/IEG notas, ingressantes acolhimento), risco de defasagem (IAN) orgânico no primeiro parágrafo, proibição de formatos robóticos; ChatOpenAI temperature=0.3; regras de negócio PEDE preservadas. Motor RAG refatorado para respostas dinâmicas.
- [x] Memória Viva — Prompting Dinâmico: diagnóstico de respostas do LLM robotizadas/padronizadas por templates fixos no System Prompt; regra "Prompting Dinâmico e Flexível" registrada em findings.md §4 (Arquitetura LLMOps): Risco de Defasagem como contexto inicial orgânico; corpo da resposta DEVE se adaptar à intenção da pergunta (psicológica, acadêmica, acolhimento).
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
- [x] findings.md: seção "Anomalias nos Dados (Pandas)" atualizada com colunas dinâmicas (mapeamento obrigatório), ausência IPP 2022 (df.get), vírgula/datas (coerce + fill 0), duplicatas (df.columns.duplicated()), FASE string.
- [x] Definição do pipeline de Ingestão em Lote e da arquitetura LLMOps de produção: orquestração Docker (api, chromadb, langfuse-server, langfuse-db em rag_network), fluxo POST /upload → /app/data → Data Contract → upsert ChromaDB via HTTP; registrado em findings.md §4.
- [x] Step 2 Orquestração Docker e LLMOps: python-multipart e openpyxl no requirements.txt; docker-compose.yml (rede rag_network, langfuse-db com healthcheck pg_isready, langfuse-server com DATABASE_URL e depends healthy, chromadb com IS_PERSISTENT e healthcheck heartbeat, api com CHROMA_HOST/LANGFUSE_HOST e volume ./data:/app/data); docker-compose.prod.yml (api --workers 4 sem --reload, restart: always em todos); diretório data/ e .env.example completo (CHROMA_HOST, LANGFUSE_HOST).
- [x] Step 3 Refatoração Data Contract: função `process_uploaded_file(file_path)` em `src/preprocessing.py` — carrega planilha (.csv/.xlsx), remove colunas duplicadas, mapeamento dinâmico (NOME_ANONIMIZADO, IDADE, INSTITUICAO_ENSINO, PEDRA, INDE, NOTA_MAT/PORT/ING, REC_PSICOLOGIA/AVALIACAO), blindagem IPP (0.0 se ausente, ex.: 2022), decimais BR e correção de idade corrompida (1/7/1900 → 0 int); contrato estendido com NOTA_MAT, NOTA_PORT, NOTA_ING e NOME_ANONIMIZADO; testes em test_preprocessing.py (mapeamento, IPP ausente, decimais/vírgula, idade corrompida, duplicatas).
- [x] Step 4 (Final) RAG Server-Side e API de Upload: `src/train.py` — cliente Chroma HTTP (`chromadb.HttpClient(host=CHROMA_HOST, port=8000)`), função `ingest_dataframe_to_chroma(df)` com metadata em tipos nativos (RA, ANO, IDADE, FASE) e upsert via Chroma(client=...). `app/routes.py` — POST /upload (UploadFile → salvar em /app/data → process_uploaded_file → ingest_dataframe_to_chroma, extensões .csv/.xlsx/.xls); POST /predict mantido. `src/rag_engine.py` — RAG usa VectorStore via HttpClient quando CHROMA_HOST definido; CallbackHandler Langfuse com LANGFUSE_HOST para rastreamento em tempo real (tokens, groundedness). **Conclusão da infraestrutura de produção LLMOps do Datathon.**
- [x] Bug de dependência do Healthcheck do Langfuse corrigido: adicionado `healthcheck` ao serviço `langfuse-server` no `docker-compose.yml` (wget -q --spider em http://localhost:3000), garantindo a subida segura da API apenas após a inicialização completa do serviço de observabilidade.
- [x] Correção TypeError no CallbackHandler do Langfuse: em `src/rag_engine.py`, remoção do argumento `host` (não suportado no Langfuse 2.x), mapeamento de `LANGFUSE_HOST` para `LANGFUSE_BASE_URL`, criação de `CallbackHandler()` sem argumentos quando habilitado e `config["callbacks"]` apenas se handler não for None; findings.md e .env.example atualizados.
- [x] Correção langfuse-server unhealthy: em `docker-compose.yml`, healthcheck do langfuse-server passou a usar `curl -f -s http://localhost:3000/` (imagem Node pode não ter wget), start_period 120s, interval 15s, retries 10 e HOSTNAME=0.0.0.0; progress.md e findings.md atualizados.
- [x] Langfuse "pending" e métricas: em `.env.example`, documentado que LANGFUSE_PUBLIC_KEY e LANGFUSE_SECRET_KEY são obrigatórios para envio de traces (senão status fica pending), reinício da API após preencher e uso da aba Traces após POST /predict; progress.md atualizado.
- [x] Garantir uso das chaves Langfuse: `src/rag_engine.py` lê LANGFUSE_PUBLIC_KEY e LANGFUSE_SECRET_KEY, inicializa Langfuse(public_key, secret_key, base_url) antes de CallbackHandler() quando as chaves existem, log de diagnóstico; `docker-compose.yml` injeta LANGFUSE_PUBLIC_KEY e LANGFUSE_SECRET_KEY no serviço api via ${LANGFUSE_PUBLIC_KEY}/${LANGFUSE_SECRET_KEY}; progress.md atualizado.
- [x] Correção 404 ao exportar spans para Langfuse: SDK Python 3.x usa OTEL; servidor `langfuse/langfuse:2` não tem endpoint OTEL. requirements.txt alterado para `langfuse>=2.0.0,<3.0.0`; findings.md documentado; progress.md atualizado.
- [x] Diretriz edital Risco de Defasagem Escolar: System Prompt em src/rag_engine.py atualizado para que a primeira frase da resposta seja obrigatoriamente a estimativa do risco (IAN 10=BAIXO, 5=MODERADO, ≤2.5=ALTO), seguida de justificativa (Destaques, IPS, IEG) e plano de ação; progress.md atualizado.
- [x] Engenharia de Qualidade (edital >80% cobertura): pytest, pytest-cov e httpx garantidos em requirements.txt; test_preprocessing.py com teste consolidado (NaNs, idade corrompida, vírgula 5,60); test_api.py com mock de get_rag e ingest_dataframe_to_chroma para /predict e /upload (sem OpenAI/ChromaDB); README.md com instruções para pytest --cov=src --cov=app; progress.md atualizado.
- [x] Ajustes finais de edital (Joblib e Documentação): em src/preprocessing.py, lógica que ao limpar os dados salva o contrato (colunas padronizadas) com joblib.dump() em app/model/contrato_dados.joblib; joblib adicionado ao requirements.txt; README.md sobrescrito com as 5 seções exigidas pela FIAP (1) Visão Geral do Projeto, 2) Estrutura do Projeto, 3) Instruções de Deploy, 4) Exemplos de Chamadas à API, 5) Etapas do Pipeline de Machine Learning); progress.md atualizado.

## Vitória
**Projeto finalizado e pronto para entrega.** Todas as fases do task_plan e exigências do edital foram cumpridas: API POST /predict e POST /upload operacionais com RAG, ChromaDB e Langfuse; serialização do contrato com joblib; README com as 5 seções FIAP; testes e cobertura >80%; diretriz de Risco de Defasagem Escolar (IAN) no System Prompt. O sistema está pronto para avaliação da banca.

## Arquivos Criados/Editados
- `requirements.txt` — dependências do projeto (incl. langchain-core, langchain-chroma, pytest-cov).
- `Dockerfile` — imagem de produção (Python 3.11-slim, uvicorn).
- `.env.example` — template de variáveis de ambiente (OpenAI, Langfuse).
- `.gitignore` — exclusão de .env, __pycache__, chroma_db/*, venv, etc.
- Estrutura: `app/`, `app/model/`, `app/model/chroma_db/` (com `.gitkeep`), `src/`, `tests/`.
- `src/preprocessing.py` — clean_and_standardize_pede (contrato PEDE, decimais BR, FASE string, duplicadas, nulos).
- `src/feature_engineering.py` — build_semantic_chunk (template narrativo PEDE para embeddings/RAG).
- `src/train.py` — build_and_persist_chroma (Document com RA/ANO, OpenAIEmbeddings, Chroma em app/model/chroma_db).
- `src/rag_engine.py` — classe RAG (retriever filter RA, system prompt Psicopedagogo com diretriz Risco de Defasagem Escolar/IAN, gpt-4o-mini, Langfuse no invoke); `query()` retorna `(resposta, documentos_usados)`.
- `app/__init__.py`, `app/main.py`, `app/routes.py` — API FastAPI e POST /predict (PredictRequest, PredictResponse com resposta + documentos_usados, 404 para aluno não encontrado).
- `tests/test_preprocessing.py` — testes de nulos (0.0 e "Sem registro no período") e colunas oficiais.
- `tests/test_api.py` — TestClient, mock de get_rag e ingest_dataframe_to_chroma; /predict (200, 404, 422) e /upload (200, 422, 500); sem OpenAI/ChromaDB.
- `README.md` — instruções de testes e cobertura (pytest --cov=src --cov=app) para a banca.
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
- `requirements.txt` — adicionado python-multipart para upload de arquivos no FastAPI.
- `docker-compose.yml` — criado: rede rag_network; serviços langfuse-db (postgres:15, volume postgres-data, healthcheck pg_isready), langfuse-server (langfuse/langfuse:latest, 3000:3000, DATABASE_URL, depends langfuse-db healthy), chromadb (chromadb/chroma:latest, 8000:8000, volume chroma-data, IS_PERSISTENT, healthcheck heartbeat), api (build ., 8001:8000, volume ./data:/app/data, CHROMA_HOST/LANGFUSE_HOST, uvicorn --reload, depends chromadb e langfuse-server healthy).
- `docker-compose.prod.yml` — override: api comando --workers 4 sem --reload; restart: always em todos os serviços; volume /app/data mantido.
- `data/.gitkeep` — diretório data/ na raiz para persistir uploads (bind mount no Docker).
- `.env.example` — completo com CHROMA_HOST, LANGFUSE_HOST e comentário DATABASE_URL para referência do Langfuse.
- `src/preprocessing.py` (Step 3) — process_uploaded_file (load_pede_data → dedup → MAPEAMENTO_DINAMICO + MAPEAMENTO_VARIANTES → IPP 0.0 → decimais BR → IDADE coerce int → clean_and_standardize_pede); COLUNAS_OFICIAIS/NUMERICAS/QUALITATIVAS estendidas com NOME_ANONIMIZADO e NOTA_MAT/PORT/ING; MAPEAMENTO_DINAMICO (variações por ano).
- `tests/test_preprocessing.py` (Step 3) — fixtures com novas colunas do contrato; testes process_uploaded_file: mapeamento dinâmico, IPP ausente, decimais BR e idade corrompida, vírgula decimal, remoção de duplicatas.
- `src/train.py` (Step 4) — _get_chroma_http_client(), ingest_dataframe_to_chroma(df) com cast RA/ANO/IDADE/FASE para tipos nativos e add_documents no Chroma HTTP.
- `src/rag_engine.py` (Step 4) — RAG.__init__: Chroma com client=chromadb.HttpClient quando CHROMA_HOST; CallbackHandler(host=LANGFUSE_HOST) quando presente.
- `app/routes.py` (Step 4) — POST /upload (UploadFile, UPLOAD_DIR=/app/data, process_uploaded_file, ingest_dataframe_to_chroma, UploadResponse); POST /predict inalterado.