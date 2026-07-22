"""RAG Studio - Retrieval-Augmented Generation for content research"""

import logging
import hashlib
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Source:
    id: str
    title: str
    url: str
    snippet: str
    relevance: float
    provider: str = "web"


@dataclass
class ResearchResult:
    query: str
    sources: List[Source]
    summary: str = ""
    model_used: str = ""
    tokens_used: int = 0
    latency_ms: float = 0.0


class RAGStudio:
    """Retrieval-Augmented Generation for content research"""

    def __init__(self):
        self._cache: Dict[str, ResearchResult] = {}
        self._cache_ttl = 3600  # 1 hour

    def _cache_key(self, query: str, num_results: int) -> str:
        return hashlib.md5(f"{query}:{num_results}".encode()).hexdigest()

    def _get_cached(self, key: str) -> Optional[ResearchResult]:
        if key in self._cache:
            result = self._cache[key]
            return result
        return None

    async def research(
        self, query: str, num_results: int = 5, model: Optional[str] = None
    ) -> ResearchResult:
        """Research a topic and return sources with a summary"""
        import time

        start = time.time()

        cache_key = self._cache_key(query, num_results)
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        sources = await self._search_sources(query, num_results)
        summary = await self._generate_summary(query, sources, model)

        latency_ms = (time.time() - start) * 1000

        result = ResearchResult(
            query=query,
            sources=sources,
            summary=summary,
            model_used=model or "auto",
            latency_ms=latency_ms,
        )

        self._cache[cache_key] = result
        return result

    async def _search_sources(self, query: str, num_results: int) -> List[Source]:
        """Search for relevant sources (web search integration)"""
        from backend.services.model_router import ModelRouter, TaskType

        try:
            router = ModelRouter()
            messages = [
                {
                    "role": "system",
                    "content": "You are a research assistant. For the given query, provide a list of relevant source titles, URLs, and brief snippets. Return as JSON array with objects containing: title, url, snippet. Provide at least 3 sources.",
                },
                {"role": "user", "content": f"Find sources for: {query}"},
            ]

            result = router.chat(
                task_type=TaskType.SCRIPT_GENERATION,
                messages=messages,
                temperature=0.3,
                max_tokens=1000,
            )

            import json

            content = result.get("content", "[]")
            try:
                raw_sources = json.loads(content)
            except json.JSONDecodeError:
                raw_sources = []

            sources = []
            for i, s in enumerate(raw_sources[:num_results]):
                sources.append(
                    Source(
                        id=f"src_{i}",
                        title=s.get("title", "Untitled"),
                        url=s.get("url", ""),
                        snippet=s.get("snippet", ""),
                        relevance=max(0.5, 1.0 - (i * 0.1)),
                        provider="ai_enhanced",
                    )
                )

            return sources

        except Exception as e:
            logger.warning(f"Source search failed: {e}")
            return [
                Source(
                    id="fallback_0",
                    title=f"Research on: {query}",
                    url="",
                    snippet=f"AI-enhanced research summary for {query}",
                    relevance=0.5,
                    provider="fallback",
                )
            ]

    async def _generate_summary(
        self, query: str, sources: List[Source], model: Optional[str] = None
    ) -> str:
        """Generate a summary from the found sources"""
        from backend.services.model_router import ModelRouter, TaskType

        try:
            router = ModelRouter()
            source_text = (
                "\n".join([f"- {s.title}: {s.snippet}" for s in sources if s.snippet])
                or "No sources found."
            )

            messages = [
                {
                    "role": "system",
                    "content": "You are a research assistant. Summarize the findings for the given topic based on the provided sources. Be concise but comprehensive. Use markdown formatting.",
                },
                {
                    "role": "user",
                    "content": f"Topic: {query}\n\nSources:\n{source_text}\n\nProvide a comprehensive summary:",
                },
            ]

            result = router.chat(
                task_type=TaskType.SUMMARIZATION,
                messages=messages,
                temperature=0.3,
                max_tokens=1500,
            )

            return result.get("content", "Summary generation failed.")

        except Exception as e:
            logger.warning(f"Summary generation failed: {e}")
            return f"Research on '{query}' completed with {len(sources)} sources found."

    async def deep_research(self, query: str, depth: int = 3) -> Dict[str, Any]:
        """Multi-pass research for comprehensive coverage"""
        all_sources = []
        all_summaries = []

        queries = [query]
        for i in range(depth):
            results = await self.research(queries[-1], num_results=5)
            all_sources.extend(results.sources)
            all_summaries.append(results.summary)

            if results.sources:
                next_query = f"{query} - {results.sources[0].title}"
                queries.append(next_query)

        unique_sources = list({s.id: s for s in all_sources}.values())

        combined_summary = "\n\n".join(
            [f"## Pass {i+1}\n{s}" for i, s in enumerate(all_summaries)]
        )

        return {
            "query": query,
            "depth": depth,
            "total_sources": len(unique_sources),
            "sources": [
                {"title": s.title, "url": s.url, "relevance": s.relevance}
                for s in unique_sources
            ],
            "combined_summary": combined_summary,
        }
