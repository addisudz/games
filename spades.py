import os
import random
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum

class SpadesGameState(Enum):
    JOINING = "joining"
    PARTNER_SELECTION = "partner_selection"
    BIDDING = "bidding"
    PLAYING_TRICK = "playing_trick"
    GAME_OVER = "game_over"

class Card:
    RANK_VALUES = {
        '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, 
        '8': 8, '9': 9, '10': 10, 'jack': 11, 'queen': 12, 'king': 13, 'ace': 14
    }

    def __init__(self, rank: str, suit: str):
        self.rank = rank
        self.suit = suit
        self.rank_value = self.RANK_VALUES[rank]
        self.filename = f"{rank}_of_{suit}.png"

    def __str__(self):
        return f"{self.rank.capitalize()} of {self.suit.capitalize()}"

    def __eq__(self, other):
        if not isinstance(other, Card):
            return False
        return self.rank == other.rank and self.suit == other.suit
    
    def __hash__(self):
        return hash((self.rank, self.suit))

class SpadesGame:
    """Manages a game of Spades."""

    RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'jack', 'queen', 'king', 'ace']
    SUITS = ['clubs', 'diamonds', 'hearts', 'spades']

    def __init__(self):
        self.state = SpadesGameState.JOINING
        self.players: Dict[int, str] = {} # user_id -> display_name
        self.player_ids: List[int] = [] # Ordered for turn rotation
        self.teams: Dict[int, int] = {} # user_id -> team_id (1 or 2)
        
        self.hands: Dict[int, List[Card]] = {} # user_id -> list of cards
        self.bids: Dict[int, int] = {} # user_id -> bid (0-13)
        self.tricks_won: Dict[int, int] = {} # user_id -> number of tricks won
        
        self.team_scores = {1: 0, 2: 0}
        self.team_bags = {1: 0, 2: 0}
        
        self.current_trick: List[Tuple[int, Card]] = [] # list of (user_id, card)
        self.spades_broken = False
        
        self.turn_index = 0
        self.current_player_id: Optional[int] = None
        self.dealer_index = 0
        self.trick_leader_id: Optional[int] = None
        
        self.selector_id: Optional[int] = None
        self.game_over = False
        self.winning_team: Optional[int] = None
        self.target_score = 500

    def add_player(self, user_id: int, display_name: str) -> None:
        if self.state != SpadesGameState.JOINING:
            return
        if len(self.players) >= 4:
            return
        self.players[user_id] = display_name

    def remove_player(self, user_id: int) -> None:
        if user_id in self.players:
            del self.players[user_id]
        if self.state != SpadesGameState.JOINING:
            # If someone leaves mid-game, game over
            self.state = SpadesGameState.GAME_OVER
            self.game_over = True

    def get_player_count(self) -> int:
        return len(self.players)

    def start_game(self) -> bool:
        """Transitions to partner selection phase if 4 players, or dealing if 2 players."""
        if len(self.players) not in (2, 4):
            return False
            
        self.player_ids = list(self.players.keys())
        if len(self.player_ids) == 4:
            self.selector_id = random.choice(self.player_ids)
            self.state = SpadesGameState.PARTNER_SELECTION
        else:
            self.teams[self.player_ids[0]] = 1
            self.teams[self.player_ids[1]] = 2
            self.dealer_index = random.randint(0, 1)
            self._deal_new_round()
            
        return True

    def choose_partner(self, selector_id: int, partner_id: int) -> bool:
        """Handles partner selection and moves to dealing/bidding."""
        if self.state != SpadesGameState.PARTNER_SELECTION:
            return False
        if selector_id != self.selector_id:
            return False
        if partner_id not in self.players or partner_id == selector_id:
            return False
            
        remaining_ids = [pid for pid in self.player_ids if pid not in (selector_id, partner_id)]
        
        # Set teams
        self.teams[selector_id] = 1
        self.teams[partner_id] = 1
        self.teams[remaining_ids[0]] = 2
        self.teams[remaining_ids[1]] = 2
        
        # Arrange sitting order: Team 1, Team 2, Team 1, Team 2
        self.player_ids = [selector_id, remaining_ids[0], partner_id, remaining_ids[1]]
        self.dealer_index = random.randint(0, 3)
        self._deal_new_round()
        return True

    def _deal_new_round(self):
        self.state = SpadesGameState.BIDDING
        deck = [Card(r, s) for r in self.RANKS for s in self.SUITS]
        random.shuffle(deck)
        
        for i, pid in enumerate(self.player_ids):
            self.hands[pid] = sorted(deck[i*13:(i+1)*13], key=lambda c: (self.SUITS.index(c.suit), c.rank_value))
            
        self.bids.clear()
        self.tricks_won = {pid: 0 for pid in self.player_ids}
        self.current_trick.clear()
        self.spades_broken = False
        
        # Player to left of dealer starts bidding and trick 1
        self.turn_index = (self.dealer_index + 1) % len(self.player_ids)
        self.current_player_id = self.player_ids[self.turn_index]
        self.trick_leader_id = self.player_ids[self.turn_index]

    def place_bid(self, user_id: int, bid_amount: int) -> Tuple[bool, str]:
        if self.state != SpadesGameState.BIDDING:
            return False, "Not the bidding phase."
        if user_id not in self.players:
            return False, "You are not in the game."
        if bid_amount < 0 or bid_amount > 13:
            return False, "Bid must be between 0 and 13."
        if user_id in self.bids:
            return False, "You have already placed a bid."
            
        self.bids[user_id] = bid_amount
        
        if len(self.bids) == len(self.player_ids):
            self.state = SpadesGameState.PLAYING_TRICK
            return True, "All bids received! Let the trick playing begin!"
        return True, f"{self.players[user_id]} bid {bid_amount}."

    def parse_card_from_text(self, text: str) -> Optional[Card]:
        text = text.lower()
        if text.startswith("played:"):
            text = text[len("played:"):].strip()
        text = text.replace('the ', '').replace(' of ', ' ')
        tokens = text.split()
        if len(tokens) < 2:
            return None
        
        rank = None
        suit = None
        for r in self.RANKS:
            if r in tokens or (r == 'ace' and 'a' in tokens) or (r == 'jack' and 'j' in tokens) or (r == 'queen' and 'q' in tokens) or (r == 'king' and 'k' in tokens):
                rank = r
                break
        
        for s in self.SUITS:
            if s in text or (s[:-1] in text):
                suit = s
                break
                
        if rank and suit:
            return Card(rank, suit)
        return None

    def get_valid_plays(self, player_hand: List[Card]) -> List[Card]:
        if not self.current_trick:
            # First card of the trick. Can lead anything except spades, unless spades broken or only have spades.
            has_non_spade = any(c.suit != 'spades' for c in player_hand)
            if not self.spades_broken and has_non_spade:
                return [c for c in player_hand if c.suit != 'spades']
            return player_hand
        
        # Must follow suit if possible
        led_suit = self.current_trick[0][1].suit
        following_cards = [c for c in player_hand if c.suit == led_suit]
        if following_cards:
            return following_cards
        return player_hand

    def is_valid_play(self, played_card: Card, valid_plays: List[Card]) -> bool:
        return played_card in valid_plays

    def play_card(self, user_id: int, card_text: str) -> Tuple[bool, str, Optional[str], bool, Optional[str]]:
        """Attempt to play a card.
        Returns: 
          (success, message, filename_of_played_card, trick_finished, evaluation_message)
        """
        if self.state != SpadesGameState.PLAYING_TRICK:
            return False, "Not the playing phase.", None, False, None
            
        if user_id != self.current_player_id:
            return False, "It's not your turn!", None, False, None
            
        played_card = self.parse_card_from_text(card_text)
        if not played_card:
            return False, "I couldn't understand that card.", None, False, None
            
        player_hand = self.hands[user_id]
        card_in_hand = next((c for c in player_hand if c == played_card), None)
        if not card_in_hand:
            return False, f"You don't have the {str(played_card)} in your hand.", None, False, None
            
        valid_plays = self.get_valid_plays(player_hand)
        if not self.is_valid_play(card_in_hand, valid_plays):
            if self.current_trick:
                led_suit = self.current_trick[0][1].suit
                return False, f"Invalid play! You must follow suit ({led_suit}) if possible.", None, False, None
            else:
                return False, "Invalid play! Spades are not broken yet.", None, False, None
                
        # Valid play
        player_hand.remove(card_in_hand)
        self.current_trick.append((user_id, card_in_hand))
        
        if card_in_hand.suit == 'spades':
            self.spades_broken = True
            
        play_msg = f"{self.players[user_id]} played {str(card_in_hand)}."
        
        # Check if trick is finished
        if len(self.current_trick) == len(self.player_ids):
            eval_msg = self._evaluate_trick()
            self._advance_turn() # Though winner leads next trick, so _evaluate sets the new turn.
            return True, play_msg, card_in_hand.filename, True, eval_msg
        else:
            self._advance_turn()
            next_player = self.players[self.current_player_id]
            play_msg += f"\n\nIt's now {next_player}'s turn."
            return True, play_msg, card_in_hand.filename, False, None

    def _evaluate_trick(self) -> str:
        led_suit = self.current_trick[0][1].suit
        winning_card = self.current_trick[0][1]
        winner_id = self.current_trick[0][0]
        
        for pid, card in self.current_trick[1:]:
            if card.suit == 'spades' and winning_card.suit != 'spades':
                winning_card = card
                winner_id = pid
            elif card.suit == winning_card.suit and card.rank_value > winning_card.rank_value:
                winning_card = card
                winner_id = pid
                
        self.tricks_won[winner_id] += 1
        eval_msg = f"🏆 {self.players[winner_id]} won the trick with {str(winning_card)}!"
        
        self.current_trick.clear()
        
        # Set next turn to the winner
        self.trick_leader_id = winner_id
        self.current_player_id = winner_id
        self.turn_index = self.player_ids.index(winner_id)
        
        # Check end of round
        if all(len(hand) == 0 for hand in self.hands.values()):
            return eval_msg + "\n\n" + self._evaluate_round()
            
        eval_msg += f"\n\nIt is {self.players[winner_id]}'s turn to lead."
        return eval_msg

    def _evaluate_round(self) -> str:
        team1_ids = [pid for pid, tid in self.teams.items() if tid == 1]
        team2_ids = [pid for pid, tid in self.teams.items() if tid == 2]
        
        round_msg = "🏁 <b>Round Over! Scopes:</b>\n"
        
        for tid, t_ids in [(1, team1_ids), (2, team2_ids)]:
            team_bid = sum(self.bids[pid] for pid in t_ids if self.bids[pid] != 0)
            team_tricks = sum(self.tricks_won[pid] for pid in t_ids)
            
            round_score = 0
            
            # Handle Nil bids individually
            for pid in t_ids:
                if self.bids[pid] == 0:
                    if self.tricks_won[pid] == 0:
                        round_score += 100
                        round_msg += f"✨ {self.players[pid]} succeeded their Nil bid! (+100)\n"
                    else:
                        round_score -= 100
                        round_msg += f"💀 {self.players[pid]} failed their Nil bid! (-100)\n"
            
            # Regular bidding points
            if team_bid > 0:
                if team_tricks >= team_bid:
                    bags = team_tricks - team_bid
                    round_score += (team_bid * 10) + bags
                    self.team_bags[tid] += bags
                    round_msg += f"Team {tid} met their bid of {team_bid} with {bags} bags. (+{team_bid*10 + bags})\n"
                else:
                    round_score -= (team_bid * 10)
                    round_msg += f"Team {tid} failed their bid of {team_bid} (Got {team_tricks}). (-{team_bid*10})\n"
            
            # Bag penalties
            if self.team_bags[tid] >= 10:
                round_score -= 100
                self.team_bags[tid] -= 10
                round_msg += f"🎒 Team {tid} accumulated 10 bags! (-100 points, bags reset to {self.team_bags[tid]})\n"
                
            self.team_scores[tid] += round_score
            round_msg += f"<b>Team {tid} Score:</b> {self.team_scores[tid]} (Bags: {self.team_bags[tid]})\n\n"
            
        # Check game over
        if self.team_scores[1] >= self.target_score or self.team_scores[2] >= self.target_score:
            self.state = SpadesGameState.GAME_OVER
            self.game_over = True
            if self.team_scores[1] > self.team_scores[2]:
                self.winning_team = 1
            elif self.team_scores[2] > self.team_scores[1]:
                self.winning_team = 2
            else:
                self.game_over = False # Tie breaker? Let's just continue
                round_msg += "Game is tied! Dealing another round...\n"
                
        if self.game_over:
            round_msg += f"\n🏆 <b>Team {self.winning_team} WINS THE GAME!</b>"
        else:
            self.dealer_index = (self.dealer_index + 1) % len(self.player_ids)
            self._deal_new_round()
            round_msg += f"Dealing next round... 🎴\n\nIt is {self.players[self.current_player_id]}'s turn to bid."
            
        return round_msg

    def _advance_turn(self):
        if not self.player_ids:
            return
        self.turn_index = (self.turn_index + 1) % len(self.player_ids)
        self.current_player_id = self.player_ids[self.turn_index]
        
    def get_team_players(self, team_id: int) -> List[int]:
        return [pid for pid, tid in self.teams.items() if tid == team_id]
