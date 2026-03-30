import random
from typing import List, Dict, Optional, Tuple, Set
from itertools import combinations


class RummyCard:
    RANKS = ['ace', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'jack', 'queen', 'king']
    SUITS = ['clubs', 'diamonds', 'hearts', 'spades']

    RANK_VALUES = {
        'ace': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7,
        '8': 8, '9': 9, '10': 10, 'jack': 11, 'queen': 12, 'king': 13
    }

    def __init__(self, rank: str, suit: str):
        self.rank = rank
        self.suit = suit
        self.rank_value = self.RANK_VALUES[rank]
        self.filename = f"{rank}_of_{suit}.png"

    def __str__(self):
        return f"{self.rank.capitalize()} of {self.suit.capitalize()}"

    def __repr__(self):
        return f"RummyCard({self.rank}, {self.suit})"

    def __eq__(self, other):
        if not isinstance(other, RummyCard):
            return False
        return self.rank == other.rank and self.suit == other.suit

    def __hash__(self):
        return hash((self.rank, self.suit))

    @property
    def sticker_key(self) -> str:
        """Key used to look up normal sticker in cache."""
        return f"{self.rank}_of_{self.suit}"

    @property
    def dark_sticker_key(self) -> str:
        """Key used to look up blackened sticker in cache."""
        return f"{self.rank}_of_{self.suit}_dark"


