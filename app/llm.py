import os
import json
import httpx

BASE = "https://openrouter.ai/api/v1/responses"

PRIMARY = os.getenv("LLM_MODEL", "meta-llama/llama-3.1-8b-instruct:free")
FALLBACK = os.getenv("LLM_FALLBACK_MODEL", "qwen/qwen2.5-7b-instruct:free")

OPENROUTER_KEY = os.getenv("OPENROUTER_KEY", "").strip()

# Опционально, но полезно для OpenRouter аналитики
APP_SITE = os.getenv("APP_SITE", "https://goosememecorparation.onrender.com")
APP_NAME = os.getenv("APP_NAME", "Goose Meme Corp Bot")

HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_KEY}" if OPENROUTER_KEY else "",
    "Content-Type": "application/json",
    "HTTP-Referer": APP_SITE,
    "X-Title": APP_NAME,
}

ERR_MSG = "Сеть шипит. Кря. (модель временно недоступна)"

def _extract_text(resp_json: dict) -> str:
    """
    Универсальный экстрактор ответа:
    - OpenRouter Responses API: choices[0].message.content
    - Иногда есть output_text
    """
    if not isinstance(resp_json, dict):
        return ""
    # 1) output_text (OpenRouter sugar)
    text = resp_json.get("output_text")
    if isinstance(text, str) and text.strip():
        return text.strip()

    # 2) choices[].message.content
    choices = resp_json.get("choices") or []
    if choices and isinstance(choices, list):
        msg = choices[0].get("message") if isinstance(choices[0], dict) else None
        if isinstance(msg, dict):
            content = msg.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()

    # 3) output[0].content (редко)
    output = resp_json.get("output")
    if isinstance(output, list) and output:
        maybe = output[0]
        if isinstance(maybe, dict):
            content = maybe.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()

    # 4) как есть
    return json.dumps(resp_json)[:800]


async def _call_model(model: str, prompt: str) -> str:
    if not OPENROUTER_KEY:
        raise RuntimeError("OPENROUTER_KEY is empty")

    payload = {
        "model": model,
        # Минимальный промпт. Можно расширять системкой при желании.
        "messages": [
            {"role": "system", "content": "Ты остроумный, краткий помощник-гусятина 🪿."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.6,
        "max_tokens": 512,
    }

    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(BASE, headers=HEADERS, json=payload)

    # ВАЖНО: всегда логируем статус и первые символы тела
    rid = r.headers.get("x-request-id", "")
    body_preview = r.text[:1200]
    print(f"[LLM] {model} -> {r.status_code} {rid} :: {body_preview}")

    if r.status_code >= 400:
        raise RuntimeError(f"{model} failed: {r.status_code} {body_preview[:300]}")

    data = r.json()
    text = _extract_text(data)
    if not text.strip():
        raise RuntimeError(f"{model} empty output")
    return text


async def llm_chat(prompt: str) -> str:
    """
    Вызов LLM с авто-фолбэком.
    """
    try:
        return await _call_model(PRIMARY, prompt)
    except Exception as e:
        print("[LLM] Primary failed:", repr(e))
        try:
            return await _call_model(FALLBACK, prompt)
        except Exception as e2:
            print("[LLM] Fallback failed:", repr(e2))
            return ERR_MSG
