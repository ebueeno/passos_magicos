# ROLE: NLP & RAG ENGINEER
Sua função em `src/feature_engineering.py` é transformar a linha padronizada do Pandas em um Parágrafo Semântico para os Embeddings da OpenAI.

# A FÓRMULA DE CHUNKING (TEMPLATE)
Crie a função `build_semantic_chunk(row: pd.Series) -> str` que retorne EXATAMENTE esta estrutura humanizada:

"No ano letivo de [ANO_PESQUISA], o aluno [RA] (Idade: [IDADE], Fase: [FASE], Instituição: [INSTITUICAO_ENSINO]) foi classificado com a Pedra [PEDRA] possuindo INDE geral de [INDE]. Atingiu o Ponto de Virada: [ATINGIU_PV].
Avaliação Psicológica (IPS: [IPS]): O parecer da equipe foi '[REC_PSICOLOGIA]'. O aluno se autoavaliou com nota [IAA] de bem-estar.
Avaliação Acadêmica e Engajamento (IDA: [IDA], IAN: [IAN], IEG: [IEG], IPP: [IPP]): A recomendação do conselho foi '[REC_AVALIACAO]'. O destaque acadêmico foi '[DESTAQUE_IDA]', e de engajamento '[DESTAQUE_IEG]'. Sobre sua integração e valores: '[DESTAQUE_IPV]'."