"""
Leaderboard module for persisting and querying player scores using Supabase.
"""
import os
import logging
from typing import Dict, List, Optional, Tuple
from supabase import create_async_client, AsyncClient

logger = logging.getLogger(__name__)

# Supabase configuration from environment
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Create a singleton client
_supabase: Optional[AsyncClient] = None

def get_supabase() -> AsyncClient:
    """Initialize or return the Supabase client."""
    global _supabase
    if _supabase is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            logger.error("SUPABASE_URL or SUPABASE_KEY not found in environment.")
            raise ValueError("Supabase credentials missing.")
        _supabase = create_async_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase

# Game code -> human-readable name mapping
GAME_CODE_NAMES: Dict[str, str] = {
    "1": "Word Unscramble",
    "2": "Story Builder",
    "3": "Guess the Imposter",
    "4": "Guess the Logo",
    "5": "GuessMoji",
    "6": "Guess the Movie",
    "7": "Guess the Flag",
    "8": "Soccer Trivia",
    "9": "General Knowledge",
    "10": "Guess the Character",
    "11": "Word Connect",
    "12": "What You Meme",
    "13": "Taylor vs Shakespeare",
    "14": "The Silent Game",
    "15": "20 Questions",
    "16": "Guess the Song",
    "17": "Crazy 8",
    "18": "Guess the Book",
    "19": "Guess the Marvel",
}

# Games that don't use a standard scoreboard (skip recording)
SKIP_GAME_CODES = {"2"}  # Story Builder has no scores

async def record_game_scores(
    scoreboard: List[Tuple[int, int]],
    game_code: str,
    chat_id: int,
    context,
) -> None:
    """
    Record scores from a completed game into Supabase.
    """
    if game_code in SKIP_GAME_CODES:
        return

    game_name = GAME_CODE_NAMES.get(game_code, f"Game {game_code}")
    supabase = get_supabase()

    for user_id, score in scoreboard:
        if score <= 0:
            continue

        uid_str = str(user_id)

        # Resolve username
        username = "Player"
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            username = member.user.first_name or member.user.username or "Player"
        except Exception as e:
            logger.warning(f"Could not resolve username for {user_id}: {e}")

        try:
            # 1. Upsert player
            # In Supabase/Postgrest, we can use upsert(..., on_conflict='id')
            # But await supabase.table("players").upsert(...) works.
            await supabase.table("players").upsert(
                {"id": uid_str, "username": username},
                on_conflict="id"
            ).execute()

            # 2. Get current game score if exists
            res = await supabase.table("game_scores").select("score").match(
                {"player_id": uid_str, "game_name": game_name}
            ).execute()
            
            existing_score = 0
            if res.data:
                existing_score = res.data[0]["score"]

            # 3. Upsert game score
            new_score = existing_score + score
            await supabase.table("game_scores").upsert(
                {"player_id": uid_str, "game_name": game_name, "score": new_score},
                on_conflict="player_id,game_name"
            ).execute()

            # 4. Update total points in players table
            # We fetch all game scores to get the total sum
            all_scores_res = await supabase.table("game_scores").select("score").match(
                {"player_id": uid_str}
            ).execute()
            
            total_sum = sum(row["score"] for row in all_scores_res.data)
            
            await supabase.table("players").update(
                {"total_score": total_sum}
            ).match({"id": uid_str}).execute()

        except Exception as e:
            logger.error(f"Supabase error recording score for {uid_str}: {e}")

async def get_total_leaderboard(page: int = 1, page_size: int = 10) -> Tuple[List[Tuple[str, str, int]], int, int]:
    """
    Get paginated total leaderboard from Supabase.
    """
    supabase = get_supabase()
    
    try:
        # Get total count
        count_res = await supabase.table("players").select("id", count="exact").execute()
        total_count = count_res.count or 0
        total_pages = max(1, (total_count + page_size - 1) // page_size)
        page = max(1, min(page, total_pages))

        start = (page - 1) * page_size
        end = start + page_size - 1

        # Fetch page
        res = await supabase.table("players").select("id, username, total_score").order("total_score", desc=True).range(start, end).execute()
        
        entries = [
            (row["id"], row["username"], row["total_score"])
            for row in res.data
        ]
        return entries, page, total_pages
    except Exception as e:
        logger.error(f"Supabase error fetching total leaderboard: {e}")
        return [], 1, 1

async def get_game_leaderboard(game_name: str, page: int = 1, page_size: int = 10) -> Tuple[List[Tuple[str, str, int]], int, int]:
    """
    Get paginated leaderboard filtered by game from Supabase.
    """
    supabase = get_supabase()
    
    try:
        # Get count for this game
        count_res = await supabase.table("game_scores").select("player_id", count="exact").match({"game_name": game_name}).execute()
        total_count = count_res.count or 0
        total_pages = max(1, (total_count + page_size - 1) // page_size)
        page = max(1, min(page, total_pages))

        start = (page - 1) * page_size
        end = start + page_size - 1

        # Fetch joined records
        res = await supabase.table("game_scores").select("score, players(username, id)").match({"game_name": game_name}).order("score", desc=True).range(start, end).execute()
        
        entries = []
        for row in res.data:
            player = row.get("players", {})
            entries.append((player.get("id"), player.get("username", "Player"), row["score"]))
            
        return entries, page, total_pages
    except Exception as e:
        logger.error(f"Supabase error fetching game leaderboard for {game_name}: {e}")
        return [], 1, 1

async def get_game_names() -> List[str]:
    """Get list of game names with scores."""
    supabase = get_supabase()
    try:
        res = await supabase.table("game_scores").select("game_name").execute()
        games = {row["game_name"] for row in res.data}
        return sorted(list(games))
    except Exception as e:
        logger.error(f"Supabase error fetching game names: {e}")
        return []
