import httpx
from .config import OPENROUTER_KEY, LLM_MODEL

BASE = "https://openrouter.ai/api/v1/chat/completions"

async def llm_chat(messages, max_tokens=120, timeout=30):
    if not OPENROUTER_KEY:
        return "Я тут без ключа OpenRouter. Кря."
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "HTTP-Referer": "https://goose.bot",
        "X-Title": "GooseBot",
    }
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.8,
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as c:
            r = await c.post(BASE, json=payload, headers=headers)
            if r.status_code >= 400:
                # аккуратно даём заглушку вместо падения
                return "Сеть шипит. Кря. (модель временно недоступна)"
            data = r.json()
            return data["choices"][0]["message"]["content"].strip()
    except httpx.HTTPError:
        return "Связь с прудом шумит. Попробуем позже. Кря."
