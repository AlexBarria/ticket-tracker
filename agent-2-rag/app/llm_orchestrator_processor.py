"""
Defines an SQL RAG agent that retrieves data from a SQL DB using natural language queries.
"""
from langchain_core.messages import AnyMessage, SystemMessage, BaseMessage
from langchain_openai.chat_models import ChatOpenAI
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

_SYSTEM_PROMPT = """
You are a helpful assistant that answer questions about user expenses.
You can use a tool to query a SQL database to get the required data. This tool is called only using natural language, NO code or SQL syntax.
"""


class OrchestratorAgent:

    def __init__(self, model: str, tools: list):
        self.client = ChatOpenAI(model=model).bind_tools(tools)

    def query(self, question: list[AnyMessage]) -> BaseMessage:
        try:
            if question and getattr(question[0], "content", None) != _SYSTEM_PROMPT.strip():
                question.insert(0, SystemMessage(content=_SYSTEM_PROMPT.strip()))
            logger.info(f"Orchestrator processing question: {question}")
            response = self.client.invoke(question)
            logger.info(f"Orchestrator response: {response}")
            return response
        except Exception as e:
            logger.error(f"An error occurred in OrchestratorAgent: {e}")
            raise
