# Referência da API — Copiloto Pedagógico (Passos Mágicos)

Documentação oficial para integração com a API do **Copiloto Pedagógico e Psicológico**, sistema RAG da Associação Passos Mágicos utilizado no Datathon. Esta API foi projetada para auxiliar tutores sociais e professores no acompanhamento de alunos em situação de vulnerabilidade.

---

## 1. Visão Geral (O que esperar do Copiloto)

A API expõe um modelo **RAG (Retrieval-Augmented Generation)** focado no acompanhamento psicopedagógico de alunos atendidos pela ONG Passos Mágicos. O objetivo é apoiar professores e equipe pedagógica com recomendações baseadas no histórico real de cada criança, mitigando evasão e situações de vulnerabilidade.

**Fluxo de funcionamento:**

1. O cliente envia o **ID do aluno (RA)** e uma **pergunta** (por exemplo: *"Quais indicadores devo priorizar com este aluno neste trimestre?"*).
2. O sistema busca o histórico do aluno no banco vetorial **ChromaDB**, onde estão indexados os indicadores e pareceres do **PEDE** (Programa de Acompanhamento da Passos Mágicos) — por exemplo: **INDE**, **IDA**, **IAA**, **IPS**, **IPV**, entre outros.
3. O modelo utiliza apenas esse contexto recuperado para gerar uma **resposta fundamentada** (plano de ação sugerido) e devolve, além da resposta, os **documentos usados** para garantir rastreabilidade (Groundedness), conforme boas práticas de MLOps.

O usuário final da API é um sistema ou ferramenta que auxiliará tutores sociais e professores da Passos Mágicos; as recomendações devem ser interpretadas como sugestões acionáveis, sempre considerando o contexto humano e institucional.

---

## 2. URL Base e Autenticação

### URL base

Em ambiente de desenvolvimento local, a API está disponível em:

| Ambiente   | URL base                |
|-----------|--------------------------|
| Local     | `http://localhost:8000`  |

Em produção ou em ambiente de avaliação do Datathon, a URL base será informada pela organização (ou configurada no deploy).

### Autenticação

No contexto do **Datathon da Passos Mágicos**, a API está configurada para **acesso aberto**: não é necessário enviar header de autenticação nem API Key. Caso no futuro seja implementado controle de acesso (por exemplo, `Authorization: Bearer <token>` ou header customizado), esta documentação será atualizada com as instruções correspondentes.

---

## 3. Endpoint Principal

### `POST /predict`

**Descrição:** Gera uma recomendação educacional/psicopedagógica **personalizada** com base no histórico do aluno armazenado no banco vetorial ChromaDB. O nome da rota é **estrito** e exigido pelo edital do Datathon.

| Item        | Valor                          |
|------------|---------------------------------|
| Método     | `POST`                          |
| Caminho    | `/predict`                      |
| Headers    | `Content-Type: application/json`|
| Corpo      | JSON (ver seção 4)              |

---

## 4. Schemas de Requisição (Input)

O corpo da requisição deve ser um JSON válido com a estrutura abaixo (modelo Pydantic `PredictRequest`).

| Campo       | Tipo   | Obrigatório | Descrição                                                                 |
|------------|--------|-------------|----------------------------------------------------------------------------|
| `aluno_id` | string | Sim         | Identificador do aluno (RA). Usado para filtrar o histórico no ChromaDB.   |
| `pergunta` | string | Sim         | Pergunta ou solicitação do professor/tutor em texto livre.                |

**Exemplo em JSON:**

```json
{
  "aluno_id": "123",
  "pergunta": "Quais indicadores devo priorizar com este aluno neste trimestre?"
}
```

Outros exemplos de `pergunta`:

- *"O aluno apresenta nota zero no IDA. Como devo abordar?"*
- *"Este aluno atingiu o Ponto de Virada (IPV). Que próximos passos sugerir?"*
- *"Resuma o histórico psicossocial (IPS) e dê uma recomendação."*

---

## 5. Schemas de Resposta (Output)

### Sucesso (HTTP 200)

Em caso de sucesso, o corpo da resposta segue o modelo Pydantic `PredictResponse`:

