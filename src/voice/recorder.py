"""
voice/recorder.py
--------------------
Voice input for SnackStack.

Pipeline: record microphone audio with sounddevice -> encode it as a WAV
file with soundfile -> transcribe it to text with OpenAI's Whisper API.

Requirements:
    pip install sounddevice soundfile openai numpy
    (sounddevice also needs the system PortAudio library --
     on Debian/Ubuntu: `sudo apt-get install libportaudio2`;
     on macOS: `brew install portaudio`)

Environment variables:
    OPENAI_API_KEY   - required for transcription
    WHISPER_MODEL    - Whisper model to use (default: "whisper-1")
"""

import os
import sys
import tempfile
from typing import Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import sounddevice as sd
import soundfile as sf
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from a .env file if present

DEFAULT_SAMPLE_RATE = 16000  # Whisper is trained on/expects 16kHz mono audio
DEFAULT_CHANNELS = 1
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "whisper-1")

_client = OpenAI()  # reads OPENAI_API_KEY from the environment automatically


# ---------------------------------------------------------------------------
# Recording
# ---------------------------------------------------------------------------
def record_audio(
    duration: float = 5.0,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    channels: int = DEFAULT_CHANNELS,
) -> np.ndarray:
    """Record a fixed-length clip from the default microphone.

    Args:
        duration: recording length in seconds.
        sample_rate: samples per second.
        channels: 1 for mono (recommended for Whisper), 2 for stereo.

    Returns:
        A float32 numpy array of shape (n_samples, channels).
    """
    print(f"Recording for {duration:.1f}s... speak now.")
    audio = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=channels,
        dtype="float32",
    )
    sd.wait()  # block until the recording finishes
    print("Recording finished.")
    return audio


def record_until_enter(
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    channels: int = DEFAULT_CHANNELS,
) -> np.ndarray:
    """Record from the microphone until the user presses Enter a second
    time, for variable-length voice queries instead of a fixed duration.

    Returns:
        A float32 numpy array of shape (n_samples, channels). Empty if
        nothing was captured.
    """
    input("Press Enter to start recording...")
    print("Recording... press Enter again to stop.")

    frames = []

    def _callback(indata, frame_count, time_info, status):
        if status:
            print(f"Recording status: {status}", file=sys.stderr)
        frames.append(indata.copy())

    with sd.InputStream(
        samplerate=sample_rate,
        channels=channels,
        dtype="float32",
        callback=_callback,
    ):
        input()  # blocks until Enter is pressed again; callback fills `frames`

    print("Recording finished.")
    if not frames:
        return np.zeros((0, channels), dtype="float32")
    return np.concatenate(frames, axis=0)


# ---------------------------------------------------------------------------
# WAV encoding
# ---------------------------------------------------------------------------
def save_wav(audio: np.ndarray, path: str, sample_rate: int = DEFAULT_SAMPLE_RATE) -> str:
    """Encode a numpy audio array to a 16-bit PCM WAV file on disk.

    Returns:
        The path the file was written to (same as the `path` argument).
    """
    sf.write(path, audio, sample_rate, subtype="PCM_16")
    return path


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------
def transcribe_audio(
    path: str,
    model: str = WHISPER_MODEL,
    language: Optional[str] = None,
) -> str:
    """Send a WAV file to OpenAI's Whisper API and return the transcript.

    Args:
        path: path to a WAV (or other Whisper-supported) audio file.
        model: Whisper model name (default: "whisper-1").
        language: optional ISO-639-1 language hint (e.g. "en") to improve
                  accuracy/speed; omit to let Whisper auto-detect.

    Returns:
        The transcribed text.
    """
    with open(path, "rb") as audio_file:
        kwargs = {"model": model, "file": audio_file}
        if language:
            kwargs["language"] = language
        transcript = _client.audio.transcriptions.create(**kwargs)
    return transcript.text


# ---------------------------------------------------------------------------
# Convenience: record + encode + transcribe + clean up, in one call
# ---------------------------------------------------------------------------
def record_and_transcribe(
    duration: Optional[float] = 5.0,
    use_enter_to_stop: bool = False,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    language: Optional[str] = None,
) -> str:
    """Record a voice query and return its transcribed text in one call.

    Records to a temporary WAV file, transcribes it, and deletes the
    temp file afterward regardless of success or failure.

    Args:
        duration: fixed recording length in seconds (ignored if
                  use_enter_to_stop=True).
        use_enter_to_stop: if True, record until Enter is pressed again
                            instead of using a fixed duration.
        sample_rate: recording sample rate (16kHz recommended for Whisper).
        language: optional ISO-639-1 language hint for Whisper.

    Returns:
        The transcribed text, or "" if nothing was recorded.
    """
    if use_enter_to_stop:
        audio = record_until_enter(sample_rate=sample_rate)
    else:
        audio = record_audio(duration=duration, sample_rate=sample_rate)

    if audio.size == 0:
        return ""

    tmp_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name

    try:
        save_wav(audio, tmp_path, sample_rate=sample_rate)
        return transcribe_audio(tmp_path, language=language)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


if __name__ == "__main__":
    # Quick manual smoke test: record 5 seconds, transcribe, print result.
    text = record_and_transcribe(duration=5.0)
    print(f"\nTranscript:\n{text}")