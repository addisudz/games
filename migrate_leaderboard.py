import os
import json
import asyncio
from dotenv import load_dotenv
from supabase import create_async_client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
DATA_FILE = "leaderboard_data.json"

async def migrate():
    if not os.path.exists(DATA_FILE):
        print(f"File {DATA_FILE} not found. Nothing to migrate.")
        return

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("SUPABASE_URL or SUPABASE_KEY missing in .env")
        return

    print(f"Connecting to {SUPABASE_URL}...")
    supabase = create_async_client(SUPABASE_URL, SUPABASE_KEY)

    print(f"Loading {DATA_FILE}...")
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    players = data.get("players", {})
    total_players = len(players)
    print(f"Found {total_players} players. Starting migration...")

    for i, (uid_str, info) in enumerate(players.items(), 1):
        username = info.get("username", "Player")
        total_score = info.get("total", 0)
        game_scores = info.get("games", {})

        print(f"[{i}/{total_players}] Migrating {username} ({uid_str})...")

        try:
            # 1. Upsert player
            await supabase.table("players").upsert(
                {"id": uid_str, "username": username, "total_score": total_score},
                on_conflict="id"
            ).execute()

            # 2. Upsert game scores
            for game_name, score in game_scores.items():
                if score <= 0:
                    continue
                await supabase.table("game_scores").upsert(
                    {"player_id": uid_str, "game_name": game_name, "score": score},
                    on_conflict="player_id,game_name"
                ).execute()
        except Exception as e:
            print(f"Error migrating {username}: {e}")

    print("Migration complete!")

if __name__ == "__main__":
    asyncio.run(migrate())
