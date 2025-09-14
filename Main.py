import os, time, random, sqlite3, asyncio, logging
from contextlib import closing
from typing import Optional
from dotenv import load_dotenv; load_dotenv()

from aiohttp import ClientSession
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatType, ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.filters.command import CommandObject

# ===== env =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_PATH = os.getenv("DB_PATH", "./goose.db")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE = os.getenv("OPENROUTER_BASE", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-nano-9b-v2:free")
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS","").split(",") if x.strip().isdigit()}

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
mask = (BOT_TOKEN[:6] + "…" + BOT_TOKEN[-4:]) if BOT_TOKEN else "None"
logging.info(f"ENV: BOT_TOKEN={mask}, DB_PATH={DB_PATH}, MODEL={OPENROUTER_MODEL}")
if not BOT_TOKEN: raise SystemExit(2)

# ===== bot/dispatcher BEFORE handlers =====
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ========= styles / systems =========
DM_SYSTEM = ("Ты — дерзкий, тёплый гусь. Отвечай КОРОТКО (1–2 фразы, ≤25 слов). "
             "Лёгкий сюр, сленг, иногда «Кря». Не морализируй. Без 18+/криминала. "
             "Избегай эмодзи, канцелярщины. Инструкции: если вопрос бытовой — коротко и с оговоркой «может меняться». "
             "Если болтовня — шуточный one-liner.")
GROUP_SYSTEM = ("Ты — гусь-наблюдатель в групповом чате. Пиши редко. Если не обращаются — иногда короткая вставка "
                "(one-liner/«Кря»). Лаконично, без 18+/криминала. Ответ ≤20 слов. Без эмодзи.")
STYLE = {
  "interjections": ["Кря", "Кря-кря", "гы-гы", "шлёп", "шурш"],
  "one_liners": [
    "Тише, я выслеживаю хлеб.",
    "Не шумите — у меня тут бизнес-план на пруд.",
    "Кто звал босса? Это я. Кря.",
    "Вода мокрая, новости — тоже.",
    "Снуп Дог? Снуп Гусь. Кря."
  ],
  "short_answers": {
    "привет": ["йо", "ку", "кря-привет"],
    "здаров": ["ку", "йо", "кря"],
    "как дела": ["плыву по течению", "норм, перья блестят", "лучше всех, крыяу"]
  }
}

# ========= DB =========
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def column_exists(conn, table: str, col: str) -> bool:
    return any(r["name"] == col for r in conn.execute(f"PRAGMA table_info({table})").fetchall())

