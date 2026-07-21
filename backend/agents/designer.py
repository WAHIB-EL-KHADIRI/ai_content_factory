"""Designer Agent - generates visual content"""

import time
import json
import logging
from typing import Dict, Any, Optional

from backend.agents.base import BaseAgent, AgentRole, AgentResult

logger = logging.getLogger(__name__)


class DesignerAgent(BaseAgent):
    role = AgentRole.DESIGNER
    name = "Designer Agent"
    description = "Creates visual content, generates image prompts, and manages design assets"

    def get_system_prompt(self) -> str:
        return """You are an expert visual designer and AI image prompt engineer.

Your capabilities:
1. Create detailed image prompts for AI generators (DALL-E, Midjourney, Stable Diffusion)
2. Design content layouts and visual hierarchies
3. Suggest color palettes and typography
4. Create social media visual specifications
5. Design infographics and data visualizations
6. Generate thumbnail concepts

When creating prompts, include:
- Subject and composition
- Style and mood
- Lighting and color
- Technical parameters
- Quality modifiers

Respond in valid JSON format."""

    async def execute(self, task: Dict[str, Any],
                      context: Optional[Dict[str, Any]] = None) -> AgentResult:
        start = time.time()

        design_type = task.get("design_type", "image_prompt")
        content = task.get("content", "")
        style = task.get("style", "cinematic")
        dimensions = task.get("dimensions", "1920x1080")

        prompt = self._build_design_prompt(design_type, content, style, dimensions, context)
        messages = self._build_messages(prompt, context)

        try:
            response = self._call_model(
                messages=messages,
                task_type="content_writing",
                temperature=0.8,
                max_tokens=2000,
            )

            design_data = self._parse_json(response["content"])

            return self._create_result(
                success=True,
                data=design_data,
                model_response=response,
                duration=time.time() - start,
            )

        except Exception as e:
            logger.error(f"Designer agent failed: {e}")
            return self._create_result(
                success=False, error=str(e), duration=time.time() - start
            )

    def _build_design_prompt(self, design_type: str, content: str,
                             style: str, dimensions: str,
                             context: Optional[Dict[str, Any]]) -> str:
        brand_context = ""
        if context and "brand" in context:
            brand = context["brand"]
            colors = brand.get("color_palette", [])
            brand_context = f"Brand Colors: {', '.join(colors)}" if colors else ""

        if design_type == "image_prompt":
            prompt = f"""Create an AI image generation prompt for this content:

Content Summary: {content[:1000]}
Style: {style}
Dimensions: {dimensions}
{brand_context}

Provide as JSON:
{{
    "image_prompts": [
        {{
            "purpose": "hero_image|social|thumbnail|infographic",
            "prompt": "Detailed prompt for AI image generation",
            "negative_prompt": "What to avoid",
            "recommended_model": "dall-e-3|stable-diffusion|midjourney",
            "parameters": {{"aspect_ratio": "16:9", "style": "..."}}
        }}
    ],
    "color_suggestions": ["#hex1", "#hex2"],
    "layout_concepts": ["concept 1", "concept 2"]
}}"""
        elif design_type == "social_media":
            prompt = f"""Create social media visual specifications:

Content: {content[:1000]}
Platforms: Instagram, Twitter, LinkedIn
Style: {style}
{brand_context}

Provide as JSON:
{{
    "platforms": {{
        "instagram": {{
            "post": {{"dimensions": "1080x1080", "prompt": "..."}},
            "story": {{"dimensions": "1080x1920", "prompt": "..."}},
            "carousel_slides": [{{"slide": 1, "prompt": "..."}}]
        }},
        "twitter": {{
            "post": {{"dimensions": "1200x675", "prompt": "..."}}
        }},
        "linkedin": {{
            "post": {{"dimensions": "1200x627", "prompt": "..."}}
        }}
    }}
}}"""
        else:
            prompt = f"""Design visual content:

Content: {content[:1000]}
Type: {design_type}
Style: {style}
{brand_context}

Provide your design specifications as JSON."""

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
            return {"raw_response": content}
