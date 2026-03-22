import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

def list_models():
    api_keys = os.getenv("GEMINI_API_KEYS", "").split(",")
    api_keys = [k.strip() for k in api_keys if k.strip()]
    if not api_keys:
        single_key = os.getenv("GEMINI_API_KEY")
        if single_key:
            api_keys = [single_key]
    
    if not api_keys:
        print("No API keys found.")
        return

    genai.configure(api_key=api_keys[0])
    
    print("Available models:")
    try:
        for m in genai.list_models():
            if 'flash' in m.name.lower() and 'generateContent' in m.supported_generation_methods:
                print(f"Name: {m.name}, Display Name: {m.display_name}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_models()
