import re, time, random
from .config import (
    ONE_LINERS, INTERJ, maybe_quack,
    DM_MAX_WORDS, GROUP_MAX_WORDS,
    GROUP_RANDOM_QUACK, COOLDOWN_SEC
)
from . import llm

_last_group_post = {}  # chat_id -> ts

def shortify(s: str, max_words=25) -> str:
    if not s:
        return s
    w = s.split()
    return " ".join(w[:max_words])

async def reply_dm(user_text: str) -> str:
    t = (user_text or "").lower()
    # Fast canned replies
    if any(x in t for x in ["привет","ку","здарова","салам","йоу","йо"]):
        return random.choice(["йо", "ку", "кря-привет"])
    if "погода" in t:
        return maybe_quack("На небе своё кино. Проверь местный прогноз — он меняется быстро.")
    # LLM short
    sys = (
        "Ты — дерзкий, тёплый гусь. Отвечай очень коротко (1–2 фразы, ≤25 слов). "
        "Иногда добавляй ‘Кря’. Без 18+ и криминала."
    )
    msgs = [
        {"role": "system", "content": sys},
        {"role": "user", "content": user_text}
    ]
    out = await llm.llm_chat(msgs, max_tokens=80)
    return maybe_quack(shortify(out, DM_MAX_WORDS))

async def maybe_group_interject(chat_id: int):
    now = time.time()
    last = _last_group_post.get(chat_id, 0)
    if now - last < COOLDOWN_SEC:
        return None
    if random.random() < GROUP_RANDOM_QUACK:
        _last_group_post[chat_id] = now
        return random.choice(ONE_LINERS + INTERJ)
    return None

async def reply_group(event, text: str, mentioned: bool):
    t = (text or "").lower()
    # Mention or keywords => respond almost always
    if mentioned or re.search(r"\b(гусь|утка|кря)\b", t):
        if random.random() < 0.10:
            return {"meme": True}
        return maybe_quack(shortify(random.choice(ONE_LINERS), GROUP_MAX_WORDS))
    # Random interjection with cooldown
    inter = await maybe_group_interject(event["chat_id"])
    if inter:
        return inter
    return None
