import os
from pathlib import Path

BASE_DIR = Path(os.environ.get("TUTOR_BASE_DIR", "/opt/japanesetutor"))
FRONTEND_DIR = str(BASE_DIR / "frontend")

VOSK_MODEL_PATH = os.environ.get("VOSK_MODEL_PATH", str(BASE_DIR / "models/vosk/vosk-model-ja-0.22"))
DB_PATH = str(BASE_DIR / "data/tutor.db")
TTS_CACHE_DIR = str(BASE_DIR / "data/tts_cache")
PIPER_BINARY = str(BASE_DIR / "models/piper/piper")
PIPER_MODEL = str(BASE_DIR / "models/piper/ja_JP-kokoro-medium.onnx")
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma2:2b")
SAMPLE_RATE = 16000
