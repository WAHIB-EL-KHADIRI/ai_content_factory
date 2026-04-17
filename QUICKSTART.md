# Quick Start Guide

## 1. First Time Setup

### Install Dependencies
```bash
# Navigate to project directory
cd ai_content_factory

# Install Python packages
pip install -r requirements.txt
```

### Configure API Keys

Edit `config.yaml` and add your API keys:

**Minimum Requirements** (choose one option per category):

**Option A - Cloud Services (Easiest)**
- DeepSeek API key (required for script generation)
- ElevenLabs API key (for voiceover)
- OpenAI API key (for images)

**Option B - Free/Local (No cost)**
- DeepSeek API key (required, has free tier)
- Coqui TTS (local, free)
- Local Stable Diffusion (requires GPU)

### Verify Setup
```bash
python test_setup.py
```

## 2. Generate Your First Video

### Simple Command
```bash
python main.py "The History of Coffee"
```

### With Custom Output Name
```bash
python main.py "The History of Coffee" --output my_video.mp4
```

## 3. Common Commands

### Validate Configuration
```bash
python main.py --validate "Test"
```

### Use Custom Config
```bash
python main.py "Topic" --config custom_config.yaml
```

### View Help
```bash
python main.py --help
```

## 4. What Happens During Generation

1. **Script Generation** (~10-30 seconds)
   - Calls DeepSeek to create video script
   - Splits into 3-8 scenes

2. **Voiceover Generation** (~30-60 seconds)
   - Converts narration to audio using TTS
   - Cached for reuse

3. **Visual Generation** (~1-3 minutes)
   - Creates AI-generated images for each scene
   - Cached for reuse

4. **Video Assembly** (~30-60 seconds)
   - Combines audio and visuals
   - Adds transitions
   - Exports final MP4

**Total Time**: ~2-5 minutes per video (first run)
**Subsequent runs**: Much faster due to caching

## 5. Recommended Provider Combinations

### Best Quality (Paid)
```yaml
tts:
  provider: "elevenlabs"
image_generation:
  provider: "openai"
```

### Best Value (Mixed)
```yaml
tts:
  provider: "elevenlabs"
image_generation:
  provider: "stability"
```

### Free (Local)
```yaml
tts:
  provider: "coqui"
image_generation:
  provider: "local"
```

## 6. Troubleshooting

### "API key not configured"
- Edit `config.yaml` and replace `YOUR_XXX_API_KEY` with actual keys

### "Module not found"
- Run: `pip install -r requirements.txt`

### Video generation fails
- Check logs in `logs/video_generator.log`
- Verify API keys are correct
- Ensure you have internet connection (for cloud APIs)

### Out of memory (local Stable Diffusion)
- Switch to cloud provider (OpenAI or Stability)
- Or reduce image resolution in config

## 7. Tips for Better Results

1. **Be Specific with Topics**: 
   - ❌ "Coffee"
   - ✅ "The History and Cultural Impact of Coffee"

2. **Adjust Settings**:
   - Edit `script` section in config.yaml
   - Change `style` to "educational", "documentary", or "entertaining"
   - Adjust `target_duration` for longer/shorter videos

3. **Use Caching**:
   - Generated assets are cached
   - Re-run with same topic uses cached audio/images
   - Clear `cache/` folder to regenerate

## 8. Example Topics

Try these example topics:

- "How the Internet Works"
- "The Life Cycle of Stars"
- "Ancient Egyptian Civilization"
- "Climate Change: Causes and Solutions"
- "The Science of Cooking"
- "How Airplanes Fly"
- "The Human Immune System"

## 9. Next Steps

- Read full `README.md` for detailed documentation
- Check `example.py` for programmatic usage
- Explore `architecture.md` to understand the system
- Customize `config.yaml` for your preferences

## 10. Getting API Keys

### DeepSeek (Required)
1. Go to https://platform.deepseek.com/
2. Sign up for account
3. Navigate to API Keys section
4. Create new API key

### ElevenLabs (Recommended for TTS)
1. Go to https://elevenlabs.io/
2. Sign up for account
3. Go to Profile → API Keys
4. Copy your API key

### OpenAI (For DALL-E 3)
1. Go to https://platform.openai.com/
2. Sign up for account
3. Navigate to API Keys
4. Create new secret key

---

**Ready to create amazing AI videos!** 🎬
