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

# languageDict = {
#     "afrikaans": "AFR" ,
#     "arabic":""ARA"",
#     "armenian" : "HYE",
#     "assamese":"ASM",
#     "azerbaijani" : "AZE",
#     "belarusian":"BEL" ,
#     "bengali": "BEN" ,
#     "bosnian":"BOS" ,
#     "bulgarian":"BUL",
#     "catalan":"CAT" ,
#     "cebuano":"CEB" ,
#     "chichewa" : "NYA",
#     "croatian": "HRV",
#     "czech":"CES" ,
#     "danish":"DAN" ,
#     "dutch":"NLD" ,
#     "english": "ENG",
#     "estonian": "EST",
#     "filipino": "FIL",
#     "finnish":"FIN",
#     "french":"FRA" ,
#     "galician": "GLG",
#     "georgian":"KAT" ,
#     "german":"DEU" ,
#     "greek":"ELL" ,
#     "gujarati":"GUJ" ,
#     "hausa":"HAU" ,
#     "hebrew":"HEB" ,
#     "hindi": "HIN",
#     "hungarian":"HUN" ,
#     "icelandic":"ISL" ,
#     "indonesian":"IND" ,
#     "irish":"GLE" ,
#     "italian": "ITA",
#     "japanese":"JPN" ,
#     "javanese":"JAV" ,
#     "kannada":"KAN" ,
#     "kazakh":"KAZ" ,
#     "kirghiz": "KIR" ,
#     "korean": "KOR",
#     "latvian":"LAV" ,
#     "lingala":"LIN" ,
#     "lithuanian":"LIT" ,
#     "luxembourgish":"LTZ" ,
#     "macedonian":"MKD" ,
#     "malay":"MSA" ,
#     "malayalam": "MAL",
#     "mandarin chinese":"CMN",
#     "marathi":"MAR" ,
#     "nepali":"NEP" ,
#     "norwegian":"NOR" ,
#     "pashto":"PUS" ,
#     "persian":"FAS" ,
#     "polish": "POL",
#     "portuguese":"POR" ,
#     "punjabi":"PAN" ,
#     "romanian": "RON",
#     "russian":"RUS" ,
#     "serbian":"SRP",
#     "sindhi":"SND" ,
#     "slovak":"SLK" ,
#     "slovenian":"SLV" ,
#     "somali":"SOM" ,
#     "spanish":"SPA" ,
#     "swahili":"SWA",
#     "swedish":"SWE",
#     "tamil": "TAM",
#     "telugu":"TEL" ,
#     "thai" : "THA", 
#     "turkish" : "TUR",
#     "ukrainian" : "UKR", 
#     "urdu": "URD", 
#     "vietnamese": "VIE",
#     "welsh" : "CYM" 
# }

languageDict = {
    "afrikaans": "aMNoVX2HjVcetNQmD15D" ,
    "arabic":"hfqsl1OMbiWsgPpht3el",
    "armenian" : "kyqw8ZqDBKvdhEqCx0j9",
    "assamese":"TukQ1ITzWEkA6YPoCkaw",
    "azerbaijani" : "Qc509wi3zyKZuolhdZxn",
    "belarusian":"BEL" ,
    "bengali": "BEN" ,
    "bosnian":"BOS" ,
    "bulgarian":"BUL",
    "catalan":"CAT" ,
    "cebuano":"CEB" ,
    "chichewa" : "NYA",
    "croatian": "hfqsl1OMbiWsgPpht3el",
    "czech":"hfqsl1OMbiWsgPpht3el" ,
    "danish":"DAN" ,
    "dutch":"hfqsl1OMbiWsgPpht3el" ,
    "english": "hfqsl1OMbiWsgPpht3el",
    "estonian": "EST",
    "filipino": "FIL",
    "finnish":"FIN",
    "french":"hfqsl1OMbiWsgPpht3el" ,
    "galician": "GLG",
    "georgian":"KAT" ,
    "german":"g1jpii0iyvtRs8fqXsd1" ,
    "greek":"g1jpii0iyvtRs8fqXsd1" ,
    "gujarati":"GUJ" ,
    "hausa":"HAU" ,
    "hebrew":"HEB" ,
    "hindi": "hfqsl1OMbiWsgPpht3el",
    "hungarian":"HUN" ,
    "icelandic":"ISL" ,
    "indonesian":"hfqsl1OMbiWsgPpht3el" ,
    "irish":"GLE" ,
    "italian": "TukQ1ITzWEkA6YPoCkaw",
    "japanese":"JPN" ,
    "javanese":"JAV" ,
    "kannada":"KAN" ,
    "kazakh":"KAZ" ,
    "kirghiz": "KIR" ,
    "korean": "KOR",
    "latvian":"LAV" ,
    "lingala":"LIN" ,
    "lithuanian":"LIT" ,
    "luxembourgish":"LTZ" ,
    "macedonian":"MKD" ,
    "malay":"hfqsl1OMbiWsgPpht3el" ,
    "malayalam": "MAL",
    "mandarin chinese":"hfqsl1OMbiWsgPpht3el",
    "marathi":"MAR" ,
    "nepali":"NEP" ,
    "norwegian":"hfqsl1OMbiWsgPpht3el" ,
    "pashto":"PUS" ,
    "persian":"FAS" ,
    "polish": "g1jpii0iyvtRs8fqXsd1",
    "portuguese":"hfqsl1OMbiWsgPpht3el" ,
    "punjabi":"PAN" ,
    "romanian": "hfqsl1OMbiWsgPpht3el",
    "russian":"g1jpii0iyvtRs8fqXsd1" ,
    "serbian":"SRP",
    "sindhi":"SND" ,
    "slovak":"SLK" ,
    "slovenian":"SLV" ,
    "somali":"SOM" ,
    "spanish":"hfqsl1OMbiWsgPpht3el" ,
    "swahili":"SWA",
    "swedish":"g1jpii0iyvtRs8fqXsd1",
    "tamil": "hfqsl1OMbiWsgPpht3el",
    "telugu":"TEL" ,
    "thai" : "THA", 
    "turkish" : "hfqsl1OMbiWsgPpht3el",
    "ukrainian" : "TukQ1ITzWEkA6YPoCkaw", 
    "urdu": "URD", 
    "vietnamese": "hfqsl1OMbiWsgPpht3el",
    "welsh" : "CYM" 
}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return dict(DEFAULTS)
    with CONFIG_PATH.open("rb") as f:
        try:
            return {**DEFAULTS, **tomllib.load(f)}
        except tomllib.TOMLDecodeError as e:
            sys.exit(f"Error: invalid {CONFIG_PATH.name}: {e}")

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
        voice_id="Vu9gRjkR23ZG8EWrSmnj",
        model_id="eleven_v4",
        #voice_id="r1KmysJdVYZjJCm4mL3b",
        #language_code=lang.lower(),
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