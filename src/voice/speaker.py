"""
voice/speaker.py
------------------
Voice output for SnackStack.

Pipeline: send text to OpenAI's TTS API requesting WAV audio -> decode
the returned WAV bytes with soundfile -> play it through the speakers
with sounddevice.

Requirements:
    pip install soundfile sounddevice openai numpy
    (sounddevice also needs the system PortAudio library --
     on Debian/Ubuntu: `sudo apt-get install libportaudio2`;
     on macOS: `brew install portaudio`)

Environment variables:
    OPENAI_API_KEY   - required
    TTS_MODEL        - OpenAI TTS model (default: "tts-1"; "tts-1-hd" for
                        higher quality at higher latency/cost)
    TTS_VOICE        - voice name (default: "alloy"; other built-in
                        options as of this writing: echo, fable, onyx,
                        nova, shimmer)
"""

import io
import os
import sys
from typing import Tuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import sounddevice as sd
import soundfile as sf
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from a .env file if present

TTS_MODEL = os.environ.get("TTS_MODEL", "tts-1")
TTS_VOICE = os.environ.get("TTS_VOICE", "alloy")

_client = OpenAI()  # reads OPENAI_API_KEY from the environment automatically


# ---------------------------------------------------------------------------
# Synthesis (text -> WAV bytes)
# ---------------------------------------------------------------------------
def synthesize_speech(text: str, model: str = TTS_MODEL, voice: str = TTS_VOICE) -> bytes:
    """Request WAV audio from OpenAI's TTS API for the given text.

    Args:
        text: the text to speak.
        model: OpenAI TTS model name.
        voice: OpenAI TTS voice name.

    Returns:
        Raw WAV file bytes.
    """
    if not text or not text.strip():
        raise ValueError("text must be non-empty")

    response = _client.audio.speech.create(
        model=model,
        voice=voice,
        input=text,
        response_format="wav",
    )
    return response.content


# ---------------------------------------------------------------------------
# Decoding (WAV bytes -> numpy audio array)
# ---------------------------------------------------------------------------
def decode_wav_bytes(wav_bytes: bytes) -> Tuple[np.ndarray, int]:
    """Decode in-memory WAV bytes into a numpy audio array with soundfile.

    Returns:
        (audio, sample_rate) where audio is a float32 numpy array (shape
        (n_samples,) for mono or (n_samples, channels) for multi-channel)
        and sample_rate is an int in Hz.
    """
    buffer = io.BytesIO(wav_bytes)
    audio, sample_rate = sf.read(buffer, dtype="float32")
    return audio, sample_rate


# ---------------------------------------------------------------------------
# Playback (numpy audio array -> speakers)
# ---------------------------------------------------------------------------
def play_audio(audio: np.ndarray, sample_rate: int, block: bool = True) -> None:
    """Play a decoded audio array through the default output device.

    Args:
        audio: numpy array as returned by decode_wav_bytes().
        sample_rate: sample rate in Hz matching `audio`.
        block: if True, wait for playback to finish before returning
               (sd.wait()); if False, return immediately and let
               playback continue in the background.
    """
    sd.play(audio, samplerate=sample_rate)
    if block:
        sd.wait()


# ---------------------------------------------------------------------------
# Convenience: synthesize + decode + play, in one call
# ---------------------------------------------------------------------------
def speak(
    text: str,
    model: str = TTS_MODEL,
    voice: str = TTS_VOICE,
    block: bool = True,
) -> None:
    """Speak `text` out loud: TTS request -> decode -> play, in one call.

    Args:
        text: the text to speak.
        model: OpenAI TTS model name.
        voice: OpenAI TTS voice name.
        block: if True (default), this call doesn't return until playback
               finishes; if False, playback continues asynchronously.
    """
    wav_bytes = synthesize_speech(text, model=model, voice=voice)
    audio, sample_rate = decode_wav_bytes(wav_bytes)
    play_audio(audio, sample_rate, block=block)


def save_speech_to_file(
    text: str,
    path: str,
    model: str = TTS_MODEL,
    voice: str = TTS_VOICE,
) -> str:
    """Synthesize speech and save the raw WAV bytes to disk without
    playing it (e.g. to cache a response or ship it to another process).

    Returns:
        The path the file was written to.
    """
    wav_bytes = synthesize_speech(text, model=model, voice=voice)
    with open(path, "wb") as f:
        f.write(wav_bytes)
    return path


if __name__ == "__main__":
    # Quick manual smoke test: synthesize and play a short greeting.
    speak("Hello! Welcome to SnackStack. What would you like to eat today?")
    save_speech_to_file(
        "Hello! Welcome to SnackStack. What would you like to eat today?",
        "greeting.wav"
    )