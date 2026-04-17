"""
Test script to verify the system setup without requiring API keys
"""

import sys
import os
from pathlib import Path


def test_imports():
    """Test that all modules can be imported"""
    print("Testing module imports...")
    
    try:
        from modules import (
            load_config,
            setup_logging,
            ensure_directories,
            ScriptGenerator,
            VoiceoverGenerator,
            VisualGenerator,
            VideoAssembler
        )
        print("✅ All modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def test_directory_structure():
    """Test that all required directories exist or can be created"""
    print("\nTesting directory structure...")
    
    required_dirs = [
        'modules',
        'cache',
        'cache/audio',
        'cache/images',
        'output',
        'logs'
    ]
    
    all_good = True
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"✅ {dir_path} exists")
        else:
            try:
                Path(dir_path).mkdir(parents=True, exist_ok=True)
                print(f"✅ {dir_path} created")
            except Exception as e:
                print(f"❌ Failed to create {dir_path}: {e}")
                all_good = False
    
    return all_good


def test_config_file():
    """Test that config file exists and can be loaded"""
    print("\nTesting configuration file...")
    
    if not Path('config.yaml').exists():
        print("❌ config.yaml not found")
        return False
    
    try:
        from modules import load_config
        config = load_config('config.yaml')
        print("✅ config.yaml loaded successfully")
        
        # Check required config sections
        required_sections = ['deepseek', 'tts', 'image_generation', 'video', 'paths']
        for section in required_sections:
            if section in config:
                print(f"  ✅ {section} section present")
            else:
                print(f"  ⚠️  {section} section missing")
        
        return True
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return False


def test_dependencies():
    """Test that required dependencies are installed"""
    print("\nTesting dependencies...")
    
    dependencies = {
        'moviepy': 'moviepy',
        'PIL': 'Pillow',
        'yaml': 'PyYAML',
        'openai': 'openai',
        'requests': 'requests',
        'tqdm': 'tqdm'
    }
    
    all_installed = True
    for module, package in dependencies.items():
        try:
            __import__(module)
            print(f"✅ {package} installed")
        except ImportError:
            print(f"❌ {package} not installed - run: pip install {package}")
            all_installed = False
    
    # Optional dependencies
    print("\nOptional dependencies (based on your provider choice):")
    optional = {
        'elevenlabs': 'ElevenLabs TTS',
        'azure.cognitiveservices.speech': 'Azure Speech',
        'google.cloud.texttospeech': 'Google Cloud TTS',
        'TTS': 'Coqui TTS',
        'stability_sdk': 'Stability AI',
        'diffusers': 'Stable Diffusion'
    }
    
    for module, name in optional.items():
        try:
            __import__(module)
            print(f"✅ {name} installed")
        except ImportError:
            print(f"⚪ {name} not installed (optional)")
    
    return all_installed


def main():
    """Run all tests"""
    print("="*60)
    print("AI Video Generation System - Setup Test")
    print("="*60)
    
    results = {
        'imports': test_imports(),
        'directories': test_directory_structure(),
        'config': test_config_file(),
        'dependencies': test_dependencies()
    }
    
    print("\n" + "="*60)
    print("Test Summary:")
    print("="*60)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.capitalize()}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n✅ All tests passed!")
        print("\nNext steps:")
        print("1. Edit config.yaml and add your API keys")
        print("2. Run: python main.py 'Your Topic Here'")
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")
        print("Run: pip install -r requirements.txt")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
