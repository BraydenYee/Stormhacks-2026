import sys
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play
from elevenlabs import VoiceSettings

from api.config import settings
from api.services.elevenlabs.speechToText import startRecording

VOICE_ID = "r1KmysJdVYZjJCm4mL3b"
# The web app speaks every tutor reply, so use the low-latency Flash model.
MODEL_ID = "eleven_flash_v2_5"


def createTextToSpeechAudio(text, speed=1.0):
    """Text to MP3 bytes. `speed` (0.7 to 1.2) lets the app slow the voice down for beginners."""
    client = ElevenLabs(api_key=settings.elevenlabs_api_key)

    with client.text_to_speech.with_raw_response.convert(
        text=text,
        voice_id=VOICE_ID,
        model_id=MODEL_ID,
        voice_settings=VoiceSettings(
        stability=0.0,
        similarity_boost=1.0,
        style=0.0,
        use_speaker_boost=True,
        speed=max(0.7, min(1.2, speed))
    )

    ) as response:
    # Access character cost from headers
        char_cost = response.headers.get("character-cost")
        print(char_cost)
        # The audio is streamed and closes with this block, so read it all before leaving.
        return b"".join(response.data)


def createAndPlayTextToSpeechMessage(text):
    play(createTextToSpeechAudio(text))


def main():
    text = startRecording()
    print(text)

if(__name__ == "__main__"):
    main()
    sys.exit(1)
