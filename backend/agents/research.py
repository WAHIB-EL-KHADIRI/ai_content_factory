"""Research Agent - gathers and analyzes information"""

import time
import json
import logging
from typing import Dict, Any, Optional

from backend.agents.base import BaseAgent, AgentRole, AgentResult

logger = logging.getLogger(__name__)


class ResearchAgent(BaseAgent):
    role = AgentRole.RESEARCH
    name = "Research Agent"
    description = "Gathers information, analyzes topics, and provides research summaries with sources"

    def get_system_prompt(self) -> str:
        return """You are an expert research analyst. Your job is to:
1. Analyze topics thoroughly and provide comprehensive research
2. Identify key facts, statistics, trends, and insights
3. Suggest credible sources and references
4. Identify target audiences and their interests
5. Analyze competitor content when relevant
6. Provide structured research briefs

Always provide:
- Executive summary (2-3 sentences)
- Key findings (bullet points)
- Target audience insights
- Content angle recommendations
- Suggested keywords and topics
- Source suggestions

Respond in valid JSON format."""

    async def execute(self, task: Dict[str, Any],
                      context: Optional[Dict[str, Any]] = None) -> AgentResult:
        start = time.time()

        topic = task.get("topic", "")
        research_type = task.get("research_type", "general")
        depth = task.get("depth", "standard")

        prompt = self._build_research_prompt(topic, research_type, depth, context)
        messages = self._build_messages(prompt, context)

        try:
            response = self._call_model(
                messages=messages,
                task_type="content_writing",
                temperature=0.7,
                max_tokens=2000,
            )

            research_data = self._parse_response(response["content"])

            return self._create_result(
                success=True,
                data=research_data,
                model_response=response,
                duration=time.time() - start,
            )

        except Exception as e:
            logger.error(f"Research agent failed: {e}")
            return self._create_result(
                success=False,
                error=str(e),
                duration=time.time() - start,
            )

    def _build_research_prompt(self, topic: str, research_type: str,
                               depth: str, context: Optional[Dict[str, Any]]) -> str:
        depth_instruction = {
            "quick": "Provide a brief overview with 3-5 key points.",
            "standard": "Provide comprehensive research with detailed analysis.",
            "deep": "Provide exhaustive research with deep analysis, multiple angles, and detailed insights."
        }.get(depth, "Provide comprehensive research with detailed analysis.")

        type_instruction = {
            "general": "Research this topic broadly.",
            "competitor": "Analyze competitor content and identify gaps.",
            "trending": "Identify trending aspects and viral potential.",
            "academic": "Focus on research-backed facts and statistics.",
        }.get(research_type, "Research this topic broadly.")

        prompt = f"""Research Topic: {topic}

Research Type: {research_type}
{type_instruction}

Depth: {depth}
{depth_instruction}

Provide your research as a JSON object with these fields:
{{
    "executive_summary": "2-3 sentence overview",
    "key_findings": ["finding 1", "finding 2", ...],
    "statistics": [{{"fact": "...", "source": "..."}}],
    "target_audience": {{
        "primary": "description",
        "interests": ["interest 1", "interest 2"],
        "pain_points": ["pain 1", "pain 2"]
    }},
    "content_angles": ["angle 1", "angle 2", ...],
    "keywords": ["keyword 1", "keyword 2", ...],
    "competitor_gaps": ["gap 1", "gap 2", ...],
    "sources": ["source 1", "source 2", ...]
}}"""

        if context:
            existing_content = context.get("existing_content", "")
            if existing_content:
                prompt += f"\n\nExisting content to build upon:\n{existing_content[:1000]}"

        return prompt

    def _parse_response(self, content: str) -> Dict[str, Any]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                return json.loads(content[start:end].strip())
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                return json.loads(content[start:end].strip())

            return {
                "executive_summary": content[:500],
                "key_findings": [],
                "content_angles": [],
                "keywords": [],
                "raw_response": content,
            }