| Campo               | Tipo           | Descrição                                                                 |
|---------------------|----------------|----------------------------------------------------------------------------|
| `resposta`          | string         | Texto gerado pelo LLM: plano de ação ou recomendação psicopedagógica.    |
| `documentos_usados` | array de string| Trechos do banco vetorial (ChromaDB) utilizados como contexto para o LLM. |

O campo **`documentos_usados`** garante **rastreabilidade (Groundedness)** exigida em MLOps: é possível verificar exatamente quais trechos do histórico do aluno foram usados para gerar a recomendação, evitando alucinações e permitindo auditoria.

**Exemplo de resposta (HTTP 200):**

```json
{
  "resposta": "Com base no histórico do aluno (INDE em evolução, IDA com abstenções), priorize: 1) Aproximação do tutor para engajamento (IEG); 2) Acompanhamento da autoavaliação (IAA). A nota zero no IDA indica vulnerabilidade de engajamento, não baixo desempenho cognitivo.",
  "documentos_usados": [
    "Ano 2023 — RA 123. INDE: Ágata. IDA: 0,0 (abstenções). IAA: 5,2. IPS: estável. Destaque IEG: Melhorar entrega de lições.",
    "Ano 2024 — RA 123. INDE: Ametista. IDA: 6,5. IEG em alta. Recomendação Psicologia: Manter acompanhamento."
  ]
}
```

---

## 6. Exemplos Práticos de Integração

### cURL (terminal)

```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{"aluno_id": "123", "pergunta": "Quais indicadores devo priorizar com este aluno neste trimestre?"}'
```

### Python (requests)

```python
import requests

url = "http://localhost:8000/predict"
payload = {
    "aluno_id": "123",
    "pergunta": "Quais indicadores devo priorizar com este aluno neste trimestre?"
}

response = requests.post(url, json=payload)

if response.status_code == 200:
    data = response.json()
    print("Recomendação:", data["resposta"])
    print("Documentos usados:", data["documentos_usados"])
else:
    print("Erro:", response.status_code, response.json())
```

### Postman / Insomnia

1. **Método:** `POST`
2. **URL:** `http://localhost:8000/predict`
3. **Headers:** adicione `Content-Type: application/json`
4. **Body:** selecione **raw** e **JSON**, então cole o JSON de exemplo:

```json
{
  "aluno_id": "123",
  "pergunta": "Quais indicadores devo priorizar com este aluno neste trimestre?"
}
```

5. Envie a requisição e verifique o corpo da resposta (campos `resposta` e `documentos_usados`).

---

## 7. Tratamento de Erros e Códigos HTTP

| Código | Significado              | Quando ocorre |
|--------|--------------------------|----------------|
| **200 OK** | Sucesso              | A recomendação foi gerada. O corpo contém `resposta` e `documentos_usados`. |
| **404 Not Found** | Recurso não encontrado | O `aluno_id` (RA) **não foi encontrado** no banco vetorial ChromaDB (por exemplo, aluno novo sem histórico indexado — cenário de Cold Start). Corpo típico: `{"detail": "Aluno não encontrado no banco."}`. |
| **422 Unprocessable Entity** | Erro de validação | O JSON da requisição está inválido ou incompleto (por exemplo: falta o campo `aluno_id` ou `pergunta`, ou tipo incorreto). O corpo retorna os detalhes de validação do Pydantic/FastAPI. |
| **500 Internal Server Error** | Erro interno       | Falha no servidor (ex.: falha de comunicação com a OpenAI, timeout, ou exceção não tratada). Corpo típico: `{"detail": "Erro interno ao processar a solicitação."}`. |

**Exemplo de resposta 404:**

```json
{
  "detail": "Aluno não encontrado no banco."
}
```

**Exemplo de resposta 422 (campo obrigatório ausente):**

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "pergunta"],
      "msg": "Field required"
    }
  ]
}
```

Recomenda-se que o cliente trate explicitamente os códigos 404 (aluno não indexado) e 422 (corrigir o payload) para uma experiência adequada aos tutores que utilizam o sistema.
