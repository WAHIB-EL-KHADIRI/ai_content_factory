"""Review Agent - quality assurance and compliance checking"""

import time
import json
import logging
from typing import Dict, Any, Optional

from backend.agents.base import BaseAgent, AgentRole, AgentResult

logger = logging.getLogger(__name__)


class ReviewAgent(BaseAgent):
    role = AgentRole.REVIEWER
    name = "Review Agent"
    description = "Performs quality assurance, compliance checks, and final reviews"

    def get_system_prompt(self) -> str:
        return """You are a senior content reviewer and quality assurance specialist.

Your review covers:
1. Content accuracy and factuality
2. Grammar, spelling, and punctuation
3. Brand voice compliance
4. Legal and compliance issues
5. SEO optimization quality
6. Readability and engagement
7. Plagiarism indicators
8. Accessibility considerations

Provide a thorough, objective review with actionable feedback.
Rate content on multiple dimensions.
Respond in valid JSON format."""

    async def execute(self, task: Dict[str, Any],
                      context: Optional[Dict[str, Any]] = None) -> AgentResult:
        start = time.time()

        content = task.get("content", "")
        review_type = task.get("review_type", "comprehensive")
        criteria = task.get("criteria", [])

        prompt = self._build_review_prompt(content, review_type, criteria, context)
        messages = self._build_messages(prompt, context)

        try:
            response = self._call_model(
                messages=messages,
                task_type="editing",
                temperature=0.2,
                max_tokens=2000,
            )

            review_data = self._parse_json(response["content"])

            return self._create_result(
                success=True,
                data=review_data,
                model_response=response,
                duration=time.time() - start,
            )

        except Exception as e:
            logger.error(f"Review agent failed: {e}")
            return self._create_result(
                success=False, error=str(e), duration=time.time() - start
            )

    def _build_review_prompt(self, content: str, review_type: str,
                             criteria: list, context: Optional[Dict[str, Any]]) -> str:
        criteria_text = ""
        if criteria:
            criteria_text = f"Specific Criteria: {', '.join(criteria)}"

        brand_context = ""
        if context and "brand" in context:
            brand = context["brand"]
            brand_context = f"Brand Voice: {brand.get('voice_tone', 'professional')}"

        prompt = f"""Perform a {review_type} review of this content:

Content:
{content[:4000]}

{criteria_text}
{brand_context}

Provide your review as JSON:
{{
    "overall_score": 85,
    "scores": {{
        "accuracy": 90,
        "grammar": 95,
        "brand_compliance": 80,
        "seo_quality": 75,
        "readability": 85,
        "engagement": 80
    }},
    "status": "approved|needs_revision|rejected",
    "issues": [
        {{
            "type": "accuracy|grammar|brand|seo|legal|accessibility",
            "severity": "critical|major|minor",
            "description": "...",
            "location": "line/section reference",
            "suggestion": "..."
        }}
    ],
    "strengths": ["strength 1", "strength 2"],
    "improvement_areas": ["area 1", "area 2"],
    "summary": "Overall review summary",
    "actionable_recommendations": [
        {{
            "priority": 1,
            "action": "...",
            "reason": "..."
        }}
    ]
}}"""

        return prompt

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
            return {
                "overall_score": 70,
                "status": "needs_revision",
                "issues": [],
                "summary": content[:500],
            }
