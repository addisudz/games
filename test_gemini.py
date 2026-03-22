import asyncio
import os
from dotenv import load_dotenv
from gemini_ai import gemini_bot

load_dotenv()

async def test_gemini():
    print("Testing Gemini Savage Bot...")
    
    # Check if keys are loaded
    print(f"Loaded keys: {len(gemini_bot.api_keys)}")
    if not gemini_bot.api_keys:
        print("Error: No API keys found! Add GEMINI_API_KEYS=key1,key2 to .env")
        return

    test_message = "You are a very slow bot."
    print(f"User: {test_message}")
    
    response = await gemini_bot.get_savage_response(test_message)
    print(f"Bot: {response}")

if __name__ == "__main__":
    asyncio.run(test_gemini())
