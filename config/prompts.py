"""
Prompt templates for script generation
"""

SCRIPT_GENERATION_PROMPT = """You are a professional video script writer. Create an engaging video script about the following topic.

Topic: {topic}

Requirements:
- Create {min_scenes} to {max_scenes} scenes
- Target total duration: approximately {target_duration} seconds
- Style: {style}
- Each scene should have clear narration text and a visual description
- Make it engaging, educational, and well-paced

Return ONLY a valid JSON object with this exact structure:
{{
  "title": "Video Title",
  "scenes": [
    {{
      "id": 1,
      "narration": "The narration text for this scene...",
      "visual_prompt": "Detailed description of what should be shown visually",
      "duration": 8
    }}
  ]
}}

Important:
- The narration should be natural and engaging
- Visual prompts should be detailed and descriptive for AI image generation
- Scene durations should vary between 5-12 seconds
- Total duration should be close to {target_duration} seconds
- Output ONLY the JSON, no markdown formatting or extra text
"""


VISUAL_ENHANCEMENT_PROMPT = """Given this visual description: "{visual_prompt}"

Enhance it for AI image generation by:
1. Adding specific visual details (colors, lighting, composition)
2. Specifying the art style (photorealistic, cinematic, illustration, etc.)
3. Adding quality modifiers

Return only the enhanced prompt, nothing else."""


def get_script_prompt(topic: str, config: dict) -> str:
    """
    Generate the script generation prompt
    
    Args:
        topic: Video topic
        config: Script configuration
        
    Returns:
        Formatted prompt
    """
    return SCRIPT_GENERATION_PROMPT.format(
        topic=topic,
        min_scenes=config.get('min_scenes', 3),
        max_scenes=config.get('max_scenes', 8),
        target_duration=config.get('target_duration', 60),
        style=config.get('style', 'educational')
    )


def get_visual_enhancement_prompt(visual_prompt: str) -> str:
    """
    Generate prompt to enhance visual descriptions
    
    Args:
        visual_prompt: Original visual prompt
        
    Returns:
        Enhancement prompt
    """
    return VISUAL_ENHANCEMENT_PROMPT.format(visual_prompt=visual_prompt)
