import sys
import os
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play
from dotenv import load_dotenv
from elevenlabs import VoiceSettings
from pathlib import Path
from speechToText import startRecording
import tomllib
#import gemini_chat

CONFIG_PATH = Path(__file__).resolve().parent.parent/"config.toml"
DEFAULTS = {"language": "English", "level": "intermediate", "model": "gemini-3.8-flash"}

skillDict = {
    "beginner": 0.75,
    "intermediate": 0.9,
    "advanced": 1.05,
    "native": 1.2

}

languageDict = {
    "afrikaans": "aMNoVX2HjVcetNQmD15D" ,
    "arabic":"hfqsl1OMbiWsgPpht3el",
    "armenian" : "kyqw8ZqDBKvdhEqCx0j9",
    "assamese":"TukQ1ITzWEkA6YPoCkaw",
    "azerbaijani" : "Qc509wi3zyKZuolhdZxn",
    "belarusian":"PTGjIESXmWC6qqTQCQD0" ,
    "bengali": "1JOQMQINvsOLiEu2pZFd" ,
    "bosnian":"uWuA4P0UhkL94Z85GkOz" ,
    "bulgarian":"406EiNlYvqFqcz3vsnOm",
    "catalan":"OCsEi4G5LJzKMSZFmYBD" ,
    "cebuano":"9i8OVlkDTOYoEWt4Cl2l" ,
    "chichewa" : "r6ufuWWwUEBR8qX5v5TD",
    "croatian": "hfqsl1OMbiWsgPpht3el",
    "czech":"hfqsl1OMbiWsgPpht3el" ,
    "danish":"d9playZ0yiaUkVYk3Y0c" ,
    "dutch":"hfqsl1OMbiWsgPpht3el" ,
    "english": "hfqsl1OMbiWsgPpht3el",
    "estonian": "0cuaFlR2we1Gl3woPjeJ",
    "filipino": "MIWz5nzn9F2CYPIedIPx",
    "finnish":"51F2Mt3z6nhTWN1lfYNp",
    "french":"hfqsl1OMbiWsgPpht3el" ,
    "galician": "Pa7DQYCr4mnUUk2JtSmO",
    "georgian":"Pa7DQYCr4mnUUk2JtSmO" ,
    "german":"g1jpii0iyvtRs8fqXsd1" ,
    "greek":"g1jpii0iyvtRs8fqXsd1" ,
    "gujarati":"6dUn0LOxdDTsxwitRcli" ,
    "hausa":"ywXXWsUzt1cKpTQ44qk1" ,
    "hebrew":"uwHajH4FhtzVp6X17pr7" ,
    "hindi": "hfqsl1OMbiWsgPpht3el",
    "hungarian":"hfqsl1OMbiWsgPpht3el" ,
    "icelandic":"hfqsl1OMbiWsgPpht3el" ,
    "indonesian":"hfqsl1OMbiWsgPpht3el" ,
    "irish":"hfqsl1OMbiWsgPpht3el" ,
    "italian": "TukQ1ITzWEkA6YPoCkaw",
    "japanese":"ay2JCCNJ5b2PFAtIaVI3" ,
    "javanese":"hfqsl1OMbiWsgPpht3el" ,
    "kannada":"hfqsl1OMbiWsgPpht3el" ,
    "kazakh":"hfqsl1OMbiWsgPpht3el" ,
    "kirghiz": "hfqsl1OMbiWsgPpht3el" ,
    "korean": "hjCvGtSCRPyjYwe2lDf1",
    "latvian":"hfqsl1OMbiWsgPpht3el" ,
    "lingala":"hfqsl1OMbiWsgPpht3el" ,
    "lithuanian":"hfqsl1OMbiWsgPpht3el" ,
    "luxembourgish":"hfqsl1OMbiWsgPpht3el" ,
    "macedonian":"hfqsl1OMbiWsgPpht3el" ,
    "malay":"hfqsl1OMbiWsgPpht3el" ,
    "malayalam": "hfqsl1OMbiWsgPpht3el",
    "mandarin chinese":"hfqsl1OMbiWsgPpht3el",
    "marathi":"hfqsl1OMbiWsgPpht3el" ,
    "nepali":"hfqsl1OMbiWsgPpht3el" ,
    "norwegian":"hfqsl1OMbiWsgPpht3el" ,
    "pashto":"hfqsl1OMbiWsgPpht3el" ,
    "persian":"hfqsl1OMbiWsgPpht3el" ,
    "polish": "g1jpii0iyvtRs8fqXsd1",
    "portuguese":"hfqsl1OMbiWsgPpht3el" ,
    "punjabi":"hfqsl1OMbiWsgPpht3el" ,
    "romanian": "hfqsl1OMbiWsgPpht3el",
    "russian":"g1jpii0iyvtRs8fqXsd1" ,
    "serbian":"hfqsl1OMbiWsgPpht3el",
    "sindhi":"hfqsl1OMbiWsgPpht3el" ,
    "slovak":"hfqsl1OMbiWsgPpht3el" ,
    "slovenian":"hfqsl1OMbiWsgPpht3el" ,
    "somali":"hfqsl1OMbiWsgPpht3el" ,
    "spanish":"hfqsl1OMbiWsgPpht3el" ,
    "swahili":"hfqsl1OMbiWsgPpht3el",
    "swedish":"g1jpii0iyvtRs8fqXsd1",
    "tamil": "hfqsl1OMbiWsgPpht3el",
    "telugu":"hfqsl1OMbiWsgPpht3el" ,
    "thai" : "hfqsl1OMbiWsgPpht3el",
    "turkish" : "hfqsl1OMbiWsgPpht3el",
    "ukrainian" : "TukQ1ITzWEkA6YPoCkaw",
    "urdu": "hfqsl1OMbiWsgPpht3el",
    "vietnamese": "hfqsl1OMbiWsgPpht3el",
    "welsh" : "hfqsl1OMbiWsgPpht3el"
}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return dict(DEFAULTS)
    with CONFIG_PATH.open("rb") as f:
        try:
            return {**DEFAULTS, **tomllib.load(f)}
        except tomllib.TOMLDecodeError as e:
            sys.exit(f"Error: invalid {CONFIG_PATH.name}: {e}")

