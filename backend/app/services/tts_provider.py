"""
Pluggable Text-To-Speech (TTS) Provider for NexuxEdu Micro-Lessons.

Architectural Principles:
1. Zero Mandatory External Dependency: Works out-of-the-box with EdgeTTS neural voices or local audio generator.
2. Provider Abstraction: Easily swap between EdgeTTS, ElevenLabs (if API key present), or Local Synthetic Audio.
3. Disk Caching: Audio files are hashed and stored in backend/media/audio/ outside SQLite.
4. Duration Synchronization: Accurately calculates audio duration so video scenes align with speech.
"""

import os
import sys
import abc
import hashlib
import asyncio
import wave
import struct
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Audio storage directory
MEDIA_DIR = Path(__file__).resolve().parent.parent.parent / "media"
AUDIO_CACHE_DIR = MEDIA_DIR / "audio"
TEMP_AUDIO_DIR = MEDIA_DIR / "temp"
for d in [AUDIO_CACHE_DIR, TEMP_AUDIO_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Capability flags
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    edge_tts = None
    EDGE_TTS_AVAILABLE = False

try:
    import imageio_ffmpeg
    FFMPEG_AVAILABLE = True
except ImportError:
    imageio_ffmpeg = None
    FFMPEG_AVAILABLE = False

def get_tts_capability_status() -> Dict[str, Any]:
    eleven_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    return {
        "edge_tts_available": EDGE_TTS_AVAILABLE,
        "elevenlabs_configured": bool(eleven_key),
        "offline_fallback_available": True,
        "ffmpeg_available": FFMPEG_AVAILABLE,
    }

class BaseTTSProvider(abc.ABC):
    @abc.abstractmethod
    async def generate_speech(self, text: str, output_path: Path) -> float:
        """
        Synthesizes speech for text and saves to output_path.
        Returns the duration of the generated audio in seconds.
        """
        pass

class EdgeTTSProvider(BaseTTSProvider):
    def __init__(self, voice: str = "en-US-ChristopherNeural"):
        self.voice = voice

    async def generate_speech(self, text: str, output_path: Path) -> float:
        if not EDGE_TTS_AVAILABLE or edge_tts is None:
            # Fallback to local tone/silent audio if edge_tts is not installed
            return generate_offline_fallback_audio(output_path, target_duration=max(3.0, len(text.split()) * 0.4))
        try:
            communicate = edge_tts.Communicate(text, self.voice)
            await communicate.save(str(output_path))
            return get_audio_duration(output_path)
        except Exception as e:
            # Fallback to local tone/silent audio if network or TTS fails
            return generate_offline_fallback_audio(output_path, target_duration=max(3.0, len(text.split()) * 0.4))

class ElevenLabsTTSProvider(BaseTTSProvider):
    def __init__(self, api_key: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM"):
        self.api_key = api_key
        self.voice_id = voice_id

    async def generate_speech(self, text: str, output_path: Path) -> float:
        import httpx
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                output_path.write_bytes(resp.content)
                return get_audio_duration(output_path)
            else:
                raise RuntimeError(f"ElevenLabs error {resp.status_code}: {resp.text}")

class OfflineFallbackTTSProvider(BaseTTSProvider):
    async def generate_speech(self, text: str, output_path: Path) -> float:
        duration = max(3.0, len(text.split()) * 0.4)
        return generate_offline_fallback_audio(output_path, target_duration=duration)

def generate_offline_fallback_audio(output_path: Path, target_duration: float = 3.0) -> float:
    """
    Generates a valid audio file (WAV or MP3) with soft acoustic tone envelope.
    Guarantees 100% offline availability without any external cloud or TTS dependency.
    """
    sample_rate = 24000
    num_samples = int(sample_rate * target_duration)
    
    # Save as WAV first
    wav_path = output_path.with_suffix(".wav")
    with wave.open(str(wav_path), "w") as wav_file:
        wav_file.setnchannels(1) # mono
        wav_file.setsampwidth(2) # 16-bit
        wav_file.setframerate(sample_rate)
        
        # Soft subtle carrier tone (440Hz fading softly)
        frames = []
        for i in range(num_samples):
            # very subtle envelope so it's not harsh
            val = int(500 * (1.0 - (i / num_samples)) * (i % 50 < 25))
            frames.append(struct.pack("<h", val))
        wav_file.writeframes(b"".join(frames))
    
    if output_path.suffix.lower() == ".mp3":
        # Convert WAV to MP3 using ffmpeg if available, otherwise keep WAV
        try:
            import imageio_ffmpeg
            import subprocess
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            subprocess.run(
                [ffmpeg_exe, "-y", "-i", str(wav_path), "-c:a", "libmp3lame", "-b:a", "128k", str(output_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
            if wav_path.exists():
                wav_path.unlink()
        except Exception:
            # If ffmpeg conversion fails, just rename to wav
            pass

    return target_duration

def get_audio_duration(file_path: Path) -> float:
    """Calculates audio duration using FFmpeg or wave module."""
    if file_path.suffix.lower() == ".wav":
        try:
            with wave.open(str(file_path), "r") as wav_file:
                frames = wav_file.getnframes()
                rate = wav_file.getframerate()
                return frames / float(rate)
        except Exception:
            pass

    try:
        import imageio_ffmpeg
        import subprocess
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [ffmpeg_exe, "-i", str(file_path)]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for line in result.stderr.splitlines():
            if "Duration:" in line:
                dur_str = line.split("Duration:")[1].split(",")[0].strip()
                parts = dur_str.split(":")
                hours = float(parts[0])
                minutes = float(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds
    except Exception:
        pass

    return 5.0

class TTSManager:
    def __init__(self):
        eleven_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
        if eleven_key:
            voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM").strip()
            self.provider: BaseTTSProvider = ElevenLabsTTSProvider(api_key=eleven_key, voice_id=voice_id)
        else:
            self.provider = EdgeTTSProvider()

    def get_cache_key(self, text: str, voice_tag: str = "edge") -> str:
        h = hashlib.sha256(f"{voice_tag}:{text.strip().lower()}".encode("utf-8")).hexdigest()[:16]
        return f"narration_{h}.mp3"

    async def get_or_generate_scene_audio(self, text: str, voice_tag: str = "edge") -> Tuple[Path, float]:
        """
        Retrieves cached audio or generates new speech file.
        Returns (Path_to_audio, duration_in_seconds).
        """
        if not text or not text.strip():
            silence_path = AUDIO_CACHE_DIR / "silence_1s.mp3"
            if not silence_path.exists():
                generate_offline_fallback_audio(silence_path, 1.0)
            return silence_path, 1.0

        filename = self.get_cache_key(text, voice_tag)
        target_path = AUDIO_CACHE_DIR / filename

        if target_path.exists() and target_path.stat().st_size > 500:
            duration = get_audio_duration(target_path)
            return target_path, duration

        # Generate fresh audio
        try:
            duration = await self.provider.generate_speech(text, target_path)
        except Exception:
            fallback = OfflineFallbackTTSProvider()
            duration = await fallback.generate_speech(text, target_path)

        return target_path, duration

tts_manager = TTSManager()
