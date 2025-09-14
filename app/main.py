import os
from fastapi import FastAPI, Request
import httpx
from .logic import reply_dm, reply_group
from .config import BOT_TOKEN

from fastapi import FastAPI
from .llm import llm_chat

API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = FastAPI(title="GooseBot")

@app.get("/health")
async def health():
    return {"ok": True, "service": "goosebot"}

@app.get("/debug_llm")
async def debug_llm():
    # Явная проверка LLM (минуя Телеграм)
    text = await llm_chat("Привет! Скажи одно короткое предложение про гусей.")
    return {"ok": True, "echo": text}
    
async def tg_send(chat_id, text=None, meme=False):
    async with httpx.AsyncClient(timeout=20) as c:
        if meme:
            # MVP: text meme; later you can switch to sendPhoto with real file_id
            return await c.post(f"{API}/sendMessage",
                                json={"chat_id": chat_id, "text": "Кря‑мем: [ ] (представь гусей) 🪿"})
        return await c.post(f"{API}/sendMessage", json={"chat_id": chat_id, "text": text})

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
    return {"ok": True, "app": "GooseBot", "hint": "use /serve or Telegram webhook"}

    # app/main.py — в конец файла
@app.get("/debug_llm")
async def debug_llm():
    # Мини-тест до OpenRouter без Телеграма
    from .llm import llm_chat
    out = await llm_chat(
        [{"role":"system","content":"Скажи одно слово: Кря"},
         {"role":"user","content":"Отвечай только этим словом."}],
        max_tokens=8
    )
    return {"ok": True, "echo": out}

