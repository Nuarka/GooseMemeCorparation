import os
import json
import httpx

BASE = "https://openrouter.ai/api/v1/responses"

PRIMARY = os.getenv("LLM_MODEL", "meta-llama/llama-3.1-8b-instruct:free")
FALLBACK = os.getenv("LLM_FALLBACK_MODEL", "qwen/qwen2.5-7b-instruct:free")

# Пытаемся взять ключ из ENV, а если пусто — пробуем из config (если есть)
OPENROUTER_KEY = (os.getenv("OPENROUTER_KEY") or "").strip()
if not OPENROUTER_KEY:
    try:
        from .config import OPENROUTER_KEY as CONF_KEY  # опционально
        OPENROUTER_KEY = (CONF_KEY or "").strip()
    except Exception:
        pass

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
    if not isinstance(resp_json, dict):
        return ""
    text = resp_json.get("output_text")
    if isinstance(text, str) and text.strip():
        return text.strip()
    choices = resp_json.get("choices") or []
    if choices and isinstance(choices, list):
        msg = choices[0].get("message") if isinstance(choices[0], dict) else None
        if isinstance(msg, dict):
            content = msg.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()
    output = resp_json.get("output")
    if isinstance(output, list) and output:
        maybe = output[0]
        if isinstance(maybe, dict):
            content = maybe.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()
    return json.dumps(resp_json)[:800]

async def _call_model(model: str, prompt: str) -> str:
    if not OPENROUTER_KEY:
        raise RuntimeError("OPENROUTER_KEY is empty")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Ты остроумный, краткий помощник-гусятина 🪿."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.6,
        "max_tokens": 512,
    }

    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(BASE, headers=HEADERS, json=payload)

    # Возвращаемой строкой занимаемся тут
    if r.status_code >= 400:
        raise RuntimeError(f"{model} failed: {r.status_code} {r.text[:400]}")

    data = r.json()
    text = _extract_text(data)
    if not text.strip():
        raise RuntimeError(f"{model} empty output")
    return text

async def llm_chat(prompt: str) -> str:
    try:
        return await _call_model(PRIMARY, prompt)
    except Exception:
        try:
            return await _call_model(FALLBACK, prompt)
        except Exception:
            return ERR_MSG

# ====== ДОБАВЛЕНО: открытая диагностика без логов Render ======

async def _probe_once(model: str, prompt: str = "ping") -> dict:
    """
    Возвращает подробности вызова одной модели: status_code, кусок тела, ошибка.
    Ничего не прячет, чтобы можно было видеть реальную причину 401/404/429/5xx.
    """
    result = {"model": model}
    if not OPENROUTER_KEY:
        result.update({
            "ok": False,
            "error": "OPENROUTER_KEY is empty (не найден ни в ENV, ни в config)",
        })
        return result

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Диагностика соединения."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 8,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(BASE, headers=HEADERS, json=payload)
    except Exception as e:
        result.update({"ok": False, "exception": repr(e)})
        return result

    result["status_code"] = r.status_code
    result["x_request_id"] = r.headers.get("x-request-id")
    body = r.text or ""
    result["body_preview"] = body[:1200]
    result["ok"] = (200 <= r.status_code < 300)
    return result

async def probe_models() -> dict:
    """
    Пробует PRIMARY и FALLBACK, плюс показывает, что за ключ/хедеры видит сервис.
    """
    return {
        "env_detected": {
            "PRIMARY": PRIMARY,
            "FALLBACK": FALLBACK,
            "has_OPENROUTER_KEY": bool(OPENROUTER_KEY),
            "OPENROUTER_KEY_len": len(OPENROUTER_KEY or ""),
            "HTTP_Referer": APP_SITE,
            "X_Title": APP_NAME,
            "BASE": BASE,
        },
        "primary": await _probe_once(PRIMARY),
        "fallback": await _probe_once(FALLBACK),
    }
