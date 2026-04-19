import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from server.services.stt import load_model
from server.database import init_db
from server.routers import kana, words, quiz, progress, tts, conversation
from server.ws.audio_handler import stt_websocket
from server.ws.conversation_ws import conversation_websocket
from server.config import BASE_DIR, FRONTEND_DIR

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    load_model()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(kana.router)
app.include_router(words.router)
app.include_router(quiz.router)
app.include_router(progress.router)
app.include_router(tts.router)
app.include_router(conversation.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.websocket("/ws/stt")
async def ws_stt(websocket: WebSocket):
    await stt_websocket(websocket)


@app.websocket("/ws/conversation")
async def ws_conversation(websocket: WebSocket):
    await conversation_websocket(websocket)


# Mount static files last — catches all remaining HTTP requests
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
