from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from server.services.tts import speak

router = APIRouter(prefix="/api/tts", tags=["tts"])


@router.get("/speak")
def tts_speak(text: str):
    wav = speak(text)
    if wav is None:
        raise HTTPException(503, "TTS unavailable")
    return Response(content=wav, media_type="audio/wav")
