"""Service for synthesizing audio segments into a single podcast file."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from pydub import AudioSegment

from config import Configuration

logger = logging.getLogger(__name__)


class PodcastSynthesisService:
    """Combines multiple audio segments into a final podcast file."""

    def __init__(self, config: Configuration) -> None:
        self._config = config
        self._output_dir = Path(config.audio_output_dir)
        
        # Configure ffmpeg path if provided
        if config.ffmpeg_path:
            AudioSegment.converter = config.ffmpeg_path
            logger.info("Configured ffmpeg path: %s", config.ffmpeg_path)
        
        # Ensure pydub/ffmpeg is available - assuming ffmpeg is installed on system
        # If not, pydub might warn or fail, but we'll catch exceptions.

    def synthesize_podcast(self, audio_files: List[str], task_id: str = "default") -> str | None:
        """
        Combine audio files into a single podcast MP3.

        Args:
            audio_files: List of paths to input audio files in order.
            task_id: Unique identifier for the output filename.

        Returns:
            Path to the final podcast file, or None if failed.
        """
        if not audio_files:
            logger.warning("No audio files provided for synthesis.")
            return None

        try:
            combined = AudioSegment.empty()
            
            # Silence between segments (e.g. 500ms)
            silence = AudioSegment.silent(duration=500)

            valid_segments_count = 0
            for file_path in audio_files:
                path = Path(file_path)
                if not path.exists():
                    logger.warning("Audio file not found: %s", file_path)
                    continue
                
                try:
                    segment = AudioSegment.from_file(file_path, format="mp3")
                    if valid_segments_count > 0:
                        combined += silence
                    combined += segment
                    valid_segments_count += 1
                except Exception as e:
                    logger.error("Failed to load audio segment %s: %s", file_path, e)

            if valid_segments_count == 0:
                logger.error("No valid audio segments to combine.")
                return None

            output_filename = f"podcast_{task_id}.mp3"
            output_path = self._output_dir / output_filename
            
            # Export
            logger.info("Exporting podcast to %s...", output_path)
            combined.export(output_path, format="mp3")
            
            return str(output_path)

        except Exception as e:
            logger.exception("Podcast synthesis failed: %s", e)
            return None
