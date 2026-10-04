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
    duration = 5
    fs = 48000
    # Live recording needs `import sounddevice as sd` (not installed on the server, so not imported above).
    #recording = (sd.rec(int(duration * fs), samplerate=fs, channels=2, dtype="int16"))
    #sd.wait()

    # Temporary Code So I done need to re record a message every time I test out the api
    recording = None
    with open("AudioBytes", "rb") as file:
        recording = file.read()
        file.close()

    buffer = BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setframerate(fs)
        wf.setnchannels(2)
        wf.setsampwidth(2)
        #wf.writeframes(np.ndarray.tobytes(recording))

        #Temporary. See other comment
        wf.writeframes(recording)
    buffer.seek(0)

    return buffer

def startRecording():
    audioBytesBuffer = getMicrophoneRecording()
    text = getTextFromSpeech(audioBytesBuffer)
    return text
