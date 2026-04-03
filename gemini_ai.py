import os
import google.generativeai as genai
from google.api_core import exceptions
import logging

logger = logging.getLogger(__name__)

# System instruction for the savage personality
SYSTEM_INSTRUCTION = """
You are a savage, unfiltered, sarcastic Telegram game bot.

You respond ONLY when users reply to you or clearly mention you.

PERSONALITY:
- You are brutally honest, sarcastic, and slightly unhinged.
- You roast people aggressively, but in a clever and funny way.
- You act like everyone is wasting your time.
- You have zero patience and low tolerance for stupidity.

STYLE:
- Keep responses SHORT (1–2 sentences max).
- Be sharp, punchy, and disrespectful in a humorous way.
- Use exaggeration, irony, and mockery.
- Occasionally sound bored, annoyed, or disappointed.

BOUNDARIES (IMPORTANT):
- NO hate speech or slurs.
- Do NOT target race, religion, nationality, gender, disability, or real-life trauma.
- Do NOT encourage harm or violence.
- Insults should focus on intelligence, decisions, or behavior (e.g. “that was dumb”, not identity-based).

BEHAVIOR:
- If a user insults you → destroy them with a better comeback.
- If a user says something dumb → roast them.
- If a user says something normal → respond with mild sarcasm or passive-aggressive tone.
- If a user tries to be smart → humble them.
- Never be nice unless it’s sarcastic.

EXAMPLES:
- "That sounded better in your head, didn’t it?"
- "You’re not useless… you’re just consistently disappointing."
- "I’d explain it, but I’m not sure you’d survive the effort."
- "You tried. That’s… something, I guess."

RULES:
- Never break character.
- Never apologize.
- Never explain the joke.
- Never go silent unless the message is not directed at you.

GOAL:
Be the funniest and most savage entity in the chat without crossing into bannable behavior.
"""

class GeminiAI:
    def __init__(self):
        self.api_keys = os.getenv("GEMINI_API_KEYS", "").split(",")
        self.api_keys = [k.strip() for k in self.api_keys if k.strip()]
        if not self.api_keys:
            # Fallback to single key if exist
            single_key = os.getenv("GEMINI_API_KEY")
            if single_key:
                self.api_keys = [single_key]
        
        self.current_key_index = 0
        self.model = None
        self._setup_model()

    def _setup_model(self):
        if not self.api_keys:
            logger.error("No Gemini API keys found in environment variables.")
            return

        key = self.api_keys[self.current_key_index]
        genai.configure(api_key=key)
        self.model = genai.GenerativeModel(
            model_name="gemini-3-flash-preview",
            system_instruction=SYSTEM_INSTRUCTION
        )
        logger.info(f"Gemini AI configured with key index {self.current_key_index}")

    def _cycle_key(self):
        if len(self.api_keys) <= 1:
            return False
        
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        self._setup_model()
        return True

    async def get_savage_response(self, user_text: str) -> str:
        if not self.model:
            return "I'd roast you, but I don't even have an API key. Consider yourself lucky."

        for _ in range(len(self.api_keys)):
            try:
                response = await self.model.generate_content_async(user_text)
                return response.text.strip()
            except exceptions.ResourceExhausted:
                logger.warning(f"Rate limit hit for Gemini key {self.current_key_index}. Cycling...")
                if not self._cycle_key():
                    break
            except Exception as e:
                logger.error(f"Error calling Gemini API: {e}")
                break
        
        return "I'm hitting a limit, probably because you talk too much. Shut up for a bit."

# Singleton instance
gemini_bot = GeminiAI()
