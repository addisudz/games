import asyncio
from telegram import Bot
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    bot = Bot(token=os.getenv("BOT_TOKEN"))
    sticker_set = await bot.get_sticker_set("DeckofCardsTraditional")
    for i, s in enumerate(sticker_set.stickers):
        print(f"Index {i}: emoji={s.emoji} - file_id={s.file_id}")

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