# ISO 639-1 codes, so ElevenLabs speaks the chosen language instead of guessing it from the text
# (which is how Mandarin text can come out sounding Cantonese). Languages not listed are auto-detected.
LANGUAGE_CODES = {
    "mandarin chinese": "zh",
    "japanese": "ja",
    "korean": "ko",
    "spanish": "es",
    "french": "fr",
    "german": "de",
    "italian": "it",
    "portuguese": "pt",
    "english": "en",
}


def createAndPlayTextToSpeechMessage(text):
    load_dotenv()
    apiKey = os.getenv("ElevenLabsKey")

    config = load_config()
    
    lang = languageDict[config["language"].lower()]
    skill = config["level"]
    #print(skill)
    #print(skillDict["advanced"])
    client = ElevenLabs(api_key=apiKey)

    with client.text_to_speech.with_raw_response.convert(
        text=text,
        #voice_id="Vu9gRjkR23ZG8EWrSmnj",
        #Added support for different langauges getting a specific speaker for thier language (mostly. Very minor languages get the english speaker
        # because copying over all those voice id's was torture)
        voice_id=languageDict[config["language"].lower()],
        model_id="eleven_v4",
        #voice_id="r1KmysJdVYZjJCm4mL3b",
        language_code=LANGUAGE_CODES.get(config["language"].lower()),
        voice_settings=VoiceSettings(
            stability=0.0,
            similarity_boost=1.0,
            style=0.0,
            use_speaker_boost=True,
            speed=skillDict[skill.lower()]
        )
        
    ) as response:
    # Access character cost from headers
        #char_cost = response.headers.get("character-cost")
        #print(char_cost)
        play(response.data)


def main():
    #print(CONFIG_PATH.resolve(), CONFIG_PATH.exists())
    text = startRecording()
    createAndPlayTextToSpeechMessage(text)

    
    #print(text)

if(__name__ == "__main__"):
    main()
    sys.exit(1)