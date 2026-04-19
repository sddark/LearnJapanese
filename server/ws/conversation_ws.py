import json
import logging
import random
from fastapi import WebSocket, WebSocketDisconnect
from server.database import get_db
from server.services import tts, llm
from server.services.stt import get_model

logger = logging.getLogger(__name__)

CHUNK_SIZE = 32_768  # bytes per WAV send


def _pick_word(conn) -> dict | None:
    from datetime import date
    today = date.today().isoformat()
    row = conn.execute(
        """SELECT * FROM words
           WHERE status != 'unknown'
             AND (next_review <= ? OR next_review IS NULL)
           ORDER BY RANDOM() LIMIT 1""",
        (today,),
    ).fetchone()
    if not row:
        row = conn.execute(
            "SELECT * FROM words ORDER BY RANDOM() LIMIT 1"
        ).fetchone()
    return dict(row) if row else None


async def _send_json(ws: WebSocket, data: dict):
    await ws.send_text(json.dumps(data))


async def _send_audio(ws: WebSocket, wav_bytes: bytes):
    await _send_json(ws, {"type": "audio_start"})
    for i in range(0, len(wav_bytes), CHUNK_SIZE):
        await ws.send_bytes(wav_bytes[i:i + CHUNK_SIZE])
    await _send_json(ws, {"type": "audio_done"})


async def conversation_websocket(websocket: WebSocket):
    await websocket.accept()
    session_id: int | None = None
    turn_number = 0

    try:
        # Expect session handshake first
        init = json.loads(await websocket.receive_text())
        session_id = init.get("session_id")
        if not session_id:
            await _send_json(websocket, {"type": "error", "message": "session_id required"})
            return

        with get_db() as conn:
            session = conn.execute(
                "SELECT * FROM conversation_sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if not session:
                await _send_json(websocket, {"type": "error", "message": "session not found"})
                return
            turn_number = session["turn_count"]

        await _send_json(websocket, {"type": "ready", "session_id": session_id})

        while True:
            turn_number += 1

            with get_db() as conn:
                word = _pick_word(conn)

            if not word:
                await _send_json(websocket, {"type": "done", "message": "No words available"})
                break

            # Generate AI sentence
            sentence = llm.generate_sentence(word["word"], word["romaji"], word["meaning"])
            await _send_json(websocket, {
                "type": "ai_text",
                "japanese": sentence["japanese"],
                "english": sentence["english"],
                "target_word": word["word"],
                "turn": turn_number,
            })

            # TTS
            wav = tts.speak(sentence["japanese"])
            if wav:
                await _send_audio(websocket, wav)
            else:
                await _send_json(websocket, {"type": "audio_done"})

            # Signal client to listen
            await _send_json(websocket, {"type": "listen"})

            # Client streams audio to /ws/stt independently and sends us the transcript
            msg_raw = await websocket.receive_text()
            msg = json.loads(msg_raw)
            transcript = msg.get("text", "")

            await _send_json(websocket, {"type": "transcript", "text": transcript})

            # Evaluate
            evaluation = llm.evaluate_answer(word["word"], word["romaji"], transcript)
            await _send_json(websocket, {
                "type": "evaluation",
                "correct": evaluation["correct"],
                "correction": evaluation.get("correction"),
                "turn": turn_number,
            })

            # Persist turn
            with get_db() as conn:
                conn.execute(
                    """INSERT INTO conversation_turns
                       (session_id, turn_number, ai_japanese, ai_english, user_transcript,
                        target_word_id, correct, correction)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (session_id, turn_number, sentence["japanese"], sentence["english"],
                     transcript, word["id"], int(evaluation["correct"]),
                     evaluation.get("correction")),
                )
                conn.execute(
                    "UPDATE conversation_sessions SET turn_count = ?, updated_at = datetime('now') WHERE id = ?",
                    (turn_number, session_id),
                )

    except WebSocketDisconnect:
        logger.info("Conversation WS disconnected (session %s)", session_id)
    except Exception as e:
        logger.error("Conversation WS error: %s", e)
        try:
            await _send_json(websocket, {"type": "error", "message": str(e)})
        except Exception:
            pass
