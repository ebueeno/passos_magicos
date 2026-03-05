# ROLE: MLOPS & BACKEND ENGINEER
Sua função é "Treinar" o RAG, Servir a API (FastAPI) e monitorar via Langfuse.

# REGRAS DO PIPELINE
1. **Serialização (`src/train.py`):** Ao vetorizar com ChromaDB e `OpenAIEmbeddings`, o argumento `persist_directory` DEVE ser `"./app/model/chroma_db"`. Em cada `Document`, o metadado `{"RA": row['RA'], "ANO": row['ANO_PESQUISA']}` é OBRIGATÓRIO.
2. **Motor e Monitoramento (`src/rag_engine.py`):** Use o `gpt-4o-mini`. O `retriever` deve filtrar a busca usando `filter={"RA": aluno_id}`. É MANDATÓRIO importar e passar o `CallbackHandler` do Langfuse no método `.invoke()` para o painel de drift/tokens do edital.
3. **API (`app/routes.py`):** Endpoint exigido: `POST /predict`. Pydantic Input: `{"aluno_id": "str", "pergunta": "str"}`. Trate erros `404` caso o aluno não exista no banco.