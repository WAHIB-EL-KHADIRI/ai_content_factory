# AI Video Generation System

An AI-powered system that automatically generates complete videos from simple text topics. Uses DeepSeek for script generation, multiple TTS providers for voiceover, image generation APIs for visuals, and MoviePy for video assembly.

## Features

- 🤖 **AI Script Generation**: Uses DeepSeek to create structured video scripts
- 🎙️ **Multi-Provider TTS**: Supports ElevenLabs, Azure, Google Cloud, and Coqui TTS
- 🎨 **Flexible Image Generation**: Works with DALL-E 3, Stability AI, or local Stable Diffusion
- 🎬 **Professional Video Assembly**: MoviePy-based assembly with transitions and effects
- 💾 **Smart Caching**: Caches audio and images to avoid regeneration
- ⚡ **Parallel Processing**: Generates voiceovers and visuals concurrently

## System Architecture

```
Topic Input → Script Generator (DeepSeek)
            ↓
         Scenes → Voiceover Generator (TTS) → Audio Files
            ↓           ↓
            └────→ Visual Generator (AI) → Image Files
                        ↓
                  Video Assembler (MoviePy) → Final Video
```

## Installation

1. **Clone or navigate to the project directory**

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure API keys** (see Configuration section)

## Configuration

Edit `config.yaml` to set up your API keys and preferences:

### Required API Keys

1. **DeepSeek API** (required):
   - Get your API key from [DeepSeek](https://platform.deepseek.com/)
   - Set in `config.yaml` under `deepseek.api_key`

2. **TTS Service** (choose one):
   - **ElevenLabs** (recommended): https://elevenlabs.io/
   - **Azure Cognitive Services**: https://azure.microsoft.com/en-us/services/cognitive-services/speech-services/
   - **Google Cloud TTS**: https://cloud.google.com/text-to-speech
   - **Coqui TTS** (free, local, no API key needed)

3. **Image Generation** (choose one):
   - **OpenAI DALL-E 3**: https://platform.openai.com/
   - **Stability AI**: https://stability.ai/
   - **Local Stable Diffusion** (free, requires GPU)

### Basic Configuration Example

```yaml
deepseek:
  api_key: "sk-xxxxx"

tts:
  provider: "elevenlabs"  # or "azure", "google", "coqui"
  elevenlabs:
    api_key: "your-key-here"

image_generation:
  provider: "openai"  # or "stability", "local"
  openai:
    api_key: "sk-xxxxx"
```

## Usage

### Basic Usage

Generate a video from a topic:

```bash
python main.py "The History of Coffee"
```

### Advanced Options

```bash
# Specify output filename
python main.py "The History of Coffee" --output coffee_history.mp4

# Use custom config file
python main.py "Topic" --config my_config.yaml

# Validate configuration
python main.py --validate "Test Topic"
```

### Python API Usage

```python
from modules import VideoGenerationPipeline

# Initialize pipeline
pipeline = VideoGenerationPipeline(config_path="config.yaml")

# Generate video
video_path = pipeline.generate_video(
    topic="The History of Coffee",
    output_filename="coffee_history.mp4"
)

print(f"Video saved to: {video_path}")
```

## Project Structure

```
ai_content_factory/
├── main.py                      # Main orchestrator
├── config.yaml                  # Configuration file
├── requirements.txt             # Python dependencies
├── README.md                    # This file
│
├── modules/
│   ├── __init__.py              # Module exports
│   ├── utils.py                 # Utility functions
│   ├── prompts.py               # Prompt templates
│   ├── script_generator.py     # DeepSeek integration
│   ├── voiceover_generator.py  # TTS integration
│   ├── visual_generator.py     # Image generation
│   └── video_assembler.py      # MoviePy assembly
│
├── cache/
│   ├── audio/                   # Cached audio files
│   └── images/                  # Cached images
│
├── output/                      # Generated videos
└── logs/                        # Log files
```

## How It Works

1. **Script Generation**: 
   - Takes a topic as input
   - Calls DeepSeek API to generate structured script
   - Parses script into scenes with narration and visual descriptions

2. **Asset Generation**:
   - **Voiceovers**: Converts narration to audio using TTS
   - **Visuals**: Generates images from visual descriptions using AI
   - Both processes run concurrently for efficiency

3. **Video Assembly**:
   - Combines images and audio for each scene
   - Applies Ken Burns effect (zoom/pan) to images
   - Adds transitions between scenes
   - Exports final video with proper encoding

## Configuration Options

### Video Settings

```yaml
video:
  resolution: [1920, 1080]      # Video resolution
  fps: 30                        # Frames per second
  transition_duration: 1.0       # Transition time in seconds
  ken_burns_effect: true         # Apply zoom/pan to images
  background_music: null         # Path to music file (optional)
```

### Script Settings

```yaml
script:
  min_scenes: 3                  # Minimum number of scenes
  max_scenes: 8                  # Maximum number of scenes
  target_duration: 60            # Target duration in seconds
  style: "educational"           # Video style
```

## Troubleshooting

### API Key Issues
- Make sure API keys are correctly set in `config.yaml`
- Run `python main.py --validate "Test"` to check configuration

### MoviePy Installation Issues
- On Windows, you may need to install ImageMagick separately
- Download from: https://imagemagick.org/script/download.php

### GPU Memory Issues (Local Stable Diffusion)
- Reduce image resolution in config
- Use fewer inference steps
- Switch to CPU mode (slower but uses less memory)

### Audio Generation Fails
- Check TTS API quotas and limits
- Try switching to Coqui TTS (local, free) for testing
- Check internet connection for cloud providers

## Performance Tips

1. **Use Caching**: Generated audio and images are cached automatically
2. **Choose Providers Wisely**: 
   - Fastest: ElevenLabs (TTS) + DALL-E 3 (images)
   - Free: Coqui TTS + Local Stable Diffusion
3. **Optimize Settings**: Lower FPS and resolution for faster processing

## Requirements

- Python 3.9 or higher
- FFmpeg (for MoviePy)
- Minimum 8GB RAM
- GPU recommended for local Stable Diffusion

## License

This project is provided as-is for educational and commercial purposes.

## Contributing

Feel free to submit issues, fork the repository, and create pull requests.

## Credits

- **DeepSeek**: AI script generation
- **MoviePy**: Video assembly
- **TTS Providers**: ElevenLabs, Azure, Google, Coqui
- **Image Generation**: OpenAI, Stability AI, Hugging Face

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review logs in `logs/video_generator.log`
3. Ensure all API keys are valid and have sufficient credits
