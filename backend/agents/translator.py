"""Translator Agent - translates content between languages"""

import time
import json
import logging
from typing import Dict, Any, Optional

from backend.agents.base import BaseAgent, AgentRole, AgentResult

logger = logging.getLogger(__name__)


class TranslatorAgent(BaseAgent):
    role = AgentRole.TRANSLATOR
    name = "Translator Agent"
    description = "Translates content between languages while preserving tone and context"

    def get_system_prompt(self) -> str:
        return """You are an expert translator and localization specialist.

Your translation approach:
1. Preserve meaning and intent, not just words
2. Adapt cultural references appropriately
3. Maintain brand voice and tone
4. Use natural, fluent language in the target language
5. Consider local customs and sensitivities
6. Maintain formatting and structure
7. Preserve SEO keywords when possible

Supported languages: English, Arabic, Spanish, French, German, Portuguese, Chinese, Japanese, Korean, and more.

Always provide accurate, natural translations. Respond in valid JSON format."""

    async def execute(self, task: Dict[str, Any],
                      context: Optional[Dict[str, Any]] = None) -> AgentResult:
        start = time.time()

        content = task.get("content", "")
        source_lang = task.get("source_language", "auto")
        target_lang = task.get("target_language", "en")
        content_type = task.get("content_type", "general")

        prompt = f"""Translate the following content from {source_lang} to {target_lang}:

Content:
{content[:4000]}

Content Type: {content_type}

Provide translation as JSON:
{{
    "translated_content": "The translated text",
    "source_language": "detected source language",
    "target_language": "{target_lang}",
    "confidence_score": 95,
    "notes": ["any localization notes"],
    "alternative_translations": [
        {{"context": "...", "alternative": "..."}}
    ]
}}"""

        messages = self._build_messages(prompt, context)

        try:
            response = self._call_model(
                messages=messages,
                task_type="translation",
                temperature=0.3,
                max_tokens=max(2000, len(content) * 2),
            )

            translation = self._parse_json(response["content"])

            return self._create_result(
                success=True,
                data=translation,
                model_response=response,
                duration=time.time() - start,
            )

        except Exception as e:
            logger.error(f"Translator agent failed: {e}")
            return self._create_result(
                success=False, error=str(e), duration=time.time() - start
            )

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
                "translated_content": content,
                "confidence_score": 80,
                "notes": [],
            }
