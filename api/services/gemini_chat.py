import os
import sys
import tomllib
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

from unidecode import unidecode

# textToSpeech.py imports its sibling modules by bare name, so its folder must be on the path.
sys.path.insert(0, str(Path(__file__).parent / "Elevenlabs"))
from speechToText import startRecording  # noqa: E402
from textToSpeech import createAndPlayTextToSpeechMessage  # noqa: E402
from sendMessages import transferMessage  # noqa: E402

load_dotenv()

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.toml"
DEFAULTS = {
    "language": "English",
    "native_language": "English",
    "level": "intermediate",
    "model": "gemini-3.8-flash",
}




class Reply(BaseModel):
    reply: str
    translation: str


LCD_CHARS = 32  # 16x2 character LCD


class TranslationGrade(BaseModel):
    reply: str  # feedback in the target language, spoken aloud
    translation: str  # the same feedback in the user's primary language
    verdict: str  # very short result for the LCD, in the user's primary language
    correct_sentence: str  # in the target language
    correct_sentence_romanized: str  # Latin letters only, for the LCD


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return dict(DEFAULTS)
    with CONFIG_PATH.open("rb") as f:
        try:
            return {**DEFAULTS, **tomllib.load(f)}
        except tomllib.TOMLDecodeError as e:
            sys.exit(f"Error: invalid {CONFIG_PATH.name}: {e}")


