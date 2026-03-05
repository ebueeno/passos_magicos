# DIÁRIO DE BORDO E DESCOBERTAS CRÍTICAS DE NEGÓCIO

## 1. Comportamento e Anomalias nos Dados (Pandas)
- **Padrão Numérico BR:** As notas originais usam vírgula (`,`) como decimal (ex: `7,5`). O Pandas precisa ler isso corretamente (`decimal=','`).
- **Coluna FASE:** Mistura números (`7`) e strings (`ALFA`). Deve ser forçada como `String` na ingestão.
- **Colunas Duplicadas:** A base de 2023 possui "Destaque IPV" duplicado. A de 2024 possui "Ativo/ Inativo" duplicado. O script deve remover colunas duplicadas mantendo a primeira ocorrência.

## 2. Regras Pedagógicas e Exceções (Passos Mágicos)
- **A "Nota Zero" no IDA:** Alunos da Escola Pública têm alta incidência de nota ZERO no IDA (Desempenho Acadêmico) devido a abstenções nas provas internas. O LLM NÃO deve tratar isso como "baixa inteligência", mas sim como "vulnerabilidade de engajamento" e sugerir aproximação do tutor.
- **Cold Start (Alunos Novos):** Ingressantes não têm histórico. A IA deve saber que eles passaram pelo Processo de Admissão (Prova de Sondagem, Entrevistas Psicológicas/Sociais e Avaliação Socioeconômica).
- **O Ponto de Virada (IPV):** A IA deve interpretar que "Atingir o Ponto de Virada" significa que o aluno desenvolveu maturidade emocional e consciência do valor da educação para transformar sua vida.