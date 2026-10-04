from elevenlabs.client import ElevenLabs

from api.config import settings

MODEL_ID = "scribe_v2"


def getTranscript(file):
    """Speech to text. `file` is a file-like object, or a (filename, bytes, content_type) tuple.

    Returns {"text", "language_code", "words": [{"text", "start", "end", "type", ...}]}. The web app
    uses the word timings to measure speaking rate and pauses.
    """
    client = ElevenLabs(api_key=settings.elevenlabs_api_key)
    response = client.speech_to_text.convert(file=file, model_id=MODEL_ID)
    return {
        "text": (response.text or "").strip(),
        "language_code": response.language_code,
        "words": [word.model_dump() for word in (response.words or [])],
    }
