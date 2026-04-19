import json
import logging
import httpx
from server.config import OLLAMA_URL, OLLAMA_MODEL

logger = logging.getLogger(__name__)

_GENERATE_PROMPT = """\
You are a Japanese tutor. Create one short, simple Japanese sentence (JLPT N5 level) using the word "{word}" ({romaji} - {meaning}).
Reply with valid JSON only, no other text:
{{"japanese": "<sentence in Japanese>", "english": "<English translation>"}}"""

_EVALUATE_PROMPT = """\
The target Japanese word was "{word}" ({romaji}). The student said: "{transcript}".
Did the student correctly say this word (exact or close enough)?
Reply with valid JSON only, no other text:
{{"correct": true or false, "correction": "<correct pronunciation if wrong, else null>"}}"""


def _call(prompt: str, temperature: float = 0.7) -> dict | None:
    try:
        r = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "options": {"temperature": temperature}},
            timeout=30,
        )
        r.raise_for_status()
        raw = r.json().get("response", "")
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == 0:
            logger.warning("LLM returned no JSON: %s", raw)
            return None
        return json.loads(raw[start:end])
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        return None


def generate_sentence(word: str, romaji: str, meaning: str) -> dict:
    result = _call(_GENERATE_PROMPT.format(word=word, romaji=romaji, meaning=meaning), temperature=0.7)
    if result and "japanese" in result and "english" in result:
        return result
    return {"japanese": f"{word}。", "english": f"({meaning})"}


def evaluate_answer(word: str, romaji: str, transcript: str) -> dict:
    result = _call(_EVALUATE_PROMPT.format(word=word, romaji=romaji, transcript=transcript), temperature=0.3)
    if result and "correct" in result:
        return result
    # Fallback: simple string match
    correct = transcript.strip().lower() in (romaji.lower(), word)
    return {"correct": correct, "correction": None if correct else romaji}
