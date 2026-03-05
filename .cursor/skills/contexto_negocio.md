# O DOMÍNIO DA ASSOCIAÇÃO PASSOS MÁGICOS (PEDE)

## O Dicionário de Indicadores (Nunca invente significados):
- `INDE` (Índice de Desenvolvimento Educacional): A nota principal. Classifica os alunos em Pedras de evolução: Quartzo (menor), Ágata, Ametista, e Topázio (maior).
- `IDA` (Desempenho Acadêmico): Média das provas.
- `IAN` (Adequação de Nível): Mede a defasagem escolar (idade do aluno vs série esperada).
- `IEG` (Engajamento): Entrega de lições de casa e participação.
- `IAA` (Autoavaliação): Como o aluno se sente sobre si mesmo e família. Notas baixas exigem intervenção psicológica urgente.
- `IPS` (Psicossocial): Avaliação feita por psicólogas (Dinâmica familiar, emocional).
- `IPP` (Psicopedagógico): Avaliação de professores (Raciocínio lógico e cognitivo).
- `IPV` (Ponto de Virada): Nível de integração aos princípios da ONG e maturidade.

## Dados Qualitativos de Texto (Para o RAG ler):
- `DESTAQUE_IEG`, `DESTAQUE_IDA`, `DESTAQUE_IPV`: Começam com "Destaque:" ou "Melhorar:" seguidos de frases como "A sua boa entrega das lições" ou "Empenhar-se mais".
- `REC_PSICOLOGIA` (ou REC_PSICO): Textos como "Requer avaliação", "Sem limitações", "Não atendido".
- `REC_AVALIACAO`: Decisões de conselho como "Promovido de Fase", "Mantido na Fase atual".