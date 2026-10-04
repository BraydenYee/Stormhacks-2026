import os
import sys
import tomllib
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

# textToSpeech.py imports its sibling modules by bare name, so its folder must be on the path.
sys.path.insert(0, str(Path(__file__).parent / "elevenlabs"))
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
            print(f"You said: {text}")
        if text:
            reply = ask_gemini(client, model, text, language, native_language, level)
            target_reply = reply.reply  # in the language being learned
            native_reply = reply.translation  # in the user's primary language
            print(f"\n{language}: {target_reply}")
            if language.lower() != native_language.lower():
                print(f"{native_language}: {native_reply}")

            transferMessage(native_reply, target_reply)

            createAndPlayTextToSpeechMessage(target_reply)


if __name__ == "__main__":
    main()
