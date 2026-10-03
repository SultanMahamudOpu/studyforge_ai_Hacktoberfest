import os

from elevenlabs.client import ElevenLabs


def text_to_speech(text: str) -> bytes:
    """
    Convert text to MP3 audio using ElevenLabs.
    """

    if not text or not text.strip():
        raise ValueError(
            "Text cannot be empty."
        )

    api_key = os.getenv(
        "ELEVENLABS_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "ELEVENLABS_API_KEY is missing."
        )

    voice_id = os.getenv(
        "ELEVENLABS_VOICE_ID",
        "JBFqnCBsd6RMkjVDRZzb",
    )

    model_id = os.getenv(
        "ELEVENLABS_MODEL_ID",
        "eleven_multilingual_v2",
    )

    try:
        client = ElevenLabs(
            api_key=api_key
        )

        audio = client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id=model_id,
            output_format="mp3_44100_128",
        )

    except Exception as exc:
        raise RuntimeError(
            f"ElevenLabs request failed: {exc}"
        ) from exc

    # Some SDK versions return raw bytes.
    if isinstance(audio, bytes):
        return audio

    # Some versions may return bytearray.
    if isinstance(audio, bytearray):
        return bytes(audio)

    # Current SDK commonly returns an iterable
    # of byte chunks.
    try:
        chunks = []

        for chunk in audio:
            if chunk:
                chunks.append(
                    bytes(chunk)
                )

        result = b"".join(chunks)

    except Exception as exc:
        raise RuntimeError(
            f"Could not process ElevenLabs audio response: {exc}"
        ) from exc

    if not result:
        raise RuntimeError(
            "ElevenLabs returned empty audio."
        )

    return result