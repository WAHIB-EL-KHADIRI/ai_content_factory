"""Publisher Agent - handles content publishing"""

import time
import json
import logging
from typing import Dict, Any, Optional

from backend.agents.base import BaseAgent, AgentRole, AgentResult

logger = logging.getLogger(__name__)


class PublisherAgent(BaseAgent):
    role = AgentRole.PUBLISHER
    name = "Publisher Agent"
    description = "Handles content publishing, formatting, and distribution"

    def get_system_prompt(self) -> str:
        return """You are an expert content publisher and distribution specialist.

Your capabilities:
1. Format content for different platforms
2. Optimize publishing schedules
3. Create platform-specific versions
4. Generate social media copy
5. Plan content distribution
6. Track publishing metrics

Respond in valid JSON format."""

    async def execute(
        self, task: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> AgentResult:
        start = time.time()

        action = task.get("action", "format")
        content = task.get("content", "")
        platforms = task.get("platforms", ["blog"])

        if action == "format":
            result = await self._format_content(content, platforms, context)
        elif action == "schedule":
            result = await self._suggest_schedule(content, context)
        elif action == "distribute":
            result = await self._create_distribution_plan(content, platforms, context)
        else:
            result = await self._format_content(content, platforms, context)

        result.duration_seconds = time.time() - start
        return result

    async def _format_content(
        self, content: str, platforms: list, context: Optional[Dict[str, Any]]
    ) -> AgentResult:
        prompt = f"""Format this content for multiple platforms:

Content:
{content[:3000]}

Target Platforms: {', '.join(platforms)}

Provide formatted versions as JSON:
{{
    "versions": {{
        "blog": {{
            "title": "...",
            "body": "Full blog post in markdown",
            "excerpt": "...",
            "tags": ["tag1", "tag2"]
        }},
        "twitter": {{
            "thread": ["tweet 1", "tweet 2"],
            "hashtags": ["#tag1"]
        }},
        "linkedin": {{
            "post": "...",
            "hashtags": ["#tag1"]
        }},
        "instagram": {{
            "caption": "...",
            "hashtags": ["#tag1"],
            "story_text": "..."
        }},
        "email": {{
            "subject": "...",
            "preview": "...",
            "body": "..."
        }}
    }},
    "publishing_order": ["platform1", "platform2"],
    "timing_notes": "..."
}}"""

        messages = self._build_messages(prompt, context)

        try:
            response = self._call_model(
                messages=messages,
                task_type="content_writing",
                temperature=0.5,
                max_tokens=3000,
            )

            formatted = self._parse_json(response["content"])

            return self._create_result(
                success=True,
                data=formatted,
                model_response=response,
            )

        except Exception as e:
            logger.error(f"Publisher format failed: {e}")
            return self._create_result(success=False, error=str(e))

    async def _suggest_schedule(
        self, content: str, context: Optional[Dict[str, Any]]
    ) -> AgentResult:
        prompt = f"""Suggest an optimal publishing schedule for this content:

Content: {content[:500]}

Provide schedule as JSON:
{{
    "recommended_date": "YYYY-MM-DD",
    "recommended_time": "HH:MM",
    "timezone": "UTC",
    "reasoning": "...",
    "platform_schedules": {{
        "platform": {{"date": "...", "time": "...", "reasoning": "..."}}
    }}
}}"""

        messages = self._build_messages(prompt, context)

        try:
            response = self._call_model(
                messages=messages,
                task_type="content_writing",
                temperature=0.3,
                max_tokens=1000,
            )

            schedule = self._parse_json(response["content"])

            return self._create_result(
                success=True,
                data=schedule,
                model_response=response,
            )

        except Exception as e:
            return self._create_result(success=False, error=str(e))

    async def _create_distribution_plan(
        self, content: str, platforms: list, context: Optional[Dict[str, Any]]
    ) -> AgentResult:
        prompt = f"""Create a content distribution plan:

Content: {content[:500]}
Platforms: {', '.join(platforms)}

Provide plan as JSON:
{{
    "distribution_plan": [
        {{
            "platform": "...",
            "format": "...",
            "timing": "...",
            "cta": "...",
            "metrics_to_track": ["metric1"]
        }}
    ],
    "total_estimated_reach": "...",
    "budget_recommendation": "..."
}}"""

        messages = self._build_messages(prompt, context)

        try:
            response = self._call_model(
                messages=messages,
                task_type="content_writing",
                temperature=0.5,
                max_tokens=2000,
            )

            plan = self._parse_json(response["content"])

            return self._create_result(
                success=True,
                data=plan,
                model_response=response,
            )

        except Exception as e:
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