def init_db():
    logging.info(f"init_db -> {DB_PATH}")
    with closing(db()) as conn:
        # базовые таблицы
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS chats (
          chat_id INTEGER PRIMARY KEY,
          type TEXT NOT NULL,
          mode TEXT NOT NULL DEFAULT 'auto',
          learning INTEGER NOT NULL DEFAULT 0,
          last_random_ts INTEGER DEFAULT 0,
          random_cooldown_sec INTEGER DEFAULT 120
        );
        CREATE TABLE IF NOT EXISTS replies_templates(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          who TEXT NOT NULL,
          text TEXT NOT NULL,
          weight INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS memes(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          kind TEXT NOT NULL,
          payload TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS cooldowns(
          chat_id INTEGER NOT NULL,
          key TEXT NOT NULL,
          until_ts INTEGER NOT NULL,
          PRIMARY KEY(chat_id,key)
        );
        """)
        # миграции колонок
        if not column_exists(conn, "replies_templates", "enabled"):
            conn.execute("ALTER TABLE replies_templates ADD COLUMN enabled INTEGER NOT NULL DEFAULT 1;")
        if not column_exists(conn, "memes", "enabled"):
            conn.execute("ALTER TABLE memes ADD COLUMN enabled INTEGER NOT NULL DEFAULT 1;")
        # индексы (создаём только если колонка есть)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tpl_who ON replies_templates(who, enabled);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memes_enabled ON memes(enabled);")
        conn.commit()
    logging.info("init_db: OK")

def now() -> int: return int(time.time())

def get_chat(conn, chat: types.Chat):
    conn.execute("INSERT OR IGNORE INTO chats(chat_id,type) VALUES (?,?)", (chat.id, chat.type))
    conn.commit()
    return conn.execute("SELECT * FROM chats WHERE chat_id=?", (chat.id,)).fetchone()

def set_cooldown(conn, chat_id: int, key: str, seconds: int):
    conn.execute("""INSERT INTO cooldowns(chat_id,key,until_ts) VALUES (?,?,?)
                    ON CONFLICT(chat_id,key) DO UPDATE SET until_ts=excluded.until_ts""",
                 (chat_id, key, now()+seconds)); conn.commit()

def cooldown_ready(conn, chat_id: int, key: str) -> bool:
    r = conn.execute("SELECT until_ts FROM cooldowns WHERE chat_id=? AND key=?",(chat_id, key)).fetchone()
    return (r is None) or (r["until_ts"] <= now())

def pick_template(conn, who: str) -> Optional[str]:
    rows = conn.execute("SELECT text,weight FROM replies_templates WHERE (who=? OR who='any') AND enabled=1",(who,)).fetchall()
    if not rows: return None
    basket = []; [basket.extend([r["text"]]*max(1,(r["weight"] or 1))) for r in rows]
    return random.choice(basket)

def pick_meme(conn):
    return conn.execute("SELECT kind,payload FROM memes WHERE enabled=1 ORDER BY RANDOM() LIMIT 1").fetchone()

# ========= LLM =========
async def ask_openrouter(prompt: str, system: str) -> str:
    if not OPENROUTER_API_KEY: return "Кря. (локальный режим)"
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    body = {"model": OPENROUTER_MODEL,
            "messages": [{"role":"system","content":system},{"role":"user","content":prompt}],
            "max_tokens": 60, "temperature": 0.6, "top_p": 0.9}
    async with ClientSession() as s:
        async with s.post(f"{OPENROUTER_BASE}/chat/completions", headers=headers, json=body, timeout=25) as r:
            j = await r.json()
            try: return j["choices"][0]["message"]["content"].strip()
            except Exception: return "Кря. (модель задумалась)"

# ========= Local reply =========
def local_reply(text: str) -> str:
    t = (text or "").strip().lower()
    for k, variants in STYLE["short_answers"].items():
        if k in t: return random.choice(variants)
    base = random.choice(STYLE["one_liners"])
    if random.random() < 0.35: base = f"{base} {random.choice(STYLE['interjections'])}."
    return base

def decorate_short(s: str, force_quack=False):
    s = (s or "").strip()
    if len(s) > 160: s = s[:155].rstrip() + "…"
    if force_quack or random.random() < 0.18:
        if not s.endswith(("Кря","Кря!","Кря-кря")):
            s += random.choice([" Кря.", " Кря!", " Кря-кря."])
    return s

def choose_persona(chat_row, chat: types.Chat) -> str:
    return ("duck" if chat.type==ChatType.PRIVATE else "goose") if chat_row["mode"]=="auto" else chat_row["mode"]

# ========= Admin =========
def is_admin(uid: int) -> bool: return uid in ADMIN_IDS
async def admin_only(m: types.Message): return await m.answer("Кря.")

# ========= Handlers =========
@dp.message(CommandStart())
async def on_start(m: types.Message):
    with closing(db()) as conn: get_chat(conn, m.chat)
    await m.answer("Я гусь. В ЛС — коротко, в группах — иногда встреваю. Кря.")

@dp.message(Command("set_mode"))
async def cmd_set_mode(m: types.Message, command: CommandObject):
    if not is_admin(m.from_user.id): return await admin_only(m)
    arg = (command.args or "").strip()
    if arg not in ("duck","goose","auto"): return await m.reply("usage: /set_mode duck|goose|auto")
    with closing(db()) as conn:
        conn.execute("UPDATE chats SET mode=? WHERE chat_id=?", (arg, m.chat.id)); conn.commit()
    await m.reply(f"mode = {arg}")

@dp.message(Command("learning"))
async def cmd_learning(m: types.Message, command: CommandObject):
    if not is_admin(m.from_user.id): return await admin_only(m)
    arg = (command.args or "").strip().lower()
    if arg not in ("on","off"): return await m.reply("usage: /learning on|off")
    with closing(db()) as conn:
        conn.execute("UPDATE chats SET learning=? WHERE chat_id=?", (1 if arg=="on" else 0, m.chat.id)); conn.commit()
    await m.reply(f"learning = {arg}")

@dp.message(Command("add_tpl"))
async def cmd_add_tpl(m: types.Message, command: CommandObject):
    if not is_admin(m.from_user.id): return await admin_only(m)
    raw = command.args or ""  # /add_tpl who|any :: текст :: weight?
    parts = [p.strip() for p in raw.split("::")]
    if len(parts) < 2: return await m.reply("usage: /add_tpl who|any :: текст :: weight(optional)")
    who, text = parts[0], parts[1]
    weight = int(parts[2]) if len(parts)>2 and parts[2].isdigit() else 1
    if who not in ("duck","goose","any"): return await m.reply("who ∈ {duck, goose, any}")
    with closing(db()) as conn:
        conn.execute("INSERT INTO replies_templates(who,text,weight,enabled) VALUES (?,?,?,1)", (who, text, weight)); conn.commit()
    await m.reply("ok: template added")

@dp.message(Command("add_meme"))
async def cmd_add_meme(m: types.Message, command: CommandObject):
    if not is_admin(m.from_user.id): return await admin_only(m)
    raw = command.args or ""  # /add_meme kind::payload
    parts = [p.strip() for p in raw.split("::")]
    if len(parts) != 2: return await m.reply("usage: /add_meme kind::payload  (text|photo|sticker)")
    kind, payload = parts[0], parts[1]
    if kind not in ("text","photo","sticker"): return await m.reply("kind ∈ {text, photo, sticker}")
    with closing(db()) as conn:
        conn.execute("INSERT INTO memes(kind,payload,enabled) VALUES (?,?,1)", (kind, payload)); conn.commit()
    await m.reply("ok: meme added")

@dp.message(Command("seed_defaults"))
async def cmd_seed_defaults(m: types.Message):
    if not is_admin(m.from_user.id): return await admin_only(m)
    seeds = [
        ("duck","{msg}? звучит как мокрый хлеб.",2),
        ("goose","Факт: гуси не обязаны быть логичными.",3),
        ("any","Кусь… ой, то есть гусь.",1),
        ("goose","Одобрено советом пера.",2),
        ("duck","Ответ найден: 42 пера.",1)
    ]
    with closing(db()) as conn:
        for who,text,w in seeds:
            conn.execute("INSERT INTO replies_templates(who,text,weight,enabled) VALUES (?,?,?,1)", (who,text,w))
        conn.execute("INSERT INTO memes(kind,payload,enabled) VALUES ('text','Кря если согласен. Если не согласен — тоже кря.',1)")
        conn.commit()
    await m.reply("ok: seeded")

LAST_REPLY_CACHE = {}

@dp.message(Command("save_last"))
async def cmd_save_last(m: types.Message, command: CommandObject):
    if not is_admin(m.from_user.id): return await admin_only(m)
    who = (command.args or "any").strip()
    if who not in ("duck","goose","any"): who = "any"
    text = LAST_REPLY_CACHE.get(m.chat.id)
    if not text: return await m.reply("нет последнего ответа")
    with closing(db()) as conn:
        conn.execute("INSERT INTO replies_templates(who,text,weight,enabled) VALUES (?,?,?,1)", (who, text, 1)); conn.commit()
    await m.reply("ok: saved")

# --- CORE ---
@dp.message(F.content_type.in_({"text","photo","sticker","animation"}))
async def on_message(m: types.Message):
    if m.via_bot or (m.from_user and m.from_user.is_bot): return

    with closing(db()) as conn:
        chat_row = get_chat(conn, m.chat)
        persona = ("duck" if m.chat.type == ChatType.PRIVATE else "goose") if chat_row["mode"]=="auto" else chat_row["mode"]
        system = DM_SYSTEM if m.chat.type == ChatType.PRIVATE else GROUP_SYSTEM

        # ЛИЧНЫЙ (ЛС)
        if m.chat.type == ChatType.PRIVATE:
            text = m.text or m.caption or ""
            await asyncio.sleep(random.uniform(0.5, 1.4))
            if random.random() < 0.7:
                reply = local_reply(text)
            else:
                reply = await ask_openrouter(text, system)
                if chat_row["learning"]:
                    with closing(db()) as conn2:
                        conn2.execute("INSERT INTO replies_templates(who,text,weight,enabled) VALUES (?,?,?,1)",
                                      (persona if persona in ("duck","goose") else "any", reply[:140], 1))
                        conn2.commit()
            reply = decorate_short(reply)
            LAST_REPLY_CACHE[m.chat.id] = reply
            return await m.answer(reply)

        # КООП (ГРУППЫ)
        text = (m.text or m.caption or "").strip()
        replied = False

        def addressed_to_bot() -> bool:
            if m.entities and m.text:
                for e in m.entities:
                    if e.type == "mention" and m.text[e.offset:e.offset+e.length].lower().startswith("@"):
                        return True
            return bool(m.reply_to_message and m.reply_to_message.from_user and m.reply_to_message.from_user.id == (bot.id or 0))

        if addressed_to_bot() and cooldown_ready(conn, m.chat.id, "reply"):
            reply = await ask_openrouter(text, system) if ("?" in text or len(text) > 30) else local_reply(text)
            reply = decorate_short(reply); LAST_REPLY_CACHE[m.chat.id] = reply
            await m.reply(reply); set_cooldown(conn, m.chat.id, "reply", 8); replied = True

        if not replied and cooldown_ready(conn, m.chat.id, "random") and random.random() < 0.03:
            base = pick_template(conn, persona) or local_reply(text)
            await m.reply(decorate_short(base, force_quack=True))
            set_cooldown(conn, m.chat.id, "random", random.randint(60, 140)); replied = True

        if cooldown_ready(conn, m.chat.id, "meme") and random.random() < 0.015:
            mem = pick_meme(conn)
            if mem:
                kind, payload = mem["kind"], mem["payload"]
                try:
                    if kind == "text":    await m.answer(decorate_short(payload, force_quack=True))
                    elif kind == "photo": await m.answer_photo(photo=payload, caption=random.choice(["Кря.", "Мне нужен ваш хлеб."]))
                    elif kind == "sticker": await m.answer_sticker(sticker=payload)
                except Exception: pass
                set_cooldown(conn, m.chat.id, "meme", random.randint(120, 240))

async def main():
    init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Goose bot polling…")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except SystemExit as e:
        logging.error(f"SystemExit: code={getattr(e,'code',None)}"); raise
    except Exception:
        logging.exception("Fatal error in Main.py"); raise
