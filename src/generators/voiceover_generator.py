"""
Voiceover Generator with support for multiple TTS providers
"""

import os
import logging
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

from src.utils.utils import (
    retry_with_backoff,
    generate_cache_key,
    get_cached_file,
    file_exists_and_valid,
)


logger = logging.getLogger("VideoGenerator.VoiceoverGenerator")


class VoiceoverGenerator:
    """Generate voiceovers using various TTS services"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the voiceover generator

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.tts_config = config.get("tts", {})
        self.provider = self.tts_config.get("provider", "elevenlabs")
        self.cache_dir = config.get("paths", {}).get("cache_audio", "cache/audio")

        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)

        logger.info(f"VoiceoverGenerator initialized with provider: {self.provider}")

    def generate_audio(
        self, text: str, output_path: Optional[str] = None, mock: bool = False
    ) -> Tuple[str, float]:
        """
        Generate audio from text

        Args:
            text: Text to convert to speech
            output_path: Optional output path (if None, uses cache)
            mock: If True, simulate audio creation

        Returns:
            Tuple of (audio_file_path, duration_in_seconds)
        """
        if mock:
            logger.info("Using mock voiceover generation")
            # Return a default path or handle mock logic
            # For simplicity in mock mode, we'll just not create a file but return a fake path
            # The assembler will need a real file later, so we'll create a dummy one if needed
            return "mock_audio.mp3", 5.0

        # Check cache first
        if output_path is None:
            cache_key = generate_cache_key(self.provider, text)
            output_path = get_cached_file(self.cache_dir, cache_key, ".mp3")

        if file_exists_and_valid(output_path):
            logger.info(f"Using cached audio: {output_path}")
            duration = self._get_audio_duration(output_path)
            return output_path, duration

        logger.info(f"Generating audio with {self.provider} provider")

        # Generate audio based on provider
        if self.provider == "elevenlabs":
            self._generate_elevenlabs(text, output_path)
        elif self.provider == "azure":
            self._generate_azure(text, output_path)
        elif self.provider == "google":
            self._generate_google(text, output_path)
        elif self.provider == "coqui":
            self._generate_coqui(text, output_path)
        else:
            raise ValueError(f"Unsupported TTS provider: {self.provider}")

        duration = self._get_audio_duration(output_path)
        logger.info(f"Audio generated: {output_path} (duration: {duration:.2f}s)")

        return output_path, duration

    def _generate_elevenlabs(self, text: str, output_path: str):
        """Generate audio using ElevenLabs"""
        try:
            from elevenlabs import ElevenLabs, save

            config = self.tts_config.get("elevenlabs", {})
            client = ElevenLabs(api_key=config.get("api_key"))

            def api_call():
                audio = client.text_to_speech.convert(
                    voice_id=config.get("voice_id", "21m00Tcm4TlvDq8ikWAM"),
                    text=text,
                    model_id=config.get("model_id", "eleven_multilingual_v2"),
                )
                save(audio, output_path)

            retry_with_backoff(api_call)

        except ImportError:
            logger.error(
                "ElevenLabs library not installed. Install with: pip install elevenlabs"
            )
            raise

    def _generate_azure(self, text: str, output_path: str):
        """Generate audio using Azure Cognitive Services"""
        try:
            import azure.cognitiveservices.speech as speechsdk

            config = self.tts_config.get("azure", {})

            speech_config = speechsdk.SpeechConfig(
                subscription=config.get("api_key"),
                region=config.get("region", "eastus"),
            )
            speech_config.speech_synthesis_voice_name = config.get(
                "voice_name", "en-US-JennyNeural"
            )

            audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=speech_config, audio_config=audio_config
            )

            def api_call():
                result = synthesizer.speak_text_async(text).get()
                if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
                    raise Exception(f"Speech synthesis failed: {result.reason}")

            retry_with_backoff(api_call)

        except ImportError:
            logger.error(
                "Azure Speech SDK not installed. Install with: pip install azure-cognitiveservices-speech"
            )
            raise

    def _generate_google(self, text: str, output_path: str):
        """Generate audio using Google Cloud TTS"""
        try:
            from google.cloud import texttospeech

            config = self.tts_config.get("google", {})

            # Set credentials if provided
            credentials_path = config.get("credentials_path")
            if credentials_path:
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

            client = texttospeech.TextToSpeechClient()

            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(
                language_code=config.get("language_code", "en-US"),
                name=config.get("voice_name", "en-US-Neural2-C"),
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )

            def api_call():
                response = client.synthesize_speech(
                    input=synthesis_input, voice=voice, audio_config=audio_config
                )
                with open(output_path, "wb") as out:
                    out.write(response.audio_content)

            retry_with_backoff(api_call)

        except ImportError:
            logger.error(
                "Google Cloud TTS not installed. Install with: pip install google-cloud-texttospeech"
            )
            raise

    def _generate_coqui(self, text: str, output_path: str):
        """Generate audio using Coqui TTS (local)"""
        try:
            from TTS.api import TTS

            config = self.tts_config.get("coqui", {})
            model_name = config.get(
                "model_name", "tts_models/en/ljspeech/tacotron2-DDC"
            )

            tts = TTS(model_name=model_name)
            tts.tts_to_file(text=text, file_path=output_path)

        except ImportError:
            logger.error("Coqui TTS not installed. Install with: pip install TTS")
            raise

    def _get_audio_duration(self, audio_path: str) -> float:
        """
        Get duration of audio file

        Args:
            audio_path: Path to audio file

        Returns:
            Duration in seconds
        """
        try:
            from pydub import AudioSegment

            audio = AudioSegment.from_file(audio_path)
            return len(audio) / 1000.0  # Convert ms to seconds
        except Exception as e:
            logger.warning(f"Could not determine audio duration: {e}")
            # Fallback: estimate based on text length (rough approximation)
            return 0.0
