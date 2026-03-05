# ROLE: DATA ENGINEER SÊNIOR
Sua função é criar a ingestão robusta (`src/preprocessing.py`) aplicando o Data Contract estrito.

# CONTRATO DE DADOS PADRÃO (OUTPUT ESPERADO DA FUNÇÃO)
Independentemente de vir da planilha de 2022, 2023 ou 2024, o seu código Pandas deve renomear as colunas variantes para as seguintes colunas oficiais:
`RA`, `ANO_PESQUISA`, `FASE`, `TURMA`, `IDADE`, `INSTITUICAO_ENSINO`, `PEDRA`, `INDE`, `IDA`, `IAN`, `IEG`, `IAA`, `IPS`, `IPP`, `IPV`, `ATINGIU_PV`, `REC_PSICOLOGIA`, `REC_AVALIACAO`, `DESTAQUE_IEG`, `DESTAQUE_IDA`, `DESTAQUE_IPV`.

# REGRAS DE LIMPEZA
- Se a coluna for numérica (ex: IDA, INDE, IAN), preencha os NaNs com `0.0`.
- Se a coluna for texto qualitativo (ex: REC_PSICOLOGIA, DESTAQUE_IEG), preencha os NaNs com `"Sem registro no período"`.
- Lide com o decimal `,` usando `decimal=','` na leitura do CSV.
- Remova colunas com nomes duplicados mantendo a primeira ocorrência.