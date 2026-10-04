import argparse
import os
import sys
import tomllib
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

CONFIG_PATH = Path(__file__).with_name("config.toml")
DEFAULTS = {"language": "English", "level": "intermediate", "model": "gemini-3.8-flash"}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return dict(DEFAULTS)
    with CONFIG_PATH.open("rb") as f:
        try:
            return {**DEFAULTS, **tomllib.load(f)}
        except tomllib.TOMLDecodeError as e:
            sys.exit(f"Error: invalid {CONFIG_PATH.name}: {e}")


def ask_gemini(client: genai.Client, model: str, text: str, language: str, level: str) -> str:
    config = types.GenerateContentConfig(
        system_instruction=(
            f"Always respond in {language}, regardless of the language the user writes in. "
            f"Use vocabulary and grammar suited to a {level} speaker of {language}."
        ),
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    response = client.models.generate_content(model=model, contents=text, config=config)
    return response.text


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
    level = args.level

    if args.text:
        print(ask_gemini(client, model, " ".join(args.text), language, level))
        return

    print(
        f"Chatting with {model} in {language} ({level}). "
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
        if text:
            print(f"\nGemini: {ask_gemini(client, model, text, language, level)}")


if __name__ == "__main__":
    main()
