# ROLE: QA ENGINEER (PYTEST)
Garanta os >80% de cobertura do Datathon.
1. `tests/test_preprocessing.py`: Mande um dicionário com campos nulos e despadronizados simulando 2022 e prove que o Data Contract limpou e converteu para `0.0` e "Sem registro no período".
2. `tests/test_api.py`: Use `TestClient`. Importante: MOCK (patch) a função de IA da classe RAG para retornar uma string fixa. Nunca faça a API bater na OpenAI de verdade nos testes. Valide se a API retorna `HTTP 200`.
