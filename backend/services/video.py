"""Video Generation Service - integrates existing src/ pipeline with backend"""

import logging
import asyncio
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class VideoService:
    """Wraps the existing VideoGenerationPipeline for backend API use"""

    def __init__(self):
        self.config_path = "config/config.yaml"

    def _get_pipeline(self):
        from src.main import VideoGenerationPipeline
        return VideoGenerationPipeline(config_path=self.config_path)

    async def generate_video(self, topic: str, output_filename: Optional[str] = None,
                             mock: bool = False) -> Dict[str, Any]:
        """Generate a video from a topic (runs pipeline in thread to avoid blocking)"""
        loop = asyncio.get_event_loop()
        try:
            pipeline = self._get_pipeline()
            video_path = await loop.run_in_executor(
                None,
                lambda: pipeline.generate_video(
                    topic=topic,
                    output_filename=output_filename,
                    mock=mock,
                )
            )
            return {
                "status": "completed",
                "video_path": str(video_path),
                "topic": topic,
                "mock": mock,
            }
        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "topic": topic,
            }

    async def generate_script_only(self, topic: str, mock: bool = True) -> Dict[str, Any]:
        """Generate only the script (no voiceover/visuals/assembly)"""
        try:
            from src.generators import ScriptGenerator
            from src.utils import load_config

            config = load_config(self.config_path)
            generator = ScriptGenerator(config)
            script = generator.generate(topic, mock=mock)
            return {
                "status": "completed",
                "script": script,
                "topic": topic,
            }
        except Exception as e:
            logger.error(f"Script generation failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "topic": topic,
            }

    async def validate_config(self) -> Dict[str, Any]:
        """Validate that the video pipeline is properly configured"""
        try:
            pipeline = self._get_pipeline()
            is_valid = pipeline.validate_configuration()
            return {
                "valid": is_valid,
                "config_path": self.config_path,
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
            }

    def get_pipeline_info(self) -> Dict[str, Any]:
        """Get information about the video pipeline"""
        return {
            "name": "Video Generation Pipeline",
            "version": "1.0.0",
            "steps": ["Script Generation", "Voiceover Generation", "Visual Generation", "Video Assembly"],
            "providers": {
                "script": "DeepSeek",
                "voiceover": "ElevenLabs / Coqui TTS",
                "visual": "DALL-E / Stable Diffusion",
                "assembly": "MoviePy",
            },
        }
