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
import json
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


class AgentPipeline:

    def __init__(self):
        self.sql_rag = SQLRagAgent(DBRepository(os.getenv("DATABASE_URL")))

        @tool
        def process_sql_rag(query: str) -> str:
            """ Retrieves data from database based on a requirement in natural language."""
            return str(self.sql_rag.query(query))

        @tool
        def process_web_search(question: str) -> str:
            """ Searches the web and returns a concise answer with sources. Use for up-to-date or external info. """
            web_url = os.getenv("WEB_AGENT_URL", "http://tool-web:8000/search")
            payload = {
                "question": question,
                "top_k": 5,
                "fetch_pages": True,
            }
            try:
                req = Request(web_url, data=json.dumps(payload).encode("utf-8"),
                              headers={"Content-Type": "application/json"})
                with urlopen(req, timeout=20) as resp:
                    body = resp.read().decode("utf-8")
                data = json.loads(body)
                summary = data.get("summary") or ""
                sources = data.get("sources") or []
                src_lines = []
                for s in sources:
                    title = s.get("title") or s.get("url") or "source"
                    url = s.get("url") or ""
                    src_lines.append(f"- {title} ({url})")
                src_block = "\n".join(src_lines)
                if summary and src_block:
                    return f"{summary}\n\nSources:\n{src_block}"
                elif src_block:
                    return f"Sources:\n{src_block}"
                else:
                    return summary or "No results."
            except (HTTPError, URLError, TimeoutError, ValueError) as e:
                return f"Web search error: {e}"

        tools = [process_sql_rag, process_web_search]
        self.orchestrator = OrchestratorAgent(model="gpt-4o", tools=tools)

        graph = StateGraph(MessagesState)
        graph.add_node("orchestrator", self.process_orchestrator)
        graph.add_node("tools", ToolNode(tools))
        graph.add_node("guardrails", self.process_guardrails)
        graph.set_entry_point("orchestrator")
        graph.add_conditional_edges("orchestrator", self.select_next_step)
        graph.add_edge("tools", "orchestrator")
        graph.add_edge("guardrails", END)
        checkpointer = MemorySaver()
        self.graph = graph.compile(checkpointer=checkpointer)

    def process_orchestrator(self, state: MessagesState):
        messages = state['messages']
        response = self.orchestrator.query(messages)
        return {"messages": [response]}  # Returns

    @staticmethod
    def select_next_step(state: MessagesState) -> Literal["tools", "guardrails"]:
        messages = state['messages']
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools"
        return "guardrails"

    @staticmethod
    def process_guardrails(state: MessagesState):
        if os.getenv("GUARDRAILS_ENABLED", "false").lower() == "false":
            return {"messages": state['messages']}
        # Extract the last messages
        messages = state['messages']
        answer = messages[-1].content
        guardrails_url = os.getenv("GUARDRAILS_URL", "http://guardrails:8000/validate")
        payload = {
            "guard": "toxic",
            "prompt": answer
        }
        try:
            req = Request(guardrails_url, data=json.dumps(payload).encode("utf-8"),
                          headers={"Content-Type": "application/json"})
            with urlopen(req, timeout=20) as response:
                if response.status != 200:
                    response_text = response.read().decode("utf-8")
                    raise Exception(f"{response_text}")
            return {"messages": messages}
        except Exception as e:
            messages.append(HumanMessage(content=f"Guardrails validation error: {e}"))
            return {"messages": messages}

    def run(self, question: str) -> str:
        initial_message = HumanMessage(content=question)
        final_state = self.graph.invoke({"messages": [initial_message]}, config={"configurable": {"thread_id": 42}})
        final_message = final_state['messages'][-1]
        return final_message.content
