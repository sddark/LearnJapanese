import json
import logging
from vosk import Model, KaldiRecognizer
from server.config import VOSK_MODEL_PATH, SAMPLE_RATE

logger = logging.getLogger(__name__)

_model: Model | None = None


def load_model() -> None:
    global _model
    logger.info("Loading Vosk model from %s — this may take 10-15s", VOSK_MODEL_PATH)
    _model = Model(VOSK_MODEL_PATH)
    logger.info("Vosk model loaded")


def get_model() -> Model:
    if _model is None:
        raise RuntimeError("Vosk model not loaded — call load_model() at startup")
    return _model


class STTSession:
    """One KaldiRecognizer per WebSocket connection (not thread-safe)."""

    def __init__(self):
        self._rec = KaldiRecognizer(get_model(), SAMPLE_RATE)
        self._rec.SetWords(True)

    def feed(self, pcm_bytes: bytes) -> dict | None:
        """
        Feed a chunk of PCM bytes.
        Returns a result dict when a segment is complete, partial otherwise.
        """
        if self._rec.AcceptWaveform(pcm_bytes):
            result = json.loads(self._rec.Result())
            return {"type": "final", "text": result.get("text", ""), "confidence": _avg_conf(result)}
        partial = json.loads(self._rec.PartialResult()).get("partial", "")
        if partial:
            return {"type": "partial", "text": partial}
        return None

    def finalize(self) -> dict:
        result = json.loads(self._rec.FinalResult())
        return {"type": "final", "text": result.get("text", ""), "confidence": _avg_conf(result)}


def _avg_conf(result: dict) -> float:
    words = result.get("result", [])
    if not words:
        return 0.0
    return sum(w.get("conf", 0.0) for w in words) / len(words)
