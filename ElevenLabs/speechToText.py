import sys
import os
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play
from dotenv import load_dotenv
import wave
import sounddevice as sd
from io import BytesIO
from elevenlabs import VoiceSettings

def getTextFromSpeech(buffer):
    load_dotenv()
    apiKey = os.getenv("ElevenLabsKey")

    client = ElevenLabs(api_key=apiKey)
    STTresponse =  client.speech_to_text.convert(
        file=buffer,
        model_id="scribe_v2"
    )
    text = ""
    for item in STTresponse:
        if(item[0] == "text"):
            text = item[1]
            break
    if(text == ""):
        return "Something has gone wrong with the system. Please Try Again"

    print(text)
    return text


def getMicrophoneRecording():
    duration = 5
    fs = 48000
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

