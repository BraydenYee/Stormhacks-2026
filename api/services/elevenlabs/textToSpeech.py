import sys
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play
from elevenlabs import VoiceSettings

from api.config import settings
from api.services.elevenlabs.speechToText import startRecording

VOICE_ID = "r1KmysJdVYZjJCm4mL3b"
# Per-language voices. Languages not listed use VOICE_ID.
# "zh": VOICE_ID sounds Cantonese, so Mandarin uses ElevenLabs' stock multilingual voice "Rachel" as a stand-in
# (spoken as Mandarin because the language code is passed). Replace it with a native Mandarin voice id from
# the ElevenLabs voice library for a natural accent.
VOICE_BY_LANGUAGE = {"zh": "21m00Tcm4TlvDq8ikWAM"}
# The web app speaks every tutor reply, so use the low-latency Flash model.
MODEL_ID = "eleven_flash_v2_5"


def createTextToSpeechAudio(text, speed=1.0, language=None):
    """Text to MP3 bytes. `speed` (0.7 to 1.2) lets the app slow the voice down for beginners.

    `language` is an ISO 639-1 code like "zh" or "ja". Passing it makes ElevenLabs speak that language
    instead of guessing it from the text (which is how Mandarin text can come out in the wrong dialect).
    """
    client = ElevenLabs(api_key=settings.elevenlabs_api_key)

    with client.text_to_speech.with_raw_response.convert(
        text=text,
        voice_id=VOICE_BY_LANGUAGE.get(language, VOICE_ID),
        model_id=MODEL_ID,
        language_code=language,
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