def ask_gemini(
    client: genai.Client, model: str, text: str, language: str, native_language: str, level: str
) -> Reply:
    config = types.GenerateContentConfig(
        system_instruction=(
            f"Always write your reply in {language}, regardless of the language the user writes in. "
            f"Use vocabulary and grammar suited to a {level} speaker of {language}. "
            f"Also provide a translation of your reply into {native_language}."
        ),
        response_mime_type="application/json",
        response_schema=Reply,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    response = client.models.generate_content(model=model, contents=text, config=config)
    return response.parsed

# I do not like having to pass all these args into each function but I dont want to deal with making it better. 2 hr left baby
def dictionTest(client,model,text, language, native_language, level):
    reply = ask_gemini(client, model, text, language, native_language, level)
    target_reply = reply.reply  # in the language being learned
    native_reply = reply.translation  # in the user's primary language

    print("Please repeat the message: " + target_reply)
    createAndPlayTextToSpeechMessage(target_reply)
    userAttempt = startRecording()


    fillerWords = ["uh", "um", "bleh", "twah", "bleh"]
    targetSlices = target_reply.split()
    attemptSlices = userAttempt.split()

    #print(targetSlices)
    #print(attemptSlices)

    #Clearing out any punctuation so we are just testing if thier words can be understood
    for item in targetSlices:
        item = item.replace(",", "").replace(".", "").replace("!", "").replace("?", "")
    for item in attemptSlices:
        item = item.replace(",", "").replace(".", "").replace("!", "").replace("?", "")

    targetIterator = 0
    attemptIterator = 0
    correct=0
    total = len(targetSlices)
    incorrectWords = []
    while(targetIterator < len(targetSlices) and attemptIterator < len(attemptSlices)):
        while(attemptSlices[attemptIterator] in fillerWords):
            attemptIterator+=1
        if(targetSlices[targetIterator].lower() != attemptSlices[attemptIterator].lower()):
            incorrectWords.append(targetSlices[targetIterator])
        else:
            correct+=1
        targetIterator+=1
        attemptIterator+=1

    responseText = "The user got " + str((float(correct)/float(total))*100) + "percent of the words correct and they got these words incorrect: "
    for item in incorrectWords:
        responseText + item + ", "
    responseText + "Please give them some appropriate guidance and critiques for thier score mentioning the words they struggled with."
    reply = ask_gemini(client, model, responseText, language, native_language, level)
    target_reply_two = reply.reply  # in the language being learned
    native_reply_two = reply.translation
    createAndPlayTextToSpeechMessage(native_reply_two)


    print("Percentage: " + str((float(correct)/float(total))))
    #print(incorrectWords)


    


def translationTest(client, model, text, language, native_language, level):
    # ask_gemini gives a sentence in the target language plus its translation; the user sees the translation.
    reply = ask_gemini(
        client, model, "Say one short, everyday sentence for me to practice translating.",
        language, native_language, level,
    )
    target_sentence = reply.reply  # in the language being learned
    native_sentence = reply.translation  # in the user's primary language

    print(f"Please translate into {language}: {native_sentence}")
    # Target screen gets an instruction, not the answer; native screen shows what to translate.
    transferMessage(f"Say it in {language}...", unidecode(f"Translate: {native_sentence}"))
    userAttempt = startRecording()
    print(f"You said: {userAttempt}")

    # Translations can be worded many ways, so let Gemini judge instead of matching word by word.
    responseText = (
        f"I was asked to translate \"{native_sentence}\" into {language}. "
        f"One correct translation is \"{target_sentence}\". I said: \"{userAttempt}\"."
    )
    config = types.GenerateContentConfig(
        system_instruction=(
            f"You grade a {level} learner's spoken translation into {language}. Accept any natural, correct "
            "translation and ignore punctuation, since the answer comes from speech recognition.\n"
            f"reply: in {language}, suited to a {level} speaker, say whether they got it right, point out "
            "each specific mistake, and give the corrected sentence.\n"
            f"translation: reply translated into {native_language}.\n"
            f"verdict: at most {LCD_CHARS} characters in {native_language}, e.g. \"Correct!\" or the main "
            "mistake in a few words.\n"
            f"correct_sentence: a correct {language} translation, keeping the learner's wording if it was close.\n"
            "correct_sentence_romanized: correct_sentence in plain Latin letters only (e.g. romaji, or pinyin "
            "without tone marks), using the correct reading of every word."
        ),
        response_mime_type="application/json",
        response_schema=TranslationGrade,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    grade = client.models.generate_content(model=model, contents=responseText, config=config).parsed
    print(f"\n{language}: {grade.reply}")
    print(f"{native_language}: {grade.translation}")

    # Target screen: the correct sentence. Native screen: a short verdict.
    transferMessage(unidecode(grade.correct_sentence_romanized), unidecode(grade.verdict)[:LCD_CHARS])
    createAndPlayTextToSpeechMessage(grade.reply)


def detectSpecialRequests(client,model,text, language, native_language, level):
    translationTriggerWords = ["translate", "translation"]
    for item in translationTriggerWords:
        if(item in text.lower()):
            translationTest(client, model, text, language, native_language, level)
            return True

    dictionTriggerWords = ["pronunciation", "articulation", "inflection", "utterences", "diction"]
    for item in dictionTriggerWords:
        if(item in text.lower()):
            #print("Requested Diction Test")
            dictionTest(client,model,text,language, native_language, level)
            return True

    return False


def main() -> None:
    # Windows consoles default to cp1252, which can't print most non-Latin scripts.
    sys.stdout.reconfigure(encoding="utf-8")

    config = load_config()

    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit("Error: set GEMINI_API_KEY in .env first.")

    client = genai.Client()  # reads GEMINI_API_KEY from .env
    model = config["model"]
    language = config["language"]
    native_language = config["native_language"]
    level = config["level"]

    print(
        f"Chatting with {model} in {language} ({level}). "
        "Press Enter on an empty line to speak, or type a message.\n"
        "Type '/lang <language>' or '/level <level>' to switch, 'exit' to quit."
    )
    while True:
        try:
            text = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if text.lower() in {"exit", "quit"}:
            break
        if text.lower().startswith("/lang"):
            new_language = text[len("/lang"):].strip()
            if new_language:
                language = new_language
                print(f"Response language set to {language}.")
            else:
                print(f"Current language: {language}. Usage: /lang <language>")
            continue
        if text.lower().startswith("/level"):
            new_level = text[len("/level"):].strip()
            if new_level:
                level = new_level
                print(f"Language level set to {level}.")
            else:
                print(f"Current level: {level}. Usage: /level <level>")
            continue
        if not text:
            print("Recording...")
            text = startRecording()
            if(detectSpecialRequests(client, model, text, language, native_language, level)):
                continue
            print(f"You said: {text}")
        if text:
            reply = ask_gemini(client, model, text, language, native_language, level)
            target_reply = reply.reply  # in the language being learned
            native_reply = reply.translation  # in the user's primary language
            print(f"\n{language}: {target_reply}")
            if language.lower() != native_language.lower():
                print(f"{native_language}: {native_reply}")

            transferMessage(unidecode(target_reply), native_reply)
            #print(target_reply)
            createAndPlayTextToSpeechMessage(target_reply)


if __name__ == "__main__":
    main()
