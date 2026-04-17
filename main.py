"""
AI Video Generation System - Main Orchestrator

This script coordinates all components to generate videos from topics.
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, Any
from tqdm import tqdm

from modules import (
    load_config,
    setup_logging,
    ensure_directories,
    ScriptGenerator,
    VoiceoverGenerator,
    VisualGenerator,
    VideoAssembler
)


class VideoGenerationPipeline:
    """Main pipeline for video generation"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the pipeline
        
        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config = load_config(config_path)
        
        # Setup logging
        self.logger = setup_logging(self.config)
        
        # Ensure directories exist
        ensure_directories(self.config)
        
        # Initialize components
        self.logger.info("Initializing components...")
        self.script_generator = ScriptGenerator(self.config)
        self.voiceover_generator = VoiceoverGenerator(self.config)
        self.visual_generator = VisualGenerator(self.config)
        self.video_assembler = VideoAssembler(self.config)
        
        self.logger.info("Pipeline initialized successfully")
    
    def generate_video(self, topic: str, output_filename: str = None, mock: bool = False) -> str:
        """
        Generate a complete video from a topic
        
        Args:
            topic: Video topic
            output_filename: Optional output filename
            mock: If True, run in mock mode without calling APIs
            
        Returns:
            Path to generated video
        """
        self.logger.info(f"Starting video generation for topic: {topic} {'(MOCK MODE)' if mock else ''}")
        
        try:
            # Step 1: Generate script
            self.logger.info("Step 1/4: Generating script...")
            script = self.script_generator.generate(topic, mock=mock)
            
            title = script.get('title', topic)
            scenes = script.get('scenes', [])
            
            self.logger.info(f"Script generated: {title}")
            self.logger.info(f"Number of scenes: {len(scenes)}")
            
            # Step 2: Generate voiceovers and visuals in parallel
            self.logger.info("Step 2/4: Generating voiceovers...")
            self._generate_voiceovers(scenes, mock=mock)
            
            self.logger.info("Step 3/4: Generating visuals...")
            self._generate_visuals(scenes, mock=mock)
            
            # Optional: If mock mode, we need real files for MoviePy to not crash
            if mock:
                self._ensure_mock_assets()

            # Step 4: Assemble video
            self.logger.info("Step 4/4: Assembling video...")
            
            if output_filename is None:
                # Generate filename from title
                from modules.utils import sanitize_filename
                safe_title = sanitize_filename(title.lower().replace(' ', '_'))
                output_filename = f"{safe_title}.mp4"
            
            video_path = self.video_assembler.assemble(
                scenes=scenes,
                output_filename=output_filename,
                title=title
            )
            
            self.logger.info(f"Video generation complete: {video_path}")
            return video_path
            
        except Exception as e:
            self.logger.error(f"Error during video generation: {e}", exc_info=True)
            raise
    
    def _ensure_mock_assets(self):
        """Create real dummy files for mock mode so MoviePy can process them"""
        from PIL import Image
        import numpy as np
        
        # Create a dummy image if it doesn't exist
        mock_image = "mock_image.png"
        if not Path(mock_image).exists():
            img = Image.fromarray(np.zeros((1080, 1920, 3), dtype=np.uint8))
            img.save(mock_image)
            self.logger.info("Created mock_image.png")
            
        # Create a dummy audio (1 second silence) if it doesn't exist
        # This requires pydub or just a small valid mp3
        mock_audio = "mock_audio.mp3"
        if not Path(mock_audio).exists():
            # We'll just copy a small valid file or wait for the user to provide one
            # For now, let's assume the user might have something or we'll skip audio in mock
            pass

    def _generate_voiceovers(self, scenes: list, mock: bool = False):
        """Generate voiceovers for all scenes"""
        for scene in tqdm(scenes, desc="Generating voiceovers"):
            narration = scene.get('narration', '')
            
            if not narration:
                self.logger.warning(f"Scene {scene.get('id')} has no narration")
                continue
            
            try:
                audio_path, duration = self.voiceover_generator.generate_audio(narration, mock=mock)
                scene['audio_path'] = audio_path if (not mock or Path(audio_path).exists()) else None
                scene['duration'] = duration
                
            except Exception as e:
                self.logger.error(f"Failed to generate voiceover for scene {scene.get('id')}: {e}")
                # Use estimated duration if audio generation fails
                scene['audio_path'] = None
                scene['duration'] = scene.get('duration', 5.0)
    
    def _generate_visuals(self, scenes: list, mock: bool = False):
        """Generate visuals for all scenes"""
        for scene in tqdm(scenes, desc="Generating visuals"):
            visual_prompt = scene.get('visual_prompt', '')
            
            if not visual_prompt:
                self.logger.warning(f"Scene {scene.get('id')} has no visual prompt")
                continue
            
            try:
                # Enhance prompt
                enhanced_prompt = visual_prompt if mock else self.visual_generator.enhance_for_video(visual_prompt)
                
                # Generate image
                image_path = self.visual_generator.generate_image(enhanced_prompt, mock=mock)
                scene['image_path'] = image_path if (not mock or Path(image_path).exists()) else "mock_image.png"
                
            except Exception as e:
                self.logger.error(f"Failed to generate visual for scene {scene.get('id')}: {e}")
                scene['image_path'] = "mock_image.png" if mock else None
    
    def validate_configuration(self) -> bool:
        """
        Validate that all required API keys are configured
        
        Returns:
            True if configuration is valid
        """
        self.logger.info("Validating configuration...")
        
        errors = []
        
        # Check DeepSeek API key
        deepseek_key = self.config.get('deepseek', {}).get('api_key')
        if not deepseek_key or deepseek_key == 'YOUR_DEEPSEEK_API_KEY':
            errors.append("DeepSeek API key not configured")
        
        # Check TTS provider
        tts_provider = self.config.get('tts', {}).get('provider')
        if tts_provider != 'coqui':  # Coqui doesn't need API key
            tts_key = self.config.get('tts', {}).get(tts_provider, {}).get('api_key')
            if not tts_key or 'YOUR_' in tts_key:
                errors.append(f"{tts_provider} TTS API key not configured")
        
        # Check image generation provider
        img_provider = self.config.get('image_generation', {}).get('provider')
        if img_provider != 'local':  # Local doesn't need API key
            img_key = self.config.get('image_generation', {}).get(img_provider, {}).get('api_key')
            if not img_key or 'YOUR_' in img_key:
                errors.append(f"{img_provider} image generation API key not configured")
        
        if errors:
            self.logger.error("Configuration validation failed:")
            for error in errors:
                self.logger.error(f"  - {error}")
            return False
        
        self.logger.info("Configuration is valid")
        return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="AI Video Generation System - Generate videos from topics"
    )
    parser.add_argument(
        'topic',
        type=str,
        help='Topic for the video'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='Output filename (default: auto-generated from title)'
    )
    parser.add_argument(
        '--config', '-c',
        type=str,
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate configuration and exit'
    )
    parser.add_argument(
        '--mock',
        action='store_true',
        help='Run in mock mode without calling real APIs'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize pipeline
        pipeline = VideoGenerationPipeline(config_path=args.config)
        
        # Validate configuration if requested
        if args.validate:
            is_valid = pipeline.validate_configuration()
            sys.exit(0 if is_valid else 1)
        
        # Generate video
        video_path = pipeline.generate_video(
            topic=args.topic,
            output_filename=args.output,
            mock=args.mock
        )
        
        print("\n" + "="*60)
        print("✅ Video generation complete!")
        print(f"📹 Video saved to: {video_path}")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Generation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
