import os, json, random

# Required env
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "meta-llama/llama-3.1-8b-instruct:free")
PUBLIC_URL = os.getenv("PUBLIC_URL", "")  # Public base URL for webhook

# Behavior
QUACK_FREQ_DM = float(os.getenv("QUACK_FREQ_DM", 0.25))
GROUP_REACT_PROB = float(os.getenv("GROUP_REACT_PROB", 0.08))
GROUP_RANDOM_QUACK = float(os.getenv("GROUP_RANDOM_QUACK", 0.04))
COOLDOWN_SEC = int(os.getenv("COOLDOWN_SEC", 45))
DM_MAX_WORDS = int(os.getenv("DM_MAX_WORDS", 25))
GROUP_MAX_WORDS = int(os.getenv("GROUP_MAX_WORDS", 20))

# Phrases
try:
    with open("assets/one_liners.json", "r", encoding="utf-8") as f:
        ONE_LINERS = json.load(f)
except Exception:
    ONE_LINERS = [
        "Тише, я выслеживаю хлеб.",
        "Снуп Гусь на связи.",
        "Кто звал босса? Это я. Кря.",
        "Вода мокрая, новости — тоже.",
        "У меня делегирование — на пруд."
    ]

INTERJ = ["Кря", "Кря-кря", "гы-гы", "шурш"]

def maybe_quack(text: str, freq: float = QUACK_FREQ_DM) -> str:
    if not text:
        return random.choice(INTERJ) if random.random() < freq else text
    return text if random.random() > freq else (text + " " + random.choice(INTERJ))
