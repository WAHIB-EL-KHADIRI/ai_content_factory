"""
Visual Generator with support for multiple image generation providers
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path
import requests

from src.utils.utils import retry_with_backoff, generate_cache_key, get_cached_file, file_exists_and_valid


logger = logging.getLogger('VideoGenerator.VisualGenerator')


class VisualGenerator:
    """Generate images using various AI image generation services"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the visual generator
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.image_config = config.get('image_generation', {})
        self.provider = self.image_config.get('provider', 'openai')
        self.cache_dir = config.get('paths', {}).get('cache_images', 'cache/images')
        
        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"VisualGenerator initialized with provider: {self.provider}")
    
    def generate_image(self, prompt: str, output_path: Optional[str] = None, mock: bool = False) -> str:
        """
        Generate image from text prompt
        
        Args:
            prompt: Text description of the image
            output_path: Optional output path (if None, uses cache)
            mock: If True, return a placeholder path
            
        Returns:
            Path to generated image
        """
        if mock:
            logger.info("Using mock visual generation")
            return "mock_image.png"

        # Check cache first
        if output_path is None:
            cache_key = generate_cache_key(self.provider, prompt)
            output_path = get_cached_file(self.cache_dir, cache_key, '.png')
        
        if file_exists_and_valid(output_path, min_size=10000):  # Minimum 10KB
            logger.info(f"Using cached image: {output_path}")
            return output_path
        
        logger.info(f"Generating image with {self.provider} provider")
        logger.debug(f"Prompt: {prompt}")
        
        # Generate image based on provider
        if self.provider == 'openai':
            self._generate_openai(prompt, output_path)
        elif self.provider == 'stability':
            self._generate_stability(prompt, output_path)
        elif self.provider == 'local':
            self._generate_local(prompt, output_path)
        else:
            raise ValueError(f"Unsupported image generation provider: {self.provider}")
        
        logger.info(f"Image generated: {output_path}")
        return output_path
    
    def _generate_openai(self, prompt: str, output_path: str):
        """Generate image using OpenAI DALL-E"""
        try:
            from openai import OpenAI
            
            config = self.image_config.get('openai', {})
            client = OpenAI(api_key=config.get('api_key'))
            
            def api_call():
                response = client.images.generate(
                    model=config.get('model', 'dall-e-3'),
                    prompt=prompt,
                    size=config.get('size', '1792x1024'),
                    quality=config.get('quality', 'hd'),
                    n=1
                )
                
                # Download image
                image_url = response.data[0].url
                img_response = requests.get(image_url)
                img_response.raise_for_status()
                
                with open(output_path, 'wb') as f:
                    f.write(img_response.content)
            
            retry_with_backoff(api_call)
            
        except ImportError:
            logger.error("OpenAI library not installed. Install with: pip install openai")
            raise
    
    def _generate_stability(self, prompt: str, output_path: str):
        """Generate image using Stability AI"""
        try:
            import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation
            from stability_sdk import client
            
            config = self.image_config.get('stability', {})
            
            stability_api = client.StabilityInference(
                key=config.get('api_key'),
                engine=config.get('engine', 'stable-diffusion-xl-1024-v1-0')
            )
            
            def api_call():
                answers = stability_api.generate(
                    prompt=prompt,
                    width=config.get('width', 1792),
                    height=config.get('height', 1024)
                )
                
                for resp in answers:
                    for artifact in resp.artifacts:
                        if artifact.finish_reason == generation.FILTER:
                            logger.warning("Content filtered by safety system")
                        if artifact.type == generation.ARTIFACT_IMAGE:
                            with open(output_path, 'wb') as f:
                                f.write(artifact.binary)
                            return
            
            retry_with_backoff(api_call)
            
        except ImportError:
            logger.error("Stability SDK not installed. Install with: pip install stability-sdk")
            raise
    
    def _generate_local(self, prompt: str, output_path: str):
        """Generate image using local Stable Diffusion"""
        try:
            from diffusers import StableDiffusionXLPipeline
            import torch
            
            config = self.image_config.get('local', {})
            
            # Load pipeline (should be cached after first load)
            device = config.get('device', 'cuda' if torch.cuda.is_available() else 'cpu')
            model_id = config.get('model_id', 'stabilityai/stable-diffusion-xl-base-1.0')
            
            logger.info(f"Loading Stable Diffusion model on {device}...")
            
            pipe = StableDiffusionXLPipeline.from_pretrained(
                model_id,
                torch_dtype=torch.float16 if device == 'cuda' else torch.float32
            )
            pipe = pipe.to(device)
            
            # Generate image
            num_steps = config.get('num_inference_steps', 50)
            image = pipe(
                prompt=prompt,
                num_inference_steps=num_steps,
                height=1024,
                width=1792
            ).images[0]
            
            # Save image
            image.save(output_path)
            
        except ImportError:
            logger.error("Diffusers/Torch not installed. Install with: pip install diffusers torch")
            raise
    
    def enhance_for_video(self, prompt: str) -> str:
        """
        Enhance prompt with video-specific modifiers
        
        Args:
            prompt: Original prompt
            
        Returns:
            Enhanced prompt optimized for video frames
        """
        enhancements = [
            "cinematic",
            "high quality",
            "detailed",
            "professional photography",
            "well-lit",
            "clear focus"
        ]
        
        enhanced = f"{prompt}, {', '.join(enhancements)}"
        return enhanced
