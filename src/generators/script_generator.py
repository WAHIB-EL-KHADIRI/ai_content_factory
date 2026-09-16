"""
Script Generator using DeepSeek API
"""

import json
import logging
from typing import Dict, Any
from openai import OpenAI

from config.prompts import get_script_prompt
from src.utils.utils import retry_with_backoff, scrub_for_log


logger = logging.getLogger("VideoGenerator.ScriptGenerator")


class ScriptGenerator:
    """Generate video scripts using DeepSeek API"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the script generator

        Args:
            config: Configuration dictionary
        """
        self.config = config
        deepseek_config = config.get("deepseek", {})

        self.client = OpenAI(
            api_key=deepseek_config.get("api_key"),
            base_url=deepseek_config.get("base_url", "https://api.deepseek.com/v1"),
        )

        self.model = deepseek_config.get("model", "deepseek-chat")
        self.max_tokens = deepseek_config.get("max_tokens", 2000)
        self.script_config = config.get("script", {})

        logger.info("ScriptGenerator initialized")

    def generate(self, topic: str, mock: bool = False) -> Dict[str, Any]:
        """
        Generate a video script for the given topic

        Args:
            topic: Video topic
            mock: If True, return a sample script without API call

        Returns:
            Dictionary containing script data with title and scenes
        """
        if mock:
            logger.info("Using mock script generation")
            return {
                "title": f"Mock Video: {topic}",
                "scenes": [
                    {
                        "id": 1,
                        "narration": f"Welcome to our video about {topic}. This is the first scene.",
                        "visual_prompt": f"A cinematic wide shot representing {topic}, high quality.",
                        "duration": 5.0,
                    },
                    {
                        "id": 2,
                        "narration": "In the second scene, we explore more details about this fascinating subject.",
                        "visual_prompt": "A detailed close up of relevant textures, soft lighting.",
                        "duration": 6.0,
                    },
                    {
                        "id": 3,
                        "narration": "Finally, we conclude our brief overview. Thank you for watching!",
                        "visual_prompt": "A beautiful sunset or abstract ending visual, cinematic.",
                        "duration": 5.0,
                    },
                ],
            }

        logger.info("Generating script for topic: %s", scrub_for_log(topic))

        prompt = get_script_prompt(topic, self.script_config)

        def api_call():
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional video script writer. Always respond with valid JSON only.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=self.max_tokens,
                temperature=0.7,
            )
            return response.choices[0].message.content

        try:
            # Call API with retry logic
            response_text = retry_with_backoff(api_call)

            # Parse JSON response
            script_data = self._parse_response(response_text)

            logger.info(
                f"Script generated successfully with {len(script_data.get('scenes', []))} scenes"
            )
            return script_data

        except Exception as e:
            logger.error(f"Error generating script: {e}")
            raise

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse the API response and validate structure

        Args:
            response_text: Raw API response

        Returns:
            Validated script dictionary
        """
        try:
            # Try to parse JSON directly
            script_data = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
                script_data = json.loads(json_str)
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
                script_data = json.loads(json_str)
            else:
                raise ValueError("Could not parse JSON from response")

        # Validate structure
        if not isinstance(script_data, dict):
            raise ValueError("Response is not a JSON object")

        if "scenes" not in script_data:
            raise ValueError("Response missing 'scenes' field")

        if not isinstance(script_data["scenes"], list):
            raise ValueError("'scenes' is not a list")

        # Validate each scene
        for i, scene in enumerate(script_data["scenes"]):
            if not isinstance(scene, dict):
                raise ValueError(f"Scene {i} is not a dictionary")

            required_fields = ["narration", "visual_prompt", "duration"]
            for field in required_fields:
                if field not in scene:
                    raise ValueError(f"Scene {i} missing required field: {field}")

            # Add ID if missing
            if "id" not in scene:
                scene["id"] = i + 1

        logger.debug(f"Validated script: {script_data.get('title', 'Untitled')}")
        return script_data

    def enhance_visual_prompt(self, visual_prompt: str) -> str:
        """
        Enhance a visual prompt for better image generation

        Args:
            visual_prompt: Original visual prompt

        Returns:
            Enhanced visual prompt
        """
        from config.prompts import get_visual_enhancement_prompt

        prompt = get_visual_enhancement_prompt(visual_prompt)

        def api_call():
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()

        try:
            enhanced = retry_with_backoff(api_call)
            logger.debug(f"Enhanced visual prompt: {enhanced[:100]}...")
            return enhanced
        except Exception as e:
            logger.warning(f"Failed to enhance visual prompt: {e}. Using original.")
            return visual_prompt
