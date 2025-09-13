from typing import Literal

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from llm_sql_processor import SQLRagAgent
from repository import DBRepository
from llm_orchestrator_processor import OrchestratorAgent
import os


class AgentPipeline:

    def __init__(self):
        self.sql_rag = SQLRagAgent(DBRepository(os.getenv("DATABASE_URL")))
        @tool
        def process_sql_rag(query: str) -> str:
            """ Retrieves data from database based on a requirement in natural language."""
            return str(self.sql_rag.query(query))
        tools = [process_sql_rag]
        self.orchestrator = OrchestratorAgent(model="gpt-4o", tools=tools)

        graph = StateGraph(MessagesState)
        graph.add_node("orchestrator", self.process_orchestrator)
        graph.add_node("tools", ToolNode(tools))
        graph.set_entry_point("orchestrator")
        graph.add_conditional_edges("orchestrator", self.select_next_step)
        graph.add_edge("tools", "orchestrator")
        checkpointer = MemorySaver()
        self.graph = graph.compile(checkpointer=checkpointer)

    def process_orchestrator(self, state: MessagesState):
        messages = state['messages']
        response = self.orchestrator.query(messages)
        return {"messages": [response]}  # Returns

    @staticmethod
    def select_next_step(state: MessagesState) -> Literal["tools", END]:
        messages = state['messages']
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools"
        return END

    def run(self, question: str) -> str:
        initial_message = HumanMessage(content=question)
        final_state = self.graph.invoke({"messages": [initial_message]}, config={"configurable": {"thread_id": 42}})
        final_message = final_state['messages'][-1]
        return final_message.content


if __name__ == "__main__":
    agent_pipeline = AgentPipeline()
    question = "What is the total amount of expenses for the last month?"
    answer = agent_pipeline.run(question)
    print(f"Final Answer: {answer}")
