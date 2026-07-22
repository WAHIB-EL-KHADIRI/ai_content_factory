"""Writer Agent - creates content"""

import time
import json
import logging
from typing import Dict, Any, Optional

from backend.agents.base import BaseAgent, AgentRole, AgentResult

logger = logging.getLogger(__name__)


class WriterAgent(BaseAgent):
    role = AgentRole.WRITER
    name = "Writer Agent"
    description = "Creates high-quality content including articles, scripts, social posts, and more"

    def get_system_prompt(self) -> str:
        return """You are an expert content writer. You create engaging, well-structured, and SEO-optimized content.

Writing principles:
1. Hook readers with compelling openings
2. Use clear, concise language
3. Structure content with headers and subheadings
4. Include relevant examples and anecdotes
5. End with strong conclusions and CTAs
6. Maintain consistent brand voice
7. Optimize for readability and SEO

Content types you handle:
- Blog posts and articles
- Video scripts
- Social media posts
- Email content
- Product descriptions
- Landing pages
- Documentation

Always provide well-formatted content with proper structure. Respond in valid JSON."""

    async def execute(
        self, task: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> AgentResult:
        start = time.time()

        content_type = task.get("content_type", "article")
        topic = task.get("topic", "")
        instructions = task.get("instructions", "")
        word_count = task.get("word_count", 1000)
        tone = task.get("tone", "professional")
        format_type = task.get("format", "markdown")

        prompt = self._build_writing_prompt(
            content_type, topic, instructions, word_count, tone, format_type, context
        )
        messages = self._build_messages(prompt, context)

        try:
            response = self._call_model(
                messages=messages,
                task_type="content_writing",
                temperature=0.75,
                max_tokens=min(4000, max(1000, word_count * 2)),
            )

            content_data = self._parse_response(response["content"], content_type)

            return self._create_result(
                success=True,
                data=content_data,
                model_response=response,
                duration=time.time() - start,
            )

        except Exception as e:
            logger.error(f"Writer agent failed: {e}")
            return self._create_result(
                success=False,
                error=str(e),
                duration=time.time() - start,
            )

    def _build_writing_prompt(
        self,
        content_type: str,
        topic: str,
        instructions: str,
        word_count: int,
        tone: str,
        format_type: str,
        context: Optional[Dict[str, Any]],
    ) -> str:
        research_data = ""
        brand_guidelines = ""

        if context:
            if "research" in context:
                research_data = json.dumps(context["research"], indent=2)[:2000]
            if "brand" in context:
                brand = context["brand"]
                brand_guidelines = f"""
Brand Voice: {brand.get('voice_tone', 'professional')}
Target Audience: {brand.get('target_audience', 'general')}
Keywords: {', '.join(brand.get('keywords', []))}
"""

        prompt = f"""Write a {content_type} about: {topic}

Requirements:
- Content Type: {content_type}
- Target Word Count: ~{word_count} words
- Tone: {tone}
- Format: {format_type}
{instructions}

{brand_guidelines}

{f'Research Data:{chr(10)}{research_data}' if research_data else ''}

Respond as JSON with:
{{
    "title": "Content title",
    "content": "The full content text",
    "summary": "2-3 sentence summary",
    "key_points": ["point 1", "point 2"],
    "suggested_tags": ["tag1", "tag2"],
    "seo_title": "SEO-optimized title (max 60 chars)",
    "meta_description": "SEO meta description (max 160 chars)"
}}"""

        return prompt

    def _parse_response(self, content: str, content_type: str) -> Dict[str, Any]:
        try:
            data = json.loads(content)
            if "content" not in data and "body" not in data:
                data["content"] = content
            return data
        except json.JSONDecodeError:
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                try:
                    return json.loads(content[start:end].strip())
                except json.JSONDecodeError:
                    pass

            return {
                "title": "Untitled",
                "content": content,
                "summary": content[:300],
                "key_points": [],
                "suggested_tags": [],
            }
