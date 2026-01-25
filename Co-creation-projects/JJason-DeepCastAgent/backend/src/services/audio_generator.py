"""Service for generating audio from text using TTS API."""

from __future__ import annotations

import logging
import os
import requests
from pathlib import Path
from typing import List, Optional

from config import Configuration
from pydub import AudioSegment

logger = logging.getLogger(__name__)


class AudioGenerationService:
    """Handles interaction with TTS service to generate audio files."""

    def __init__(self, config: Configuration) -> None:
        self._config = config
        self._output_dir = Path(config.audio_output_dir)
        self._ensure_output_dir()

    def _ensure_output_dir(self) -> None:
        """Create output directory if it doesn't exist."""
        if not self._output_dir.exists():
            try:
                self._output_dir.mkdir(parents=True, exist_ok=True)
                logger.info("Created audio output directory: %s", self._output_dir)
            except Exception as e:
                logger.error("Failed to create audio output directory: %s", e)

    def generate_audio(self, script: List[dict[str, str]], task_id: str = "default") -> List[str]:
        """
        Generate audio files for a given script.
        
        Args:
            script: List of dialogue turns, e.g. [{"role": "Host", "content": "..."}, ...]
            task_id: Unique identifier for the current task/session
            
        Returns:
            List of paths to generated audio files
        """
        # 检查FFmpeg路径是否配置
        if not self._config.ffmpeg_path:
            logger.error("FFmpeg path not configured. Audio generation will fail.")
            return []
        if not self._config.tts_api_key:
            logger.warning("TTS API key not configured. Skipping audio generation.")
            return []

        generated_files = []
        
        for index, turn in enumerate(script):
            role = turn.get("role", "")
            content = turn.get("content", "")
            
            if not role or not content:
                continue
                
            voice_id = self._get_voice_for_role(role)
            if not voice_id:
                logger.warning("Unknown role: %s. Using default voice.", role)
                voice_id = "xiayu" # Fallback
            
            file_name = f"{task_id}_{index:03d}_{role}.mp3"
            file_path = self._output_dir / file_name
            
            if self._call_tts_api(content, voice_id, file_path):
                generated_files.append(str(file_path))
            else:
                logger.error("Failed to generate audio for turn %d (%s)", index, role)
                
        logger.info("Generated %d audio files for task %s", len(generated_files), task_id)
        return generated_files

    def _get_voice_for_role(self, role: str) -> str:
        """Map role names to voice IDs."""
        role_lower = role.lower()
        if "host" in role_lower or "xiayu" in role_lower:
            return "xiayu"
        elif "guest" in role_lower or "liwa" in role_lower:
            return "liwa"
        return "xiayu"

    def _call_tts_api(self, text: str, voice: str, output_path: Path) -> bool:
        """Call the TTS API and save the audio file."""
        if output_path.exists():
            logger.debug("Audio file already exists: %s", output_path)
            return True

        headers = {
            "Authorization": f"Bearer {self._config.tts_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self._config.tts_model,
            "input": text,
            "voice": voice,
            "speed": 1.0
        }
        
        try:
            logger.debug("Calling TTS API for voice %s: %s...", voice, text[:20])
            response = requests.post(
                self._config.tts_base_url,
                json=payload,
                headers=headers,
                timeout=30 # TTS generation might take some time
            )
            
            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                return True
            else:
                logger.error(
                    "TTS API failed with status %d: %s", 
                    response.status_code, 
                    response.text
                )
                return False
                
        except Exception as e:
            logger.exception("Exception during TTS API call: %s", e)
            return False
