"""Editor Agent - reviews and improves content"""

import time
import json
import logging
from typing import Dict, Any, Optional

from backend.agents.base import BaseAgent, AgentRole, AgentResult

logger = logging.getLogger(__name__)


class EditorAgent(BaseAgent):
    role = AgentRole.EDITOR
    name = "Editor Agent"
    description = "Reviews, edits, and improves content quality, grammar, and style"

    def get_system_prompt(self) -> str:
        return """You are a professional editor with expertise in content quality, grammar, style, and clarity.

Your editing covers:
1. Grammar and spelling corrections
2. Style and tone consistency
3. Structure and flow improvements
4. Clarity and conciseness
5. Fact-checking suggestions
6. Readability optimization
7. Brand voice alignment

Provide specific, actionable feedback with line-level suggestions.
Always return the corrected content alongside your feedback.
Respond in valid JSON format."""

    async def execute(
        self, task: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> AgentResult:
        start = time.time()

        content = task.get("content", "")
        edit_type = task.get("edit_type", "comprehensive")
        style_guide = task.get("style_guide", "")

        prompt = self._build_edit_prompt(content, edit_type, style_guide, context)
        messages = self._build_messages(prompt, context)

        try:
            response = self._call_model(
                messages=messages,
                task_type="editing",
                temperature=0.3,
                max_tokens=max(2000, len(content)),
            )

            edit_data = self._parse_json(response["content"])

            return self._create_result(
                success=True,
                data=edit_data,
                model_response=response,
                duration=time.time() - start,
            )

        except Exception as e:
            logger.error(f"Editor agent failed: {e}")
            return self._create_result(
                success=False, error=str(e), duration=time.time() - start
            )

    def _build_edit_prompt(
        self,
        content: str,
        edit_type: str,
        style_guide: str,
        context: Optional[Dict[str, Any]],
    ) -> str:
        brand_context = ""
        if context and "brand" in context:
            brand = context["brand"]
            brand_context = f"""
Brand Voice: {brand.get('voice_tone', 'professional')}
Target Audience: {brand.get('target_audience', 'general')}
"""

        prompt = f"""Review and edit this content ({edit_type} editing):

Content:
{content[:4000]}
{brand_context}
{f'Style Guide: {style_guide}' if style_guide else ''}

Provide your edit as JSON:
{{
    "edited_content": "The full corrected and improved content",
    "changes": [
        {{
            "type": "grammar|style|structure|clarity|fact",
            "original": "original text",
            "corrected": "corrected text",
            "reason": "explanation",
            "severity": "high|medium|low"
        }}
    ],
    "quality_score": 85,
    "readability_score": 78,
    "summary": "Brief summary of changes made",
    "strengths": ["strength 1", "strength 2"],
    "improvement_areas": ["area 1", "area 2"]
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
                "edited_content": content,
                "changes": [],
                "quality_score": 70,
                "summary": "Content returned unprocessed",
            }
