# DIÁRIO DE BORDO E DESCOBERTAS CRÍTICAS DE NEGÓCIO

## 1. Comportamento e Anomalias nos Dados (Pandas)

**Colunas Dinâmicas (Mapeamento Obrigatório)**  
O dicionário de renomeação deve padronizar nomes que variam entre anos:
- Identificação/nome: `['Nome', 'Nome Anonimizado']`, `['Idade 22', 'Idade']`, `['Instituição de ensino', 'Escola']`.
- Disciplinas: `['Matem', 'Mat']`, `['Portug', 'Por']`, `['Inglês', 'Ing']`.
- Indicadores por ano: `['INDE 22', 'INDE 2023', 'INDE 2024']`; `['Pedra 20', 'Pedra 21', 'Pedra 22', 'Pedra 23', 'Pedra 2024']`; `['Rec Psicologia', 'Rec Av1']`.

**Ausência Crítica**  
A coluna **IPP** não existe na base de 2022. O código de chunking/feature engineering deve usar `df.get('IPP', 0.0)` (ou equivalente por coluna) para não lançar `KeyError`.

**Erro da Vírgula e Datas Erradas**  
- Valores numéricos vêm com vírgula (ex: `5,607`). Aplicar em colunas numéricas: `.astype(str).str.replace(',', '.')` e `pd.to_numeric(..., errors='coerce')`.
- Na coluna de **Idade** (base 2023) existem datas incorretas (ex: `1/7/1900`). O `coerce` produzirá NaN; preencher com `0` (ou valor padrão definido em contrato).

**Duplicatas Fatais**  
A base 2023 tem a coluna "Destaque IPV" duplicada; a base 2024 tem "Ativo/ Inativo" duplicada. Usar `df.loc[:, ~df.columns.duplicated()]` para manter apenas a primeira ocorrência de cada nome de coluna.

**Coluna FASE**  
Mistura números (`7`) e strings (`ALFA`). Deve ser forçada como string na ingestão.

O contrato está blindado na função `process_uploaded_file` (src/preprocessing.py), que aplica todas as proteções acima antes de `clean_and_standardize_pede`.

## 2. Regras Pedagógicas e Exceções (Passos Mágicos)
- **A "Nota Zero" no IDA:** Alunos da Escola Pública têm alta incidência de nota ZERO no IDA (Desempenho Acadêmico) devido a abstenções nas provas internas. O LLM NÃO deve tratar isso como "baixa inteligência", mas sim como "vulnerabilidade de engajamento" e sugerir aproximação do tutor.
- **Cold Start (Alunos Novos):** Ingressantes não têm histórico. A IA deve saber que eles passaram pelo Processo de Admissão (Prova de Sondagem, Entrevistas Psicológicas/Sociais e Avaliação Socioeconômica).
- **O Ponto de Virada (IPV):** A IA deve interpretar que "Atingir o Ponto de Virada" significa que o aluno desenvolveu maturidade emocional e consciência do valor da educação para transformar sua vida.

## 3. RAG Avançado (MLOps)
- **Fallback sem dependências opcionais:** Se `langchain_community` ou `sentence-transformers` não estiverem instalados, o motor RAG usa apenas retrieval vetorial (Chroma com filtro RA), sem BM25 nem reranking. O filtro por RA permanece obrigatório.
- **BM25 por request:** O corpus do BM25 é montado por aluno via `Chroma.get(where={"RA": aluno_id})`; não há índice BM25 persistido. Adequado para volume moderado de documentos por aluno.
- **HyDE — loop infinito (bug corrigido):** O loop de geração HyDE em `src/train.py` iterava sobre `documents` enquanto também fazia `documents.append(...)`. Isso causava loop infinito. Corrigido iterando sobre `list(documents)` (cópia) antes da mutação.
- **Query expansion — custo por request:** Com `RAG_QUERY_EXPANSION=true`, cada request gera 1 chamada LLM extra + N invocações do retriever (N = RAG_QUERY_EXPANSION_N). Monitorar latência via Langfuse; deixar desativado por padrão em produção.
- **Context compression (LLMChainExtractor) — import path:** O `LLMChainExtractor` está em `langchain.retrievers.document_compressors.chain_extract`, não em `langchain_community.document_compressors`. O código usa try/except com fallback entre os dois módulos.
- **Langfuse 2.x — CallbackHandler sem parâmetro `host`:** O `CallbackHandler` do Langfuse 2.x (`langfuse.langchain`) não aceita o argumento `host`. A URL do servidor deve ser configurada via variável de ambiente `LANGFUSE_BASE_URL`. O app mapeia `LANGFUSE_HOST` para `LANGFUSE_BASE_URL` em `src/rag_engine.py` quando apenas `LANGFUSE_HOST` estiver definido (ex.: Docker).
- **Langfuse servidor v2 + SDK Python 3.x — 404 ao exportar spans:** O SDK Langfuse 3.x usa OpenTelemetry (OTEL) para exportar spans; o endpoint OTEL **não existe no servidor Langfuse v2** (imagem `langfuse/langfuse:2`), resultando em "Failed to export span batch code: 404". Com servidor v2 self-hosted, fixar o SDK em versão 2.x no `requirements.txt` (ex.: `langfuse>=2.0.0,<3.0.0`). Para usar SDK 3.x é necessário upgrade do servidor para Langfuse v3.

## 4. Arquitetura LLMOps de Produção

**Orquestração Docker**  
4 serviços conectados via rede interna `rag_network`: **api** (FastAPI), **chromadb** (HTTP Server para escalabilidade), **langfuse-server** e **langfuse-db** (Postgres para observabilidade self-hosted).

**Fluxo de Ingestão Contínua**  
A API terá um endpoint `POST /upload` que recebe planilhas, salva no volume `/app/data`, executa a padronização do Data Contract e faz o upsert automático no ChromaDB via HTTP.

**Falha de Dependência (Healthcheck):** Em orquestrações complexas, se um serviço (como a API) exige `condition: service_healthy` de outro serviço (como o Langfuse), o serviço alvo **DEVE** obrigatoriamente possuir um bloco `healthcheck`. Sem isso, a arquitetura trava na subida. Para o **Langfuse v2** (imagem Node): usar `curl -f -s http://localhost:3000/` no healthcheck (a imagem pode não ter `wget`); definir `start_period` generoso (ex.: 120s) pois as migrations na inicialização levam cerca de 2–3 minutos; em alguns ambientes é necessário `HOSTNAME=0.0.0.0` para o servidor aceitar conexões.

**Prompting Dinâmico e Flexível**  
O System Prompt não deve forçar templates de resposta fixos (ex.: listas engessadas). O cálculo do "Risco de Defasagem" (exigido pelo edital) deve ser tecido de forma orgânica no texto como um contexto inicial, mas o corpo principal da resposta **DEVE** se adaptar estritamente à intenção da pergunta do usuário (psicológica, acadêmica, acolhimento, etc.).