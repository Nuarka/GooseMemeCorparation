import os
from fastapi import FastAPI, Request
import httpx

from .logic import reply_dm, reply_group
from .config import BOT_TOKEN
from .llm import llm_chat, probe_models  # <-- добавили probe_models

API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = FastAPI(title="GooseBot")

@app.get("/health")
async def health():
    return {"ok": True, "service": "goosebot"}

@app.get("/debug_llm")
async def debug_llm_route():
    # Прямой пинг модели (новая сигнатура llm_chat(prompt: str))
    text = await llm_chat("Привет! Скажи одно короткое предложение про гусей.")
    return {"ok": True, "echo": text}

@app.get("/debug_llm_probe")
async def debug_llm_probe_route():
    # Детальная диагностика PRIMARY/FALLBACK и ключа
    info = await probe_models()
    return {"ok": True, "probe": info}

@app.post("/webhook")
async def webhook(req: Request):
    upd = await req.json()
    msg = upd.get("message") or upd.get("channel_post")
    if not msg:
        return {"ok": True}

    chat = msg.get("chat", {})
    chat_id = chat.get("id")
    chat_type = chat.get("type", "private")
    text = msg.get("text", "") or ""
    entities = msg.get("entities", []) or []
    mentioned = any(e.get("type") == "mention" for e in entities)

    is_group = chat_type in ("group", "supergroup", "channel")

    if is_group:
        out = await reply_group({"chat_id": chat_id}, text, mentioned)
        if out:
            if isinstance(out, dict) and out.get("meme"):
                await tg_send(chat_id, meme=True)
            else:
                await tg_send(chat_id, text=out)
    else:
        out = await reply_dm(text)
        await tg_send(chat_id, text=out)

    return {"ok": True}

@app.get("/")
def root():
    return {"ok": True, "app": "GooseBot", "hint": "use /webhook or /debug_llm"}
