import argparse
import os
import sys
import tomllib
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

load_dotenv()

# config.toml sits at the project root, shared by this CLI and the web app (api/config.py).
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


def build_system_instruction(language: str, level: str) -> str:
    # The web app's tutor prompt (api/services/llm.py) starts with this same instruction.
    return (
        f"Always respond in {language}, regardless of the language the user writes in. "
        f"Use vocabulary and grammar suited to a {level} speaker of {language}."
    )


def generation_config(**kwargs) -> types.GenerateContentConfig:
    # Shared by the CLI and the web app; automatic function calling is off because no tools are used.
    return types.GenerateContentConfig(
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        **kwargs,
    )


def ask_gemini(
    client: genai.Client, model: str, text: str, language: str, native_language: str, level: str
) -> Reply:
    config = generation_config(
        system_instruction=(
            build_system_instruction(language, level)
            + f" Also provide a translation of your reply into {native_language}."
        ),
        response_mime_type="application/json",
        response_schema=Reply,
    )
    response = client.models.generate_content(model=model, contents=text, config=config)
    return response.parsed


def show_reply(reply: Reply, language: str, native_language: str) -> None:
    # Imported here: it needs the optional ElevenLabs/sounddevice setup, and api.config imports this module.
    from api.services.elevenlabs.textToSpeech import createAndPlayTextToSpeechMessage

    print(f"\n{language}: {reply.reply}")
    if language.lower() != native_language.lower():
        print(f"{native_language}: {reply.translation}")
    createAndPlayTextToSpeechMessage(reply.reply)


def main() -> None:
    # Windows consoles default to cp1252, which can't print most non-Latin scripts.
    sys.stdout.reconfigure(encoding="utf-8")

    config = load_config()

    parser = argparse.ArgumentParser(description="Chat with Gemini.")
    parser.add_argument(
        "-l", "--lang", default=config["language"], help="language for responses (overrides config)"
    )
    parser.add_argument(
        "--level", default=config["level"], help="language level, e.g. beginner (overrides config)"
    )
    parser.add_argument("text", nargs="*", help="one-shot prompt; omit for interactive chat")
    args = parser.parse_args()

    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit("Error: set GEMINI_API_KEY in .env first.")

    client = genai.Client()  # reads GEMINI_API_KEY from .env
    model = config["model"]
    language = args.lang
    native_language = config["native_language"]
    level = args.level

    if args.text:
        show_reply(ask_gemini(client, model, " ".join(args.text), language, native_language, level), language, native_language)
        return

    print(
        f"Chatting with {model} in {language} ({level}). "
        "Press Enter on an empty line to speak, or type a message. "
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
            from api.services.elevenlabs.speechToText import startRecording

            print("Recording...")
            text = startRecording()
            print(f"You said: {text}")
        try:
            show_reply(ask_gemini(client, model, text, language, native_language, level), language, native_language)
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
