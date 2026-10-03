import os
import sys

from dotenv import load_dotenv
from google import genai

load_dotenv()

MODEL = "gemini-3.8-flash"


def ask_gemini(client: genai.Client, text: str) -> str:
    response = client.models.generate_content(model=MODEL, contents=text)
    return response.text


def main() -> None:
    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit("Error: set GEMINI_API_KEY in .env first.")

    client = genai.Client()  # reads GEMINI_API_KEY from .env

    if len(sys.argv) > 1:
        print(ask_gemini(client, " ".join(sys.argv[1:])))
        return

    print(f"Chatting with {MODEL}. Type 'exit' to quit.")
    while True:
        try:
            text = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if text.lower() in {"exit", "quit"}:
            break
        if text:
            print(f"\nGemini: {ask_gemini(client, text)}")


if __name__ == "__main__":
    main()
