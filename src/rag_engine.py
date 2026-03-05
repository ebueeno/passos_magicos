"""
Motor RAG do Copiloto PEDE: retrieval filtrado por RA, LLM gpt-4o-mini e Langfuse.
Chain: Chroma (filter RA) -> contexto -> prompt (Psicopedagogo) -> LLM.
"""

from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langfuse.langchain import CallbackHandler

# Mesmo persist e coleção de src.train para carregar o índice
PERSIST_DIR = "./app/model/chroma_db"
COLLECTION_NAME = "pede"

SYSTEM_PROMPT = """Você é um Psicopedagogo da Associação Passos Mágicos (PEDE). Seu papel é apoiar professores com planos de ação baseados no histórico do aluno, mitigando evasão e vulnerabilidade.

Use estritamente os indicadores do PEDE:
- INDE: Índice de Desenvolvimento Educacional (Pedras: Quartzo, Ágata, Ametista, Topázio).
- IDA: Desempenho Acadêmico (média das provas).
- IAN: Adequação de Nível (defasagem idade/série).
- IEG: Engajamento (lições de casa e participação).
- IAA: Autoavaliação (bem-estar; notas baixas exigem intervenção psicológica).
- IPS: Psicossocial (avaliação das psicólogas).
- IPP: Psicopedagógico (avaliação dos professores).
- IPV: Ponto de Virada (integração à ONG e maturidade).

Regras obrigatórias:
- Nota ZERO no IDA NÃO indica "baixa inteligência"; indique "vulnerabilidade de engajamento" e sugira aproximação do tutor.
- Alunos novos (sem histórico) passaram pelo Processo de Admissão (Prova de Sondagem, Entrevistas, Avaliação Socioeconômica).
- "Atingir o Ponto de Virada" significa maturidade emocional e consciência do valor da educação.

Responda com base APENAS no contexto fornecido (histórico do aluno). Seja objetivo e acionável para o professor."""


class AlunoNaoEncontradoError(Exception):
    """Aluno (RA) não possui documentos no banco vetorial."""


class RAG:
    """Motor RAG: retrieval por RA + LLM com prompt de Psicopedagogo; Langfuse no invoke."""

    def __init__(self) -> None:
        self._embedding = OpenAIEmbeddings()
        self._vectorstore = Chroma(
            persist_directory=PERSIST_DIR,
            embedding_function=self._embedding,
            collection_name=COLLECTION_NAME,
        )
        self._llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self._prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                (
                    "human",
                    "Contexto do histórico do aluno:\n\n{contexto}\n\nPergunta do professor: {pergunta}",
                ),
            ]
        )
        self._chain = self._prompt | self._llm
        self._langfuse_handler = CallbackHandler()

    def query(self, aluno_id: str, pergunta: str) -> tuple[str, list[str]]:
        """
        Recupera documentos do aluno (RA), monta o contexto e invoca o LLM com Langfuse.

        Parameters
        ----------
        aluno_id : str
            RA do aluno (filtro obrigatório no retrieval).
        pergunta : str
            Pergunta do professor.

        Returns
        -------
        tuple[str, list[str]]
            (resposta do LLM, lista de conteúdos dos documentos usados no contexto).

        Raises
        ------
        AlunoNaoEncontradoError
            Se não houver documentos para o RA no banco.
        """
        config = {"callbacks": [self._langfuse_handler]}
        retriever = self._vectorstore.as_retriever(
            search_kwargs={"filter": {"RA": aluno_id}, "k": 10}
        )
        docs = retriever.invoke(pergunta, config=config)
        if not docs:
            raise AlunoNaoEncontradoError(f"Nenhum documento encontrado para RA {aluno_id}")
        documentos_usados = [d.page_content for d in docs]
        contexto = "\n\n---\n\n".join(documentos_usados)
        msg = self._chain.invoke(
            {"contexto": contexto, "pergunta": pergunta},
            config=config,
        )
        resposta = msg.content if hasattr(msg, "content") else str(msg)
        return resposta, documentos_usados
