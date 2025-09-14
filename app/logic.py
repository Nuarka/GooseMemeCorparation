import re, time, random
from .config import (
    ONE_LINERS, INTERJ, maybe_quack,
    DM_MAX_WORDS, GROUP_MAX_WORDS,
    GROUP_RANDOM_QUACK, COOLDOWN_SEC
)
from . import llm

_last_group_post = {}  # chat_id -> ts
ERR_SIGNATURE = "модель временно недоступна"

def shortify(s: str, max_words=25) -> str:
    if not s:
        return s
    w = s.split()
    return " ".join(w[:max_words])

async def reply_dm(user_text: str) -> str:
    t = (user_text or "").lower()

    # Быстрые заготовки без LLM
    if any(x in t for x in ["привет", "ку", "здарова", "салам", "йоу", "йо"]):
        return random.choice(["йо", "ку", "кря-привет"])
    if "погода" in t:
        return maybe_quack("На небе своё кино. Проверь местный прогноз — он меняется быстро.")

    # Короткий ответ через LLM с graceful fallback
    prompt = (
        "Отвечай очень коротко: 1–2 фразы, не более {maxw} слов. "
        "Стиль — дерзкий, тёплый гусь. Изредка добавляй «Кря». "
        "Без 18+ и криминала.\n\n"
        "Вопрос пользователя:\n{q}"
    ).format(maxw=DM_MAX_WORDS, q=user_text)

    try:
        out = await llm.llm_chat(prompt)
    except Exception:
        out = random.choice(ONE_LINERS)

    # Если пришла наша заглушка — подменяем
    if isinstance(out, str) and ERR_SIGNATURE in out.lower():
        out = random.choice(ONE_LINERS)

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

    # Если упомянули бота или триггер-слова — отвечаем почти всегда
    if mentioned or re.search(r"\b(гусь|утка|кря)\b", t):
        # Иногда — отдаём мем-заглушку (для твоей логики sendMessage с "meme": True)
        if random.random() < 0.10:
            return {"meme": True}

        # Пытаемся ответить LLM коротко; если не получилось — однолайнер
        prompt = (
            "Групповой чат. Дай очень короткую реплику в тему: 1 фраза, максимум {maxw} слов. "
            "Стиль — дерзкий, тёплый гусь. Без 18+ и криминала. "
            "Можно вставить «Кря».\n\n"
            "Сообщение:\n{q}"
        ).format(maxw=GROUP_MAX_WORDS, q=text)

        try:
            out = await llm.llm_chat(prompt)
        except Exception:
            out = random.choice(ONE_LINERS)

        if isinstance(out, str) and ERR_SIGNATURE in out.lower():
            out = random.choice(ONE_LINERS)

        return maybe_quack(shortify(out, GROUP_MAX_WORDS))

    # Иначе — редкие реплики с кулдауном
    inter = await maybe_group_interject(event["chat_id"])
    if inter:
        return inter
    return None
