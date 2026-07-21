"""SEO Agent - optimizes content for search engines"""

import time
import json
import logging
from typing import Dict, Any, Optional

from backend.agents.base import BaseAgent, AgentRole, AgentResult

logger = logging.getLogger(__name__)


class SEOAgent(BaseAgent):
    role = AgentRole.SEO
    name = "SEO Agent"
    description = "Analyzes and optimizes content for search engine visibility"

    def get_system_prompt(self) -> str:
        return """You are an expert SEO specialist. You analyze content and provide actionable optimization recommendations.

Your expertise covers:
1. Keyword research and optimization
2. On-page SEO (title tags, meta descriptions, headers, URLs)
3. Content structure and readability
4. Internal and external linking strategies
5. Technical SEO considerations
6. Content gap analysis
7. SERP feature optimization

Always provide specific, actionable recommendations with priority levels.
Respond in valid JSON format."""

    async def execute(self, task: Dict[str, Any],
                      context: Optional[Dict[str, Any]] = None) -> AgentResult:
        start = time.time()

        action = task.get("action", "analyze")
        content = task.get("content", "")
        target_keywords = task.get("keywords", [])

        if action == "analyze":
            result = await self._analyze_content(content, target_keywords, context)
        elif action == "optimize":
            result = await self._optimize_content(content, target_keywords, context)
        elif action == "keywords":
            result = await self._research_keywords(task.get("topic", ""), context)
        else:
            result = await self._analyze_content(content, target_keywords, context)

        result.duration_seconds = time.time() - start
        return result

    async def _analyze_content(self, content: str, keywords: list,
                               context: Optional[Dict[str, Any]]) -> AgentResult:
        prompt = f"""Analyze this content for SEO optimization:

Content:
{content[:3000]}

Target Keywords: {', '.join(keywords) if keywords else 'Not specified'}

Provide a comprehensive SEO analysis as JSON:
{{
    "score": 75,
    "title": {{
        "current": "...",
        "recommended": "...",
        "issues": ["issue 1"]
    }},
    "meta_description": {{
        "current": "...",
        "recommended": "...",
        "issues": ["issue 1"]
    }},
    "headings": {{
        "structure": "h1, h2, h3...",
        "issues": ["issue 1"],
        "recommendations": ["rec 1"]
    }},
    "keywords": {{
        "primary": "keyword",
        "secondary": ["kw1", "kw2"],
        "density": {{"keyword": 2.5}},
        "recommendations": ["rec 1"]
    }},
    "content_quality": {{
        "readability_score": 70,
        "word_count": 1000,
        "avg_sentence_length": 15,
        "issues": ["issue 1"]
    }},
    "technical": {{
        "issues": ["issue 1"],
        "recommendations": ["rec 1"]
    }},
    "quick_wins": ["win 1", "win 2"],
    "priority_actions": [
        {{"action": "...", "priority": "high", "impact": "..."}}
    ]
}}"""

        messages = self._build_messages(prompt, context)

        try:
            response = self._call_model(
                messages=messages,
                task_type="seo_analysis",
                temperature=0.3,
                max_tokens=3000,
            )

            analysis = self._parse_json(response["content"])

            return self._create_result(
                success=True,
                data=analysis,
                model_response=response,
            )

        except Exception as e:
            logger.error(f"SEO analysis failed: {e}")
            return self._create_result(success=False, error=str(e))

    async def _optimize_content(self, content: str, keywords: list,
                                context: Optional[Dict[str, Any]]) -> AgentResult:
        prompt = f"""Optimize this content for SEO:

Original Content:
{content[:3000]}

Target Keywords: {', '.join(keywords) if keywords else 'Not specified'}

Provide the optimized content as JSON:
{{
    "optimized_title": "...",
    "optimized_meta_description": "...",
    "optimized_content": "The full optimized content...",
    "changes_made": ["change 1", "change 2"],
    "keyword_insertions": [{{"keyword": "...", "location": "...", "context": "..."}}],
    "structural_improvements": ["improvement 1"]
}}"""

        messages = self._build_messages(prompt, context)

        try:
            response = self._call_model(
                messages=messages,
                task_type="seo_analysis",
                temperature=0.5,
                max_tokens=4000,
            )

            optimized = self._parse_json(response["content"])

            return self._create_result(
                success=True,
                data=optimized,
                model_response=response,
            )

        except Exception as e:
            logger.error(f"SEO optimization failed: {e}")
            return self._create_result(success=False, error=str(e))

    async def _research_keywords(self, topic: str,
                                 context: Optional[Dict[str, Any]]) -> AgentResult:
        prompt = f"""Research keywords for the topic: {topic}

Provide keyword research as JSON:
{{
    "primary_keywords": [
        {{"keyword": "...", "difficulty": "medium", "search_volume": "high", "relevance": 9}}
    ],
    "long_tail_keywords": ["keyword 1", "keyword 2"],
    "related_topics": ["topic 1", "topic 2"],
    "question_keywords": ["question 1", "question 2"],
    "content_gaps": ["gap 1", "gap 2"],
    "recommended_strategy": "..."
}}"""

        messages = self._build_messages(prompt, context)

        try:
            response = self._call_model(
                messages=messages,
                task_type="seo_analysis",
                temperature=0.5,
                max_tokens=2000,
            )

            keywords_data = self._parse_json(response["content"])

            return self._create_result(
                success=True,
                data=keywords_data,
                model_response=response,
            )

        except Exception as e:
            logger.error(f"Keyword research failed: {e}")
            return self._create_result(success=False, error=str(e))

    def _parse_json(self, content: str) -> Dict[str, Any]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                try:
                    return json.loads(content[start:end].strip())
                except json.JSONDecodeError:
                    pass
            return {"raw_response": content}
