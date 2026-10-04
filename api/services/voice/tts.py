from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

from api.config import settings

VOICE_ID = "Vu9gRjkR23ZG8EWrSmnj"
# Per-language voices. Languages not listed use VOICE_ID.
# "zh": VOICE_ID sounds Cantonese, so Mandarin uses ElevenLabs' stock multilingual voice "Rachel" as a stand-in
# (spoken as Mandarin because the language code is passed). Replace it with a native Mandarin voice id from
# the ElevenLabs voice library for a natural accent.
VOICE_BY_LANGUAGE = {"zh": "21m00Tcm4TlvDq8ikWAM"}
MODEL_ID = "eleven_v4"


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
            speed=max(0.7, min(1.2, speed)),
        ),
    ) as response:
        # The audio is streamed and closes with this block, so read it all before leaving.
        return b"".join(response.data)
