# ROLE: MLOPS & BACKEND ENGINEER
Sua função é "Treinar" o RAG, Servir a API (FastAPI) e monitorar via Langfuse.

# REGRAS DO PIPELINE
1. **Serialização (`src/train.py`):** Ao vetorizar com ChromaDB e `OpenAIEmbeddings`, o argumento `persist_directory` DEVE ser `"./app/model/chroma_db"`. Em cada `Document`, o metadado `{"RA": row['RA'], "ANO": row['ANO_PESQUISA']}` é OBRIGATÓRIO.
2. **Motor e Monitoramento (`src/rag_engine.py`):** Use o `gpt-4o-mini`. O `retriever` deve filtrar a busca usando `filter={"RA": aluno_id}`. É MANDATÓRIO importar e passar o `CallbackHandler` do Langfuse no método `.invoke()` para o painel de drift/tokens do edital.
3. **API (`app/routes.py`):** Endpoint exigido: `POST /predict`. Pydantic Input: `{"aluno_id": "str", "pergunta": "str"}`. Trate erros `404` caso o aluno não exista no banco.

# RAG AVANÇADO

Conceitos e técnicas do pipeline de Retrieval-Augmented Generation (baseado em LangChain + ChromaDB):

## 1. Metadata e Self-Querying Retriever
- **Metadata obrigatório:** Em cada `Document` incluir metadados estruturados (ex.: `RA`, `ANO_PESQUISA`) para filtragem no retriever.
- **Self-querying:** Dada uma pergunta em linguagem natural, um LLM gera uma *structured query* + filtros; o retriever aplica essa query ao vector store. Assim combina similaridade semântica com filtros por metadados.
- **AttributeInfo:** Definir nome, descrição e tipo de cada campo de metadata para o chain de construção de query (ex.: `year`, `topics`, `subtopic`).

## 2. Hypothetical Questions (HyDE-style)
- Para cada chunk/documento, gerar *perguntas hipotéticas* que o trecho poderia responder.
- Indexar essas perguntas no vector store; manter vínculo com o *parent chunk* (e metadados) via metadata.
- Na busca: a query do usuário é comparada às perguntas hipotéticas; retorna-se o parent chunk (e metadata) do melhor match. Aumenta diversidade e recall.

## 3. Hybrid Search
- Combinar **busca por keywords** (BM25) e **busca vetorial/semântica** (embedding + similarity).
- Usar `EnsembleRetriever` com lista de retrievers (ex.: `BM25Retriever` + retriever do Chroma) e pesos (ex.: `[0.5, 0.5]`).
- BM25 cobre termos exatos; vetorial cobre significado; híbrido melhora cobertura.

## 4. Reranking (Cross-Encoder)
- **Reranking:** reordenar os documentos já recuperados com um modelo mais preciso (cross-encoder), em vez de rankear todo o banco.
- **Cross-encoder:** modelo que recebe (query, documento) e devolve score de relevância; ex.: `cross-encoder/ms-marco-MiniLM-L-6-v2`.
- Aplicar via `CrossEncoderReranker` (top_n) + `ContextualCompressionRetriever` em cima do retriever base. Custo e latência maiores; usar só sobre os chunks já recuperados.

## 5. Context Compression
- Reduzir o texto dos chunks recuperados mantendo só o que é relevante para a pergunta.
- **LLMChainExtractor:** usa o LLM para extrair/reescrever apenas as partes do documento pertinentes à query.
- Encadear com `ContextualCompressionRetriever`: base_compressor = extractor, base_retriever = retriever (ex.: ensemble ou pós-rerank).

## 6. Prompt Enhancement / Query Expansion
- **Definição:** Query expansion, or prompt enhancement, involves modifying a user's original query by adding synonyms, related terms, or rephrased variations to improve search results or comprehension by a language model. This process aims to capture a broader context and increase the chances of retrieving relevant information.
- **Implementação:** Expandir a pergunta do usuário com sinônimos, termos relacionados ou reformulações (via LLM); gerar várias versões da pergunta (ex.: lista de 3+ versões).
- Fazer retrieval para cada versão; unir e deduplicar documentos para formar o contexto final.
- Aumenta recall quando a redação da pergunta difere da redação dos documentos.

## Ordem sugerida no pipeline

Fluxo recomendado para uma requisição `POST /predict`: da pergunta do usuário até a resposta gerada.

| # | Etapa | Obrigatório? | Entrada → Saída | Observação |
|---|--------|----------------|------------------|------------|
| 1 | **Query expansion** | Opcional | 1 pergunta → N versões (sinônimos/reformulações) | Aumenta recall; custo extra de LLM por request. |
| 2 | **Retrieval** | Sim | query(s) + `aluno_id` → lista de chunks | Self-query (metadata) + híbrido (BM25 + vetorial). Filtro **obrigatório** `filter={"RA": aluno_id}`. |
| 3 | **Reranking** | Recomendado | top‑k chunks → mesma lista reordenada por relevância | Cross-encoder só sobre os k recuperados (não no banco inteiro). Custo/latência moderados. |
| 4 | **Context compression** | Opcional | chunks reordenados → chunks enxutos (só trechos relevantes) | LLMChainExtractor; reduz ruído e tamanho do contexto. |
| 5 | **Geração** | Sim | contexto final + pergunta → resposta | `gpt-4o-mini`; **sempre** passar `CallbackHandler` do Langfuse no `.invoke()`. |

- **Mínimo viável (edital):** 2 → 5 (retrieval com filtro por RA + geração com Langfuse).
- **Para melhor qualidade:** adicionar 3 (reranking); depois 1 e 4 conforme necessidade de recall e clareza.
