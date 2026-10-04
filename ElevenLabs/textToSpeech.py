import sys
import os
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play
from dotenv import load_dotenv
import sounddevice as sd
from io import BytesIO
import numpy as np
import time
from elevenlabs import VoiceSettings

from speechToText import startRecording

def createAndPlayTextToSpeechMessage(text):
    load_dotenv()
    apiKey = os.getenv("ElevenLabsKey")

    client = ElevenLabs(api_key=apiKey)

    with client.text_to_speech.with_raw_response.convert(
        text=text,
        voice_id="r1KmysJdVYZjJCm4mL3b",
        voice_settings=VoiceSettings(
        stability=0.0,
        similarity_boost=1.0,
        style=0.0,
        use_speaker_boost=True,
        speed=1.0  
    )
        
    ) as response:
    # Access character cost from headers
        char_cost = response.headers.get("character-cost")
        print(char_cost)
        play(response.data)


def main():
    text = startRecording()
    print(text)

if(__name__ == "__main__"):
    main()
    sys.exit(1)