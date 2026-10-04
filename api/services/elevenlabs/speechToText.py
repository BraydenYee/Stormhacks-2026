import wave
from io import BytesIO

from elevenlabs.client import ElevenLabs

from api.config import settings

MODEL_ID = "scribe_v2"


def getTranscript(file):
    """Speech to text. `file` is a file-like object, or a (filename, bytes, content_type) tuple.

    Returns {"text", "language_code", "words": [{"text", "start", "end", "type", ...}]}. The web app
    uses the word timings to measure speaking rate and pauses.
    """
    client = ElevenLabs(api_key=settings.elevenlabs_api_key)
    STTresponse = client.speech_to_text.convert(
        file=file,
        model_id=MODEL_ID
    )
    return {
        "text": (STTresponse.text or "").strip(),
        "language_code": STTresponse.language_code,
        "words": [word.model_dump() for word in (STTresponse.words or [])],
    }


def getTextFromSpeech(buffer):
    text = getTranscript(buffer)["text"]
    if(text == ""):
        return "Something has gone wrong with the system. Please Try Again"

    print(text)
    return text


def getMicrophoneRecording():
    # Imported here: the web server doesn't install sounddevice, only the CLI needs it.
    import numpy as np
    import sounddevice as sd

    duration = 10
    fs = 48000
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=2, dtype="int16")
    sd.wait()

    buffer = BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setframerate(fs)
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.writeframes(np.ndarray.tobytes(recording))
    buffer.seek(0)

    return buffer


def startRecording():
    audioBytesBuffer = getMicrophoneRecording()
    text = getTextFromSpeech(audioBytesBuffer)
    return text
