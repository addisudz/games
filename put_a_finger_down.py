import random
import logging
from typing import List, Dict, Optional, Tuple, Set

logger = logging.getLogger(__name__)

class PutAFingerDownGame:
    """Manages the Put A Finger Down game logic."""

    QUESTIONS = [
        "Put a finger down if you've ever lied to your parents about where you were.",
        "Put a finger down if you've ever cried in public.",
        "Put a finger down if you've ever had a crush on a teacher.",
        "Put a finger down if you've ever cheated on a test.",
        "Put a finger down if you've ever broken a bone.",
        "Put a finger down if you've ever been on TV.",
        "Put a finger down if you've ever traveled outside of Ethiopia.",
        "Put a finger down if you've ever stayed up all night.",
        "Put a finger down if you've ever sent a text to the wrong person.",
        "Put a finger down if you've ever laughed so hard you cried.",
        "Put a finger down if you've ever forgotten someone's name right after meeting them.",
        "Put a finger down if you've ever stalked an ex on social media.",
        "Put a finger down if you've ever talked to yourself in the mirror.",
        "Put a finger down if you've ever tripped in public and pretended it didn't happen.",
        "Put a finger down if you've ever regifted a present.",
        "Put a finger down if you've ever fallen asleep in class.",
        "Put a finger down if you've ever lied about your age.",
        "Put a finger down if you've ever eaten food that fell on the floor.",
        "Put a finger down if you've ever pretended to be on the phone to avoid someone.",
        "Put a finger down if you've ever sung in the shower.",
        "Put a finger down if you've ever spent more than 5 hours on your phone today.",
        "Put a finger down if you've ever Googled yourself.",
        "Put a finger down if you've ever worn pajamas all day.",
        "Put a finger down if you've ever practiced an argument in your head.",
        "Put a finger down if you've ever binge-watched a whole series in one weekend.",
        "Put a finger down if you've ever accidentally liked an old photo while stalking someone.",
        "Put a finger down if you've ever forgotten why you walked into a room.",
        "Put a finger down if you've ever lied to get out of plans.",
        "Put a finger down if you've ever talked to a pet like it's a human.",
        "Put a finger down if you've ever tried to open a door that says 'pull' by pushing it.",
        "Put a finger down if you've ever laughed at a joke you didn't get.",
        "Put a finger down if you've ever checked the fridge multiple times hoping for new food.",
        "Put a finger down if you've ever used your phone's flashlight to look for your phone.",
        "Put a finger down if you've ever pretended to know a song when you didn't.",
        "Put a finger down if you've ever accidentally called someone 'Mom' or 'Dad' who wasn't.",
    ]

    def __init__(self, total_rounds: int = 15):
        self.total_rounds = total_rounds
        self.current_round = 0
        self.is_active = False
        
        # Player state
        self.players: Dict[int, str] = {}  # user_id -> display_name
        self.fingers: Dict[int, int] = {}  # user_id -> finger_count (starts at 10)
        
        # Answer history: user_id -> list of (question, put_down: bool)
        self.answer_history: Dict[int, List[Tuple[str, bool]]] = {}
        
        # Round state
        self.current_question: Optional[str] = None
        self.answered_this_round: Set[int] = set() # user_ids who answered in current round
        self.used_questions: Set[str] = set()

    def add_player(self, user_id: int, display_name: str) -> None:
        """Add a player to the game."""
        if user_id not in self.players:
            self.players[user_id] = display_name
            self.fingers[user_id] = 10
            self.answer_history[user_id] = []

    def remove_player(self, user_id: int) -> None:
        """Remove a player from the game."""
        if user_id in self.players:
            del self.players[user_id]
            if user_id in self.fingers:
                del self.fingers[user_id]

    def start_game(self) -> str:
        """Initialize and start the game."""
        self.is_active = True
        self.current_round = 0
        self.used_questions = set()
        for pid in self.players:
            self.fingers[pid] = 10
            self.answer_history[pid] = []
        return "Put a Finger Down game has started! 🖐️ Each player starts with 10 fingers."

    def next_round(self) -> Optional[str]:
        """Advance to the next round and return the new question."""
        if self.current_round >= self.total_rounds:
            self.is_active = False
            return None
            
        self.current_round += 1
        self.answered_this_round = set()
        
        # Pick a unique question
        available = [q for q in self.QUESTIONS if q not in self.used_questions]
        if not available:
            available = self.QUESTIONS # Refill if all used
            self.used_questions = set()
            
        self.current_question = random.choice(available)
        self.used_questions.add(self.current_question)
        
        return self.current_question

    def handle_answer(self, user_id: int, put_down: bool) -> Tuple[bool, int]:
        """
        Record a player's answer for the current round.
        Returns: (success, new_finger_count)
        """
        if user_id not in self.players or user_id in self.answered_this_round:
            return False, self.fingers.get(user_id, 10)
            
        if put_down:
            self.fingers[user_id] = max(0, self.fingers[user_id] - 1)
        
        # Track the per-question answer
        q = self.current_question or "Unknown question"
        if user_id not in self.answer_history:
            self.answer_history[user_id] = []
        self.answer_history[user_id].append((q, put_down))
            
        self.answered_this_round.add(user_id)
        return True, self.fingers[user_id]

    def get_non_responders(self) -> List[int]:
        """Get list of user IDs who haven't answered in the current round."""
        return [pid for pid in self.players if pid not in self.answered_this_round]

    def is_game_over(self) -> bool:
        """Check if the game has reached the total rounds limit."""
        return self.current_round >= self.total_rounds or not self.is_active

    def get_results(self) -> List[Tuple[int, str, int]]:
        """Get the final results: (user_id, name, remaining_fingers)."""
        results = []
        for pid, name in self.players.items():
            results.append((pid, name, self.fingers[pid]))
        # Sort by fingers remaining (more is better? or just sort)
        return sorted(results, key=lambda x: x[2], reverse=True)

    def build_ai_prompt(self) -> str:
        """Build a Gemini prompt summarizing each player's answers for AI analysis."""
        lines = []
        for uid, name in self.players.items():
            history = self.answer_history.get(uid, [])
            if not history:
                continue
            yes_list = [q.replace("Put a finger down if you've ever ", "").rstrip(".") for q, ans in history if ans]
            no_list = [q.replace("Put a finger down if you've ever ", "").rstrip(".") for q, ans in history if not ans]
            lines.append(f"Player: {name}")
            if yes_list:
                lines.append(f"  They said YES to: {', '.join(yes_list)}.")
            if no_list:
                lines.append(f"  They said NO to: {', '.join(no_list)}.")
            lines.append("")
        
        if not lines:
            return ""
        
        summary = "\n".join(lines)
        prompt = (
            f"These players just played a \"Put A Finger Down\" game where they answered personal questions.\n"
            f"Here are their answers:\n\n{summary}\n"
            f"Based on each player's answers, write a short, fun, and insightful personality read for each one. "
            f"Be playful but honest. Address each player by name directly.\n"
            f"Format your response like:\n"
            f"Here is what I can tell.\n"
            f"[Name1] — you are the type of person who...\n"
            f"[Name2] — you are the type of person who...\n"
            f"Keep it casual, fun, and a tiny bit savage."
        )
        return prompt
