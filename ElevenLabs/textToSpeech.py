import sys
import os
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play
from dotenv import load_dotenv
from elevenlabs import VoiceSettings
from pathlib import Path
from speechToText import startRecording
import tomllib

CONFIG_PATH = Path(__file__).resolve().parent.parent/"config.toml"
DEFAULTS = {"language": "English", "level": "intermediate", "model": "gemini-3.8-flash"}


languageDict = {
    "afrikaans": "AFR" ,
    "arabic":"ARA",
    "armenian" : "HYE",
    "assamese":"ASM",
    "azerbaijani" : "AZE",
    "belarusian":"BEL" ,
    "bengali": "BEN" ,
    "bosnian":"BOS" ,
    "bulgarian":"BUL",
    "catalan":"CAT" ,
    "cebuano":"CEB" ,
    "chichewa" : "NYA",
    "croatian": "HRV",
    "czech":"CES" ,
    "danish":"DAN" ,
    "dutch":"NLD" ,
    "english": "ENG",
    "estonian": "EST",
    "filipino": "FIL",
    "finnish":"FIN",
    "french":"FRA" ,
    "galician": "GLG",
    "georgian":"KAT" ,
    "german":"DEU" ,
    "greek":"ELL" ,
    "gujarati":"GUJ" ,
    "hausa":"HAU" ,
    "hebrew":"HEB" ,
    "hindi": "HIN",
    "hungarian":"HUN" ,
    "icelandic":"ISL" ,
    "indonesian":"IND" ,
    "irish":"GLE" ,
    "italian": "ITA",
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
    "malay":"MSA" ,
    "malayalam": "MAL",
    "mandarin chinese":"CMN",
    "marathi":"MAR" ,
    "nepali":"NEP" ,
    "norwegian":"NOR" ,
    "pashto":"PUS" ,
    "persian":"FAS" ,
    "polish": "POL",
    "portuguese":"POR" ,
    "punjabi":"PAN" ,
    "romanian": "RON",
    "russian":"RUS" ,
    "serbian":"SRP",
    "sindhi":"SND" ,
    "slovak":"SLK" ,
    "slovenian":"SLV" ,
    "somali":"SOM" ,
    "spanish":"SPA" ,
    "swahili":"SWA",
    "swedish":"SWE",
    "tamil": "TAM",
    "telugu":"TEL" ,
    "thai" : "THA", 
    "turkish" : "TUR",
    "ukrainian" : "UKR", 
    "urdu": "URD", 
    "vietnamese": "VIE",
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
    #print(CONFIG_PATH.resolve(), CONFIG_PATH.exists())
    text = startRecording()

    config = load_config()
    
    lang = languageDict[config["language"].lower()]
    skill = config["level"]

    print(lang)
    print(skill)

    print(text)

if(__name__ == "__main__"):
    main()
    sys.exit(1)