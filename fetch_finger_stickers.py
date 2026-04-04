import asyncio
import os
import json
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

async def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ BOT_TOKEN not found in .env file!")
        return
        
    bot = Bot(token=token)
    pack_name = "twinkhands"
    
    try:
        sticker_set = await bot.get_sticker_set(pack_name)
        print(f"✅ Found sticker pack: {sticker_set.title} ({len(sticker_set.stickers)} stickers)")
        
        finger_stickers = {}
        for i, s in enumerate(sticker_set.stickers):
            # We assume the order is 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0
            # but we'll print them all so the user can verify.
            print(f"Index {i}: emoji={s.emoji} - file_id={s.file_id}")
            finger_stickers[f"finger_{i}"] = s.file_id
            
        # Also print a JSON snippet for easy copying
        print("\n--- JSON Snippet for sticker_cache.json ---")
        print(json.dumps({"twinkhands": finger_stickers}, indent=2))
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
