CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    is_vip BOOLEAN DEFAULT TRUE,
    banned BOOLEAN DEFAULT FALSE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sessions (
    telegram_id BIGINT PRIMARY KEY,
    username TEXT REFERENCES users(username) ON DELETE CASCADE,
    logged_in BOOLEAN DEFAULT TRUE,
    platform TEXT,
    market_type TEXT,
    asset TEXT,
    timeframe TEXT,
    utc_time TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS signals (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    username TEXT,
    platform TEXT,
    market_type TEXT,
    asset TEXT,
    timeframe TEXT,
    utc_time TEXT,
    signal TEXT,
    confidence INT,
    trend_strength TEXT,
    rsi NUMERIC(10,2),
    ema9 NUMERIC(18,6),
    ema21 NUMERIC(18,6),
    macd_hist NUMERIC(18,6),
    pattern TEXT,
    reasons TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_sessions_telegram_id ON sessions(telegram_id);
CREATE INDEX IF NOT EXISTS idx_signals_telegram_created ON signals(telegram_id, created_at DESC);


CREATE TABLE IF NOT EXISTS platforms (
    id BIGSERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS market_categories (
    id BIGSERIAL PRIMARY KEY,
    platform_name TEXT NOT NULL,
    name TEXT NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(platform_name, name)
);

CREATE TABLE IF NOT EXISTS trading_assets (
    id BIGSERIAL PRIMARY KEY,
    platform_name TEXT NOT NULL,
    market_name TEXT NOT NULL,
    name TEXT NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(platform_name, market_name, name)
);

CREATE TABLE IF NOT EXISTS signal_timeframes (
    id BIGSERIAL PRIMARY KEY,
    platform_name TEXT NOT NULL,
    name TEXT NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(platform_name, name)
);

CREATE TABLE IF NOT EXISTS utc_sessions (
    id BIGSERIAL PRIMARY KEY,
    platform_name TEXT NOT NULL,
    name TEXT NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(platform_name, name)
);

CREATE TABLE IF NOT EXISTS license_keys (
    id BIGSERIAL PRIMARY KEY,
    license_key TEXT UNIQUE NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    max_devices INT DEFAULT 1,
    used_devices INT DEFAULT 0,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS license_sessions (
    id BIGSERIAL PRIMARY KEY,
    license_key TEXT NOT NULL REFERENCES license_keys(license_key) ON DELETE CASCADE,
    telegram_id BIGINT NOT NULL,
    first_login_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(license_key, telegram_id)
);
