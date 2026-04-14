import random
from typing import Dict, List, Optional, Set, Tuple


BINGO_LETTERS = "BINGO"


class BingoGame:
    """
    Turn-based Bingo game for 2-8 players.

    Each player gets a private 5×5 card (numbers 1–25, shuffled uniquely).
    Players take turns picking one number from their card.
    The called number is marked on ALL players' cards.
    Completing a row, column, or diagonal earns a BINGO letter (B→I→N→G→O).
    First player to collect all 5 letters wins.
    """

    def __init__(self):
        self.players: Dict[int, str] = {}        # user_id -> display_name
        self.player_ids: List[int] = []           # ordered turn list

        # Each player's card: flat list of 25 unique numbers (1–25), row-major
        self.cards: Dict[int, List[int]] = {}

        # Global set of numbers that have been called so far
        self.called_numbers: Set[int] = set()

        # How many complete lines each player has formed so far
        self.completed_lines: Dict[int, int] = {}

        # Private message IDs (for deleting & re-sending updated cards)
        self.card_message_ids: Dict[int, int] = {}

        # Turn tracking
        self.turn_index: int = 0
        self.current_player_id: Optional[int] = None

        self.game_over: bool = False
        self.winner_id: Optional[int] = None

    # ── Player Management ──────────────────────────────────────────────────────

    def add_player(self, user_id: int, display_name: str) -> None:
        if user_id not in self.players:
            self.players[user_id] = display_name

    def remove_player(self, user_id: int) -> None:
        if user_id in self.players:
            del self.players[user_id]
        if user_id in self.player_ids:
            idx = self.player_ids.index(user_id)
            self.player_ids.remove(user_id)
            if not self.player_ids:
                self.game_over = True
                return
            if idx < self.turn_index:
                self.turn_index -= 1
            if self.turn_index >= len(self.player_ids):
                self.turn_index = 0
            if self.current_player_id == user_id:
                self.current_player_id = self.player_ids[self.turn_index]

    def get_player_count(self) -> int:
        return len(self.players)

    # ── Game Lifecycle ─────────────────────────────────────────────────────────

    def start_game(self) -> bool:
        if len(self.players) < 2:
            return False

        self.player_ids = list(self.players.keys())
        random.shuffle(self.player_ids)

        for pid in self.player_ids:
            numbers = list(range(1, 26))
            random.shuffle(numbers)
            self.cards[pid] = numbers
            self.completed_lines[pid] = 0

        self.turn_index = 0
        self.current_player_id = self.player_ids[0]
        return True

    def get_current_player_id(self) -> Optional[int]:
        return self.current_player_id

    def get_current_player_name(self) -> str:
        if self.current_player_id:
            return self.players.get(self.current_player_id, "Player")
        return "Player"

    # ── Turn Action ───────────────────────────────────────────────────────────

    def call_number(self, user_id: int, number: int) -> Tuple[bool, str]:
        """
        The current player picks a number.
        Returns (success, error_message).  On success error_message is "".
        """
        if self.game_over:
            return False, "The game is already over."
        if user_id != self.current_player_id:
            return False, "It's not your turn!"
        if not (1 <= number <= 25):
            return False, "Invalid number. Must be between 1 and 25."
        if number in self.called_numbers:
            return False, "That number has already been called!"
        # The number must be on the current player's card
        if number not in self.cards.get(user_id, []):
            return False, "That number is not on your card!"

        self.called_numbers.add(number)
        return True, ""

    # ── BINGO Progress ────────────────────────────────────────────────────────

    def _count_complete_lines(self, user_id: int) -> int:
        """Count how many rows, cols, and diagonals are fully marked for a player."""
        card = self.cards.get(user_id)
        if not card:
            return 0

        grid = [card[r * 5:(r + 1) * 5] for r in range(5)]
        count = 0

        # Rows
        for row in grid:
            if all(n in self.called_numbers for n in row):
                count += 1

        # Columns
        for col in range(5):
            if all(grid[r][col] in self.called_numbers for r in range(5)):
                count += 1

        # Main diagonal (top-left → bottom-right)
        if all(grid[i][i] in self.called_numbers for i in range(5)):
            count += 1

        # Anti-diagonal (top-right → bottom-left)
        if all(grid[i][4 - i] in self.called_numbers for i in range(5)):
            count += 1

        return count

    def update_bingo_letters(self, user_id: int) -> List[str]:
        """
        Recalculate completed lines for a player after a number is called.
        Returns a list of newly earned BINGO letters (e.g. ['B', 'I']).
        """
        old = self.completed_lines.get(user_id, 0)
        new = self._count_complete_lines(user_id)
        # Cap at 5 (can't earn more than B-I-N-G-O)
        new = min(new, 5)

        if new > old:
            earned = list(BINGO_LETTERS[old:new])
            self.completed_lines[user_id] = new
            return earned
        return []

    def has_bingo(self, user_id: int) -> bool:
        """True when a player has all 5 BINGO letters."""
        return self.completed_lines.get(user_id, 0) >= 5

    def get_bingo_display(self, user_id: int) -> str:
        """E.g. 'BIN' for 3 letters earned, '—' for 0."""
        count = self.completed_lines.get(user_id, 0)
        return BINGO_LETTERS[:count] if count > 0 else "—"

    # ── Turn Advance ──────────────────────────────────────────────────────────

    def advance_turn(self) -> None:
        if not self.player_ids:
            return
        self.turn_index = (self.turn_index + 1) % len(self.player_ids)
        self.current_player_id = self.player_ids[self.turn_index]

    # ── Card Rendering ────────────────────────────────────────────────────────

    def build_card_keyboard(self, user_id: int, chat_id: int):
        """
        Build the 5×5 InlineKeyboardMarkup for a player's bingo card.

        Called numbers show  🔴  (callback_data='bingo_noop').
        Available numbers show the number; tapping sends
        switch_inline_query=f'bingo_{chat_id} {num}' so the player can
        open an inline picker in the game group and submit the number.
        """
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        card = self.cards.get(user_id, [])
        rows = []
        for r in range(5):
            row_btns = []
            for c in range(5):
                num = card[r * 5 + c]
                if num in self.called_numbers:
                    row_btns.append(
                        InlineKeyboardButton("🔴", callback_data="bingo_noop")
                    )
                else:
                    row_btns.append(
                        InlineKeyboardButton(
                            str(num),
                            switch_inline_query=f"bingo_{chat_id} {num}"
                        )
                    )
            rows.append(row_btns)

        # Bottom row: player's BINGO progress
        letters = self.get_bingo_display(user_id)
        rows.append([
            InlineKeyboardButton(
                f"🎯 {letters}" if letters != "—" else "🎯 —",
                callback_data="bingo_noop"
            )
        ])

        return InlineKeyboardMarkup(rows)

    def build_card_text(self, user_id: int) -> str:
        """Short header for the card private message."""
        name = self.players.get(user_id, "Player")
        letters = self.get_bingo_display(user_id)
        called = len(self.called_numbers)
        return (
            f"🎰 <b>{name}'s Bingo Card</b>\n"
            f"Letters: <b>{letters}</b>  |  Numbers called: <b>{called}</b>\n\n"
            f"Tap a number on your turn to play it in the group! 👇"
        )

    # ── Order Text ────────────────────────────────────────────────────────────

    def get_order_text(self) -> str:
        lines = ["📋 <b>Turn Order:</b>"]
        for i, pid in enumerate(self.player_ids):
            marker = "👉 " if pid == self.current_player_id else f"{i + 1}. "
            letters = self.get_bingo_display(pid)
            lines.append(
                f"{marker}<a href=\"tg://user?id={pid}\">{self.players[pid]}</a>"
                f" — <b>{letters}</b>"
            )
        return "\n".join(lines)
