PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS chats (
  chat_id INTEGER PRIMARY KEY,
  type TEXT NOT NULL,                    -- private|group|supergroup|channel
  mode TEXT NOT NULL DEFAULT 'auto',     -- 'duck'|'goose'|'auto'
  learning INTEGER NOT NULL DEFAULT 0,   -- 0|1 (режим «самообучения»)
  last_random_ts INTEGER DEFAULT 0,
  random_cooldown_sec INTEGER DEFAULT 120
);

CREATE TABLE IF NOT EXISTS users (
  user_id INTEGER PRIMARY KEY,
  username TEXT,
  first_name TEXT,
  last_seen_ts INTEGER
);

CREATE TABLE IF NOT EXISTS kv_cache (
  key TEXT PRIMARY KEY,
  value TEXT,
  updated_ts INTEGER
);

CREATE TABLE IF NOT EXISTS memes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT NOT NULL,                    -- 'text'|'photo'|'sticker'
  payload TEXT NOT NULL,                 -- текст или file_id / ссылка
  enabled INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS replies_templates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  who TEXT NOT NULL,                     -- 'duck'|'goose'|'any'
  text TEXT NOT NULL,
  weight INTEGER DEFAULT 1,
  enabled INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS cooldowns (
  chat_id INTEGER NOT NULL,
  key TEXT NOT NULL,                     -- 'random'|'reply'|'meme'
  until_ts INTEGER NOT NULL,
  PRIMARY KEY (chat_id, key)
);

-- индексы
CREATE INDEX IF NOT EXISTS idx_memes_enabled ON memes(enabled);
CREATE INDEX IF NOT EXISTS idx_tpl_who ON replies_templates(who,enabled);
