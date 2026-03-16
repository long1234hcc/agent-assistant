import os
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from gateway.channels.telegram import TelegramAdapter
from gateway.channels.http import HttpAdapter
from gateway.dispatcher import dispatchInboundMessage
from fastapi.concurrency import run_in_threadpool


# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gateway")

# ── Global adapters ────────────────────────────────────────────────────────
_telegram_adapter: TelegramAdapter | None = None
_http_adapter = HttpAdapter()

# ── Startup / Shutdown lifecycle ───────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):

    global _telegram_adapter

    # 1. Tạo folders cần thiết
    os.makedirs("workspace/auth", exist_ok=True)
    os.makedirs("workspace/sessions_store", exist_ok=True)

    # 2. Kiểm tra Telegram token
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if token:
        _telegram_adapter = TelegramAdapter(bot_token=token)
        logger.info("Telegram adapter initialized.")
    else:
        logger.warning("TELEGRAM_BOT_TOKEN not set. Telegram webhook disabled.")

    # 3. Log startup
    logger.info("Gateway started on port 8000")

    yield

    # cleanup nếu cần
    logger.info("Gateway shutting down...")


# ── FastAPI app ────────────────────────────────────────────────────────────
app = FastAPI(lifespan=lifespan)

# ── Telegram Webhook Endpoint ──────────────────────────────────────────────
@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    if _telegram_adapter is None:
        return JSONResponse(status_code=503, content={"error": "Telegram adapter not configured"})
    raw = await request.json()
    msg = _telegram_adapter.parse_inbound(raw)
    await run_in_threadpool(dispatchInboundMessage, msg)
    return {"status": "ok"}

# ── HTTP Chat Endpoint ─────────────────────────────────────────────────────
@app.post("/chat")
async def chat(request: Request):
    raw = await request.json()
    msg = _http_adapter.parse_inbound(raw)
    
    # chạy blocking dispatcher trong thread pool
    await run_in_threadpool(dispatchInboundMessage, msg)
    
    reply = _http_adapter.get_reply()
    if reply is None:
        return JSONResponse(
            status_code=500,
            content={"error": "No reply generated"}
        )
    return {"text": reply.text}


# ── Health Check ───────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting uvicorn server...")
    # NOTE: Run this script from the root of the project (assistant directory)
    uvicorn.run("gateway.server:app", host="0.0.0.0", port=8000, reload=True)