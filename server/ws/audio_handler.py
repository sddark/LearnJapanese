from fastapi import WebSocket, WebSocketDisconnect
from server.services.stt import STTSession


async def stt_websocket(websocket: WebSocket):
    """
    Generic streaming STT WebSocket.
    Client sends binary PCM frames (16kHz, 16-bit mono).
    Server streams {"type":"partial","text":"..."} and {"type":"final","text":"...","confidence":0.9}.
    Client sends text "STOP" to flush final result and close.
    """
    await websocket.accept()
    try:
        session = STTSession()
    except RuntimeError:
        await websocket.send_json({"type": "error", "text": "STT unavailable"})
        await websocket.close()
        return
    try:
        while True:
            data = await websocket.receive()
            if "bytes" in data and data["bytes"]:
                result = session.feed(data["bytes"])
                if result:
                    await websocket.send_json(result)
            elif "text" in data:
                if data["text"] == "STOP":
                    final = session.finalize()
                    await websocket.send_json(final)
                    break
    except WebSocketDisconnect:
        pass
