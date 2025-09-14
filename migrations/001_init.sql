CREATE TABLE IF NOT EXISTS users (
  id BIGSERIAL PRIMARY KEY,
  tg_id BIGINT UNIQUE NOT NULL,
  tz TEXT DEFAULT 'Asia/Almaty',
  locale TEXT DEFAULT 'ru',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS groups (
  id BIGSERIAL PRIMARY KEY,
  tg_chat_id BIGINT UNIQUE NOT NULL,
  settings_json JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
  id BIGSERIAL PRIMARY KEY,
  chat_id BIGINT NOT NULL,
  user_id BIGINT,
  role TEXT NOT NULL, -- 'user' | 'assistant'
  content TEXT NOT NULL,
  tokens INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS reminders (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT,
  persona_id BIGINT,
  next_at TIMESTAMPTZ,
  rrule TEXT,
  payload JSONB DEFAULT '{}'::jsonb,
  status TEXT DEFAULT 'active'
);