class RummyGame:
    """
    Turn-based Rummy game for 2-6 players.

    Custom win condition: a player must form exactly
    - Two 3-card consecutive same-suit runs, AND
    - One 4-card consecutive same-suit run
    = 10 cards total

    Turns:
        1. Draw from deck (send 'draw' sticker) OR grab top discard (send 'grab' sticker)
        2. Play cards if desired (handled implicitly through hand checks)
        3. Discard one card (send the card sticker) to end turn

    Player receives:
        - 2 players: 10 cards each
        - 3-4 players: 7 cards each
        - 5-6 players: 6 cards each
    """

    CARDS_PER_PLAYER = {2: 10, 3: 7, 4: 7, 5: 6, 6: 6}

    def __init__(self):
        self.players: Dict[int, str] = {}          # user_id -> display_name
        self.player_ids: List[int] = []             # ordered turn list
        self.hands: Dict[int, List[RummyCard]] = {} # user_id -> cards
        self.locked_melds: Dict[int, List[List[RummyCard]]] = {} # user_id -> list of melds

        self.deck: List[RummyCard] = []
        self.discard_pile: List[RummyCard] = []

        self.turn_index: int = 0
        self.current_player_id: Optional[int] = None

        # Phase per player: 'draw' or 'discard'
        # After joining turn starts in 'draw' phase — player must draw/grab first
        self.player_phase: Dict[int, str] = {}  # user_id -> 'draw' | 'discard'

        self.game_over: bool = False
        self.winner_id: Optional[int] = None

    # ── Player Management ──────────────────────────────────────────────────────

    def add_player(self, user_id: int, display_name: str) -> None:
        if user_id not in self.players:
            self.players[user_id] = display_name
            self.hands[user_id] = []
            self.locked_melds[user_id] = []

    def remove_player(self, user_id: int) -> None:
        if user_id in self.players:
            del self.players[user_id]
        if user_id in self.hands:
            self.discard_pile.extend(self.hands.pop(user_id))
        if user_id in self.locked_melds:
            for meld in self.locked_melds.pop(user_id):
                self.discard_pile.extend(meld)
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

    # ── Deck ──────────────────────────────────────────────────────────────────

    def _build_deck(self) -> List[RummyCard]:
        deck = [RummyCard(r, s) for s in RummyCard.SUITS for r in RummyCard.RANKS]
        random.shuffle(deck)
        return deck

    def _draw_from_deck(self) -> Optional[RummyCard]:
        """Draw from stock; reshuffle discard if needed (keep top card)."""
        if not self.deck:
            if len(self.discard_pile) > 1:
                top = self.discard_pile.pop()
                self.deck = self.discard_pile[:]
                random.shuffle(self.deck)
                self.discard_pile = [top]
            else:
                return None
        return self.deck.pop() if self.deck else None

    # ── Game Lifecycle ─────────────────────────────────────────────────────────

    def start_game(self) -> bool:
        n = len(self.players)
        if n < 2 or n > 6:
            return False

        self.deck = self._build_deck()
        self.player_ids = list(self.players.keys())
        random.shuffle(self.player_ids)

        cards_each = self.CARDS_PER_PLAYER[n]
        for pid in self.player_ids:
            self.hands[pid] = [self.deck.pop() for _ in range(cards_each)]

        # Flip starting discard card
        starting = self.deck.pop()
        self.discard_pile = [starting]

        self.turn_index = 0
        self.current_player_id = self.player_ids[0]
        self.player_phase = {pid: 'draw' for pid in self.player_ids}

        return True

    def get_top_discard(self) -> Optional[RummyCard]:
        if self.discard_pile:
            return self.discard_pile[-1]
        return None

    # ── Turn Actions ───────────────────────────────────────────────────────────

    def draw_from_deck(self, user_id: int) -> Tuple[bool, str, Optional[RummyCard]]:
        """
        Player draws from the stock pile.
        Returns (success, message, drawn_card)
        """
        if self.game_over:
            return False, "The game is over.", None
        if user_id != self.current_player_id:
            return False, "It's not your turn!", None
        if self.player_phase.get(user_id) != 'draw':
            return False, "You must discard a card first.", None

        card = self._draw_from_deck()
        if not card:
            return False, "The deck is empty!", None

        self.hands[user_id].append(card)
        self.player_phase[user_id] = 'discard'
        return True, f"You drew a card.", card

    def grab_from_discard(self, user_id: int) -> Tuple[bool, str, Optional[RummyCard]]:
        """
        Player takes the top card from the discard pile.
        Returns (success, message, grabbed_card)
        """
        if self.game_over:
            return False, "The game is over.", None
        if user_id != self.current_player_id:
            return False, "It's not your turn!", None
        if self.player_phase.get(user_id) != 'draw':
            return False, "You must discard a card first.", None

        top = self.get_top_discard()
        if not top:
            return False, "The discard pile is empty!", None

        self.discard_pile.pop()
        self.hands[user_id].append(top)
        self.player_phase[user_id] = 'discard'
        return True, f"You grabbed {str(top)} from the discard pile.", top

    def discard_card(self, user_id: int, card_key: str) -> Tuple[bool, str, Optional[RummyCard], bool]:
        """
        Player discards a card, ending their turn.
        card_key: '{rank}_of_{suit}' (e.g. 'ace_of_spades')
        Returns (success, message, discarded_card, game_won)
        """
        if self.game_over:
            return False, "The game is over.", None, False
        if user_id != self.current_player_id:
            return False, "Not your turn!", None, False
        if self.player_phase.get(user_id) != 'discard':
            return False, "Draw or grab a card first!", None, False

        # Parse card_key -> find in hand
        card = self._find_card_in_hand(user_id, card_key)
        if not card:
            return False, "You don't have that card.", None, False

        self.hands[user_id].remove(card)
        self.discard_pile.append(card)

        # Check win
        if self.check_win(user_id):
            self.game_over = True
            self.winner_id = user_id
            return True, f"🏆 {self.players[user_id]} wins!", card, True

        # Advance turn
        self._advance_turn()
        return True, f"{self.players[user_id]} discarded {str(card)}.", card, False

    def _find_card_in_hand(self, user_id: int, card_key: str) -> Optional[RummyCard]:
        """Find a card in player's hand by its sticker key '{rank}_of_{suit}'."""
        # card_key may be e.g. "ace_of_spades" or "ace of spades"
        key = card_key.lower().replace(' ', '_')
        for card in self.hands.get(user_id, []):
            if card.sticker_key == key:
                return card
        return None

    def _advance_turn(self):
        if not self.player_ids:
            return
        self.turn_index = (self.turn_index + 1) % len(self.player_ids)
        self.current_player_id = self.player_ids[self.turn_index]
        self.player_phase[self.current_player_id] = 'draw'

    # ── Locking ───────────────────────────────────────────────────────────────

    def get_valid_melds(self, user_id: int, length: int) -> List[List[RummyCard]]:
        """Return all valid melds (Runs or Sets) of given length in player's hand."""
        return self._find_all_melds(self.hands.get(user_id, []), length)

    def lock_meld(self, user_id: int, keys: List[str]) -> Tuple[bool, str, bool]:
        """Lock exactly these cards by sticker_key. Returns (success, msg, won)."""
        hand = self.hands.get(user_id, [])
        cards_to_lock = []
        for key in keys:
            found = False
            for c in hand:
                if c.sticker_key == key and c not in cards_to_lock:
                    cards_to_lock.append(c)
                    found = True
                    break
            if not found:
                return False, f"Missing card {key} in hand.", False
                
        # Validate that these cards form a meld
        # Just to be safe, find if it's within _find_all_melds
        melds = self._find_all_melds(cards_to_lock, len(keys))
        if not melds:
            return False, "Those cards do not form a valid meld.", False
            
        for c in cards_to_lock:
            hand.remove(c)
        self.locked_melds.setdefault(user_id, []).append(cards_to_lock)
        
        # Check if this lock triggers a win
        if self.check_win(user_id):
            self.game_over = True
            self.winner_id = user_id
            return True, "Cards locked successfully.", True
            
        return True, "Cards locked successfully.", False

    def unlock_meld(self, user_id: int, length: int) -> Tuple[bool, str]:
        """Unlock the most recently locked meld of length `length`."""
        melds = self.locked_melds.get(user_id, [])
        for i in range(len(melds) - 1, -1, -1):
            if len(melds[i]) == length:
                extracted = melds.pop(i)
                self.hands.get(user_id, []).extend(extracted)
                return True, f"Unlocked a {length}-card set."
        return False, f"No locked {length}-card meld found."

    # ── Win Condition ─────────────────────────────────────────────────────────

    def check_win(self, user_id: int) -> bool:
        """
        Win condition: hand must contain exactly
          - Two 3-card consecutive same-suit runs
          - One 4-card consecutive same-suit run
        Total = 10 cards.
        """
        hand = self.hands.get(user_id, [])
        all_cards = hand[:]
        for m in self.locked_melds.get(user_id, []):
            all_cards.extend(m)
            
        if len(all_cards) != 10:
            return False
        return self._find_winning_arrangement(all_cards)

    def _find_winning_arrangement(self, hand: List[RummyCard]) -> bool:
        """
        Try all combinations of cards to find two 3-runs and one 4-run.
        Returns True if a valid arrangement exists.
        """
        # Get all valid runs in hand
        runs_3 = self._find_all_melds(hand, length=3)
        runs_4 = self._find_all_melds(hand, length=4)

        # Try every combination: 1 run of 4 + 2 runs of 3
        for r4 in runs_4:
            r4_set = set(id(c) for c in r4)
            remaining_after_4 = [c for c in hand if id(c) not in r4_set]

            # Now try 2 runs of 3 from remaining 6 cards
            runs_3_in_remaining = self._find_all_melds(remaining_after_4, length=3)
            for r3a in runs_3_in_remaining:
                r3a_set = set(id(c) for c in r3a)
                remaining_after_3a = [c for c in remaining_after_4 if id(c) not in r3a_set]
                runs_3b = self._find_all_melds(remaining_after_3a, length=3)
                if runs_3b:
                    # Found a valid winning arrangement
                    return True
        return False

    def _find_all_melds(self, cards: List[RummyCard], length: int) -> List[List[RummyCard]]:
        """
        Find all groups of `length` valid melds (runs or sets) within `cards`.
        A run: same suit, consecutive rank values (ace=1 low only).
        A set: same rank, different suits.
        Returns list of valid melds (each meld is a list of cards).
        """
        melds = []
        
        # 1. Group by suit to find Runs
        by_suit: Dict[str, List[RummyCard]] = {}
        for c in cards:
            by_suit.setdefault(c.suit, []).append(c)

        for suit, suit_cards in by_suit.items():
            if len(suit_cards) >= length:
                for combo in combinations(suit_cards, length):
                    values = sorted(c.rank_value for c in combo)
                    if values == list(range(values[0], values[0] + length)):
                        melds.append(list(combo))
                        
        # 2. Group by rank to find Sets
        by_rank: Dict[str, List[RummyCard]] = {}
        for c in cards:
            by_rank.setdefault(c.rank, []).append(c)
            
        for rank, rank_cards in by_rank.items():
            if len(rank_cards) >= length:
                for combo in combinations(rank_cards, length):
                    # In standard deck, 3 or 4 cards of same rank are naturally different suits.
                    melds.append(list(combo))
                    
        return melds

    # ── Info ──────────────────────────────────────────────────────────────────

    def get_player_order_text(self) -> str:
        """Return formatted text showing play order and card counts."""
        lines = ["📋 <b>Play Order &amp; Card Counts:</b>"]
        for i, pid in enumerate(self.player_ids):
            marker = "👉 " if pid == self.current_player_id else f"{i+1}. "
            count = len(self.hands.get(pid, []))
            locked = self.locked_melds.get(pid, [])
            locked_text = ""
            if locked:
                locked_counts = [str(len(m)) for m in locked]
                locked_text = f" (Locked: {', '.join(locked_counts)})"
            
            lines.append(f"{marker}<a href=\"tg://user?id={pid}\">{self.players[pid]}</a> — {count} card(s){locked_text}")
        return "\n".join(lines)

    def get_hand_count(self, user_id: int) -> int:
        return len(self.hands.get(user_id, []))

    def get_sorted_hand(self, user_id: int) -> List[RummyCard]:
        """Return hand sorted by suit then rank for display."""
        SUIT_ORDER = {s: i for i, s in enumerate(RummyCard.SUITS)}
        return sorted(
            self.hands.get(user_id, []),
            key=lambda c: (SUIT_ORDER[c.suit], c.rank_value)
        )
