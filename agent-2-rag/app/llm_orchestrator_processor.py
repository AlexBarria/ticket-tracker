from langchain_core.messages import AnyMessage, SystemMessage, BaseMessage
from langchain_openai.chat_models import ChatOpenAI
import logging
from openinference.instrumentation.langchain import LangChainInstrumentor

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

_SYSTEM_PROMPT = """
You are a helpful assistant that answers questions about user expenses.

TOOLS AVAILABLE:
- process_sql_rag(query: str): Use this FIRST to retrieve information from the internal SQL database using a natural language query (no SQL code). Prefer this tool for anything related to the user's tickets, expenses, metrics, summaries or any data likely stored internally.
- process_web_search(question: str): Use this ONLY IF the SQL result is insufficient, empty, or the user explicitly asks for external, up-to-date or general-world information (e.g., prices in the market, news, public best practices).

DECISION POLICY:
1) Always attempt process_sql_rag first when the question could be answered with internal data.
2) If the SQL result does not contain the needed answer, then call process_web_search.
3) If the question is clearly about external or current world facts, you may directly call process_web_search.

"""


class OrchestratorAgent:
    """
    An orchestrator agent that uses a language model to process natural language queries and decide if a tool should be
    used, or if a direct answer can be provided.
    """

    def __init__(self, model: str, tools: list):
        """
        Initializes the OrchestratorAgent with a language model and available tools.
        """
        # Enable OpenInference instrumentation for LangChain to capture LLM spans and token usage
        try:
            LangChainInstrumentor().instrument()
        except Exception:
            pass
        self.client = ChatOpenAI(model=model).bind_tools(tools)

    def query(self, question: list[AnyMessage]) -> BaseMessage:
        """
        Processes a natural language question using the orchestrator agent.

        Args:
            question (list[AnyMessage]): The input question as a list of messages.
        Returns:
            BaseMessage: The response from the orchestrator agent.
        """
        try:
            if question and getattr(question[0], "content", None) != _SYSTEM_PROMPT.strip():
                question.insert(0, SystemMessage(content=_SYSTEM_PROMPT.strip()))
            logger.info(f"Orchestrator processing question: {question}")
            response = self.client.invoke(question)
            logger.info(f"Orchestrator response: {response}")

            # Log token usage if available
            if hasattr(response, 'response_metadata'):
                usage = response.response_metadata.get('token_usage', {})
                if usage:
                    logger.info(f"Tokens used - prompt: {usage.get('prompt_tokens')}, completion: {usage.get('completion_tokens')}, total: {usage.get('total_tokens')}")

            return response
        except Exception as e:
            logger.error(f"An error occurred in OrchestratorAgent: {e}")
            raise
