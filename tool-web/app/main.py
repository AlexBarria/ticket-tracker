"""
Web search service using FastAPI and Tavily API.
"""
# tool-web/app/main.py
import os
import logging
from typing import List, Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from openinference.instrumentation.openai import OpenAIInstrumentor

# Optional: summarization via OpenAI to produce concise answers
USE_SUMMARIZATION = True

logger = logging.getLogger(__name__)

app = FastAPI(title="Agent Web - Search")


def _setup_tracing(app: FastAPI) -> None:
    try:
        service_name = os.getenv("OTEL_SERVICE_NAME", "tool-web")
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "http://phoenix:4317")
        provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        # Instrument frameworks/clients
        FastAPIInstrumentor().instrument_app(app)
        RequestsInstrumentor().instrument()
        try:
            HTTPXClientInstrumentor().instrument()
        except Exception:
            pass
    except Exception as e:
        logging.getLogger(__name__).warning(f"Tracing setup failed: {e}")


_setup_tracing(app)

# Enable OpenInference OpenAI SDK instrumentation to capture LLM spans and token usage
try:
    OpenAIInstrumentor().instrument()
except Exception as _:
    pass


class SearchRequest(BaseModel):
    """
    Request model for web search.
    """
    question: str
    top_k: int = 5
    fetch_pages: bool = True


class Source(BaseModel):
    """
    Model representing a search source result.
    """
    url: str
    title: Optional[str] = None
    snippet: Optional[str] = None


class SearchResponse(BaseModel):
    """
    Response model for web search results.
    """
    summary: Optional[str] = None
    sources: List[Source]
    reasoning: Optional[str] = None



async def tavily_search(query: str, top_k: int) -> List[Source]:
    """Search using Tavily API (https://api.tavily.com)."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="TAVILY_API_KEY not configured")
    payload = {
        "api_key": api_key,
        "query": query,
        "max_results": max(1, min(10, top_k)),
        "search_depth": "basic",
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post("https://api.tavily.com/search", json=payload)
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Tavily error: {r.text}")
        data = r.json() or {}
        results = []
        for item in (data.get("results") or [])[:top_k]:
            results.append(
                Source(
                    url=item.get("url"),
                    title=item.get("title"),
                    snippet=item.get("content"),
                )
            )
        return results


async def fetch_page_text(url: str) -> str:
    """
    Fetch and extract text content from a web page.

    Args:
        url (str): The URL of the web page to fetch.
    Returns:
        str: The extracted text content, capped at 8000 characters.
    """
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return ""
            text = r.text
            # Very light-weight text extraction (no bs4 dependency to keep it slim)
            # Strip tags crudely
            import re
            text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.IGNORECASE)
            text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text)
            return text[:8000]  # cap
    except Exception:
        return ""


async def summarize_with_openai(question: str, snippets: List[str]) -> str:
    """
    Summarize text content using OpenAI GPT-4o model.

    Args:
        question (str): The original search question.
        snippets (List[str]): List of text snippets to summarize.
    Returns:
        str: The generated summary.
    """
    client = OpenAI()

    prompt = (
        "You are a helpful assistant. Given the question and excerpts from sources, write a concise answer.\n"
        f"Question: {question}\n"
        "Excerpts:\n" + "\n---\n".join(snippets[:5]) + "\n"
        "Cite the answer qualitatively and avoid fabricating details."
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a web research assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=256,
        )
        return resp.choices[0].message.content
    except Exception as e:
        logger.warning(f"OpenAI summarization failed: {e}")
        return ""


@app.get("/")
async def health():
    """
    Health check endpoint.
    """
    return {"status": "ok", "service": "Agent Web - Search"}


@app.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    """
    Perform a web search and optionally summarize results.

    Args:
        req (SearchRequest): The search request containing the question, number of top results, and whether to fetch
        and summarize page contents.
    Returns:
        SearchResponse: The search response containing the summary, sources, and reasoning.
    Raises:
        HTTPException: If there is an error during the search or summarization process.
    """
    sources = await tavily_search(req.question, req.top_k)
    summary = None
    if USE_SUMMARIZATION and req.fetch_pages and sources:
        snippets = []
        for s in sources[:3]:
            text = await fetch_page_text(s.url)
            if text:
                snippets.append(text)
        if snippets:
            summary = await summarize_with_openai(req.question, snippets)

    return SearchResponse(summary=summary, sources=sources, reasoning=None)
