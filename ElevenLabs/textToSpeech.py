import sys
import os
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play
from dotenv import load_dotenv
import wave
import sounddevice as sd
from io import BytesIO
import numpy as np
import time

def main():

    duration = 2

    fs = 48000

    #print("Starting Recording")
    #recording = np.ndarray.tobytes(sd.rec(int(duration * fs), samplerate=fs, channels=2))
    recording = (sd.rec(int(duration * fs), samplerate=fs, channels=2))
    sd.wait()

    buffer = BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setframerate(fs)
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.writeframes(recording.tobytes())

    buffer.seek(0)

    sd.wait()

    #sd.play(recording, fs)
    #sd.wait()

    #sys.exit(0)

    load_dotenv()
    apiKey = os.getenv("ElevenLabsKey")

    #print("Hello World")

    client = ElevenLabs(api_key=apiKey)

    STTresponse =  client.speech_to_text.convert(
        #file=BytesIO(recording),
        file=buffer,
        model_id="scribe_v2"

    )
    text = ""
    for item in STTresponse:
        print(item)
        #text+=item.text

    print(text)

    with client.text_to_speech.with_raw_response.convert(
        text=text,
        voice_id="r1KmysJdVYZjJCm4mL3b"
    ) as response:
    # Access character cost from headers
        char_cost = response.headers.get("character-cost")
        print(char_cost)
        #play(response.data)


if(__name__ == "__main__"):
    main()
    sys.exit(1)