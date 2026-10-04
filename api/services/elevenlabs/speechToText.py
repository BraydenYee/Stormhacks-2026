import sys
import os
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play
from dotenv import load_dotenv
import wave
import sounddevice as sd
from sounddevice import InputStream
import numpy as np
from io import BytesIO
from elevenlabs import VoiceSettings
from pathlib import Path
import tomllib
import threading
import signal



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

CONFIG_PATH = Path(__file__).resolve().parent.parent/"config.toml"
DEFAULTS = {"language": "English", "level": "intermediate", "model": "gemini-3.8-flash"}

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return dict(DEFAULTS)
    with CONFIG_PATH.open("rb") as f:
        try:
            return {**DEFAULTS, **tomllib.load(f)}
        except tomllib.TOMLDecodeError as e:
            sys.exit(f"Error: invalid {CONFIG_PATH.name}: {e}")


def getTextFromSpeech(buffer):
    load_dotenv()
    apiKey = os.getenv("ElevenLabsKey")

    config = load_config()
        
    lang = languageDict[config["language"].lower()]
    skill = config["level"]

    client = ElevenLabs(api_key=apiKey)
    STTresponse =  client.speech_to_text.convert(
        file=buffer,
        #language_code=lang,
        model_id="scribe_v2"
    )
    text = ""
    for item in STTresponse:
        if(item[0] == "text"):
            text = item[1]
            break
    if(text == ""):
        return "Something has gone wrong with the system. Please Try Again"

    #print(text)
    return text


def getMicrophoneRecording():
    duration = 10
    fs = 48000

    

    chunks = []
    #for i in range(0, 2):
    stopEvent = threading.Event()

    def callback(inData, frames, time, status):
            if status:
                print(status)
            #print(frames)
            #print(inData)
            chunks.append(inData.copy())
    def handle_signal(signum, frame):
        #if(not stopEvent.is_set):
        stopEvent.set()

    signal.signal(signal.SIGINT, handle_signal)

    #print("Waiting on the first stop event")
    #stopEvent.wait()
    print("Recording")
    stopEvent.clear()
    
    with InputStream(samplerate=fs, channels=2, dtype="int16", callback=callback, blocksize=1024) as stream:
        stopEvent.wait()
    #print(i)
    #sys.exit(0)
    recording = np.concatenate(chunks)
    #recording = (sd.rec(int(duration * fs), samplerate=fs, channels=2, dtype="int16"))
    #sd.wait()

    # Temporary Code So I done need to re record a message every time I test out the api
    #recording = None
    #with open("AudioBytes", "rb") as file:
    #    recording = file.read()
    #    file.close()

    buffer = BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setframerate(fs)
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.writeframes(np.ndarray.tobytes(recording))

        #Temporary. See other comment
        #wf.writeframes(recording)
    buffer.seek(0)

    return buffer

def startRecording():
    audioBytesBuffer = getMicrophoneRecording()
    text = getTextFromSpeech(audioBytesBuffer)
    return text