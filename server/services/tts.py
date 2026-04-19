import hashlib
import logging
import subprocess
from pathlib import Path
from server.config import PIPER_BINARY, PIPER_MODEL, TTS_CACHE_DIR

logger = logging.getLogger(__name__)


def _cache_path(text: str) -> Path:
    key = hashlib.md5(text.encode()).hexdigest()
    return Path(TTS_CACHE_DIR) / f"{key}.wav"


def speak(text: str) -> bytes | None:
    """Return WAV bytes for text, using cache. Returns None if Piper unavailable."""
    cached = _cache_path(text)
    if cached.exists():
        return cached.read_bytes()

    piper = Path(PIPER_BINARY)
    model = Path(PIPER_MODEL)
    if not piper.exists() or not model.exists():
        logger.warning("Piper not available — TTS skipped")
        return None

    try:
        Path(TTS_CACHE_DIR).mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [str(piper), "--model", str(model), "--output_file", str(cached)],
            input=text.encode(),
            capture_output=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.error("Piper error: %s", result.stderr.decode())
            return None
        return cached.read_bytes()
    except Exception as e:
        logger.error("TTS failed: %s", e)
        return None
