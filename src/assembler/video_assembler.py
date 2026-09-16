"""
Video Assembler using MoviePy
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    CompositeVideoClip,
    concatenate_videoclips,
    CompositeAudioClip,
)
from moviepy.video.fx.all import fadein, fadeout
from moviepy.video.fx.resize import resize

from src.utils.utils import format_duration


logger = logging.getLogger("VideoGenerator.VideoAssembler")


class VideoAssembler:
    """Assemble video from scenes using MoviePy"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the video assembler

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.video_config = config.get("video", {})
        self.output_dir = config.get("paths", {}).get("output_dir", "output")

        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        logger.info("VideoAssembler initialized")

    def assemble(
        self,
        scenes: List[Dict[str, Any]],
        output_filename: str,
        title: Optional[str] = None,
    ) -> str:
        """
        Assemble video from scenes

        Args:
            scenes: List of scene dictionaries with audio_path, image_path, duration
            output_filename: Output video filename
            title: Optional video title

        Returns:
            Path to generated video
        """
        output_path = Path(self.output_dir) / output_filename

        logger.info(f"Assembling video with {len(scenes)} scenes")
        logger.info(f"Output: {output_path}")

        # Create video clips for each scene
        video_clips = []

        for i, scene in enumerate(scenes):
            logger.info(f"Processing scene {i + 1}/{len(scenes)}")

            # Create image clip
            image_path = scene.get("image_path")
            audio_path = scene.get("audio_path")
            duration = scene.get("duration", 5.0)

            if not image_path or not Path(image_path).exists():
                logger.error(f"Image not found for scene {i + 1}: {image_path}")
                continue

            # Create video clip from image
            clip = ImageClip(image_path, duration=duration)

            # Apply Ken Burns effect if enabled
            if self.video_config.get("ken_burns_effect", True):
                clip = self._apply_ken_burns(clip, i)

            # Resize to target resolution
            resolution = self.video_config.get("resolution", [1920, 1080])
            clip = resize(clip, newsize=resolution)

            # Add audio if available
            if audio_path and Path(audio_path).exists():
                audio = AudioFileClip(audio_path)
                clip = clip.set_audio(audio)
                # Update duration to match audio
                clip = clip.set_duration(audio.duration)

            # Add fade in/out transitions
            transition_duration = self.video_config.get("transition_duration", 1.0)
            if i == 0:
                # Fade in for first scene
                clip = fadein(clip, transition_duration)
            if i == len(scenes) - 1:
                # Fade out for last scene
                clip = fadeout(clip, transition_duration)

            video_clips.append(clip)

        if not video_clips:
            raise ValueError("No valid video clips created")

        # Concatenate all clips
        logger.info("Concatenating clips...")
        final_clip = concatenate_videoclips(video_clips, method="compose")

        # Add background music if specified
        bg_music_path = self.video_config.get("background_music")
        if bg_music_path and Path(bg_music_path).exists():
            final_clip = self._add_background_music(final_clip, bg_music_path)

        # Write final video
        logger.info("Writing video file...")
        total_duration = format_duration(final_clip.duration)
        logger.info(f"Total video duration: {total_duration}")

        final_clip.write_videofile(
            str(output_path),
            fps=self.video_config.get("fps", 30),
            codec=self.video_config.get("codec", "libx264"),
            audio_codec=self.video_config.get("audio_codec", "aac"),
            bitrate=self.video_config.get("bitrate", "8000k"),
            preset="medium",
            threads=4,
        )

        # Clean up
        logger.info("Cleaning up clips...")
        final_clip.close()
        for clip in video_clips:
            clip.close()

        logger.info(f"Video assembly complete: {output_path}")
        return str(output_path)

    def _apply_ken_burns(self, clip, scene_index: int):
        """
        Apply Ken Burns effect (zoom and pan) to image clip

        Args:
            clip: ImageClip to apply effect to
            scene_index: Index of scene (for variation)

        Returns:
            Modified clip
        """
        # Alternate between zoom in and zoom out
        zoom_in = scene_index % 2 == 0
        duration = clip.duration

        if zoom_in:
            # Zoom in effect: from 1.0 to 1.1
            return clip.resize(lambda t: 1.0 + 0.1 * (t / duration))
        else:
            # Zoom out effect: from 1.1 to 1.0
            return clip.resize(lambda t: 1.1 - 0.1 * (t / duration))

    def _add_background_music(self, video_clip, music_path: str, volume: float = 0.1):
        """
        Add background music to video

        Args:
            video_clip: Video clip to add music to
            music_path: Path to music file
            volume: Music volume (0.0 to 1.0)

        Returns:
            Video clip with background music
        """
        logger.info("Adding background music...")

        # Load music
        music = AudioFileClip(music_path)

        # Loop music if needed
        if music.duration < video_clip.duration:
            n_loops = int(video_clip.duration / music.duration) + 1
            music = music.loop(n=n_loops)

        # Trim music to video duration
        music = music.subclip(0, video_clip.duration)

        # Reduce volume
        music = music.volumex(volume)

        # Mix with existing audio
        if video_clip.audio:
            final_audio = CompositeAudioClip([video_clip.audio, music])
            video_clip = video_clip.set_audio(final_audio)
        else:
            video_clip = video_clip.set_audio(music)

        return video_clip

    def create_title_card(self, title: str, duration: float = 3.0) -> ImageClip:
        """
        Create a title card clip

        Args:
            title: Title text
            duration: Duration in seconds

        Returns:
            ImageClip with title
        """
        from moviepy.editor import TextClip, ColorClip

        resolution = self.video_config.get("resolution", [1920, 1080])

        # Create black background
        background = ColorClip(size=resolution, color=(0, 0, 0), duration=duration)

        # Create title text
        title_clip = TextClip(
            title, fontsize=70, color="white", font="Arial-Bold", size=resolution
        )
        title_clip = title_clip.set_duration(duration).set_position("center")

        # Composite
        final = CompositeVideoClip([background, title_clip])

        return final
