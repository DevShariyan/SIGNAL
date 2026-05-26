# NEON CACHED PLAN FIX V56: asyncpg statement_cache_size=0 enabled
import os
import asyncpg
from datetime import datetime, timedelta, timezone

pool = None
dynamic_tables_ready = False
license_tables_ready = False
bot_settings_ready = False
signal_session_columns_ready = False

async def init_db():
    global pool
    if pool:
        return pool

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL missing. Add Neon connection string in Render env.")

    pool = await asyncpg.create_pool(
        dsn=database_url,
        min_size=1,
        max_size=5,
        command_timeout=10,
        statement_cache_size=0,
    )

    async with pool.acquire() as conn:
        await conn.execute("""
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
        
        CREATE TABLE IF NOT EXISTS bot_platforms (
            id BIGSERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        INSERT INTO bot_platforms(name, active)
        VALUES('Quotex', TRUE), ('Binomo', TRUE), ('Pocket Option', TRUE), ('Olymp Trade', TRUE), ('ExpertOption', TRUE)
        ON CONFLICT(name) DO NOTHING;

        CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
        CREATE INDEX IF NOT EXISTS idx_sessions_telegram_id ON sessions(telegram_id);
        CREATE INDEX IF NOT EXISTS idx_signals_telegram_created ON signals(telegram_id, created_at DESC);
        """)

    return pool

async def create_user(username, password, days):
    p = await init_db()
    expires_at = datetime.now(timezone.utc) + timedelta(days=int(days))
    async with p.acquire() as conn:
        return await conn.fetchrow("""
            INSERT INTO users(username, password, is_vip, banned, expires_at)
            VALUES($1, $2, TRUE, FALSE, $3)
            ON CONFLICT(username)
            DO UPDATE SET password=$2, is_vip=TRUE, banned=FALSE, expires_at=$3
            RETURNING username, expires_at, banned, is_vip
        """, username.lower(), password, expires_at)

async def get_user(username):
    p = await init_db()
    async with p.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM users WHERE username=$1", username.lower())

def user_is_active(user):
    if not user or user["banned"] or not user["is_vip"]:
        return False
    return user["expires_at"] > datetime.now(timezone.utc)

async def list_users(limit=50):
    p = await init_db()
    async with p.acquire() as conn:
        return await conn.fetch("""
            SELECT username, banned, is_vip, expires_at
            FROM users
            ORDER BY created_at DESC
            LIMIT $1
        """, limit)

async def set_ban(username, banned=True):
    p = await init_db()
    async with p.acquire() as conn:
        return await conn.fetchrow("""
            UPDATE users SET banned=$2 WHERE username=$1
            RETURNING username, banned
        """, username.lower(), banned)

async def login_session(telegram_id, username):
    p = await init_db()
    async with p.acquire() as conn:
        return await conn.fetchrow("""
            INSERT INTO sessions(telegram_id, username, logged_in, updated_at)
            VALUES($1, $2, TRUE, NOW())
            ON CONFLICT(telegram_id)
            DO UPDATE SET username=$2, logged_in=TRUE, platform=NULL, market_type=NULL,
            asset=NULL, timeframe=NULL, utc_time=NULL, updated_at=NOW()
            RETURNING *
        """, int(telegram_id), username.lower())

async def update_session(telegram_id, **kwargs):
    allowed = {"platform", "market_type", "asset", "timeframe", "utc_time", "logged_in"}
    fields = []
    values = []
    for k, v in kwargs.items():
        if k in allowed:
            values.append(v)
            fields.append(f"{k}=${len(values)+1}")
    if not fields:
        return await get_session(telegram_id)
    values.insert(0, int(telegram_id))
    sql = f"""
        UPDATE sessions SET {', '.join(fields)}, updated_at=NOW()
        WHERE telegram_id=$1
        RETURNING *
    """
    p = await init_db()
    async with p.acquire() as conn:
        return await conn.fetchrow(sql, *values)

async def get_session(telegram_id):
    p = await init_db()
    async with p.acquire() as conn:
        return await conn.fetchrow("""
            SELECT s.*, u.expires_at, u.banned, u.is_vip
            FROM sessions s
            JOIN users u ON u.username=s.username
            WHERE s.telegram_id=$1 AND s.logged_in=TRUE
        """, int(telegram_id))


async def auto_logout_if_expired(telegram_id):
    sess = await get_session(telegram_id)
    if not sess:
        return False, None
    active = (not sess["banned"]) and sess["is_vip"] and sess["expires_at"] > datetime.now(timezone.utc)
    if not active:
        await logout_session(telegram_id)
        return True, sess
    return False, sess

async def session_active(telegram_id):
    sess = await get_session(telegram_id)
    if not sess:
        return False, None
    active = (not sess["banned"]) and sess["is_vip"] and sess["expires_at"] > datetime.now(timezone.utc)
    if not active:
        await logout_session(telegram_id)
        return False, None
    return True, sess

async def logout_session(telegram_id):
    p = await init_db()
    async with p.acquire() as conn:
        await conn.execute("DELETE FROM sessions WHERE telegram_id=$1", int(telegram_id))

async def add_signal(telegram_id, username, data):
    p = await init_db()
    async with p.acquire() as conn:
        return await conn.fetchrow("""
            INSERT INTO signals(
                telegram_id, username, platform, market_type, asset, timeframe, utc_time,
                signal, confidence, trend_strength, rsi, ema9, ema21, macd_hist, pattern, reasons
            )
            VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)
            RETURNING id, created_at
        """,
        int(telegram_id), username, data.get("platform"), data.get("market_type"),
        data.get("asset"), data.get("timeframe"), data.get("utc_time"),
        data.get("signal"), data.get("confidence"), data.get("trend_strength"),
        data.get("rsi"), data.get("ema9"), data.get("ema21"), data.get("macd_hist"),
        data.get("pattern"), data.get("reasons"))

async def get_history(telegram_id, limit=10):
    p = await init_db()
    async with p.acquire() as conn:
        return await conn.fetch("""
            SELECT created_at, platform, market_type, asset, timeframe, utc_time, signal, confidence
            FROM signals
            WHERE telegram_id=$1
            ORDER BY created_at DESC
            LIMIT $2
        """, int(telegram_id), limit)


async def get_platforms():
    p = await init_db()
    async with p.acquire() as conn:
        rows = await conn.fetch("""
            SELECT name FROM bot_platforms
            WHERE active=TRUE
            ORDER BY id ASC
        """)
    return [r["name"] for r in rows] or ["Quotex", "Binomo"]

async def add_platform(name):
    p = await init_db()
    async with p.acquire() as conn:
        return await conn.fetchrow("""
            INSERT INTO bot_platforms(name, active)
            VALUES($1, TRUE)
            ON CONFLICT(name) DO UPDATE SET active=TRUE
            RETURNING name, active
        """, name.strip())

async def remove_platform(name):
    p = await init_db()
    async with p.acquire() as conn:
        return await conn.fetchrow("""
            UPDATE bot_platforms SET active=FALSE
            WHERE LOWER(name)=LOWER($1)
            RETURNING name, active
        """, name.strip())


async def get_active_session_by_username(username):
    p = await init_db()
    async with p.acquire() as conn:
        return await conn.fetchrow("""
            SELECT telegram_id, username, updated_at
            FROM sessions
            WHERE username=$1 AND logged_in=TRUE
            LIMIT 1
        """, username.lower())

async def force_logout_username(username):
    p = await init_db()
    async with p.acquire() as conn:
        await conn.execute("DELETE FROM sessions WHERE username=$1", username.lower())


async def ensure_dynamic_tables():
    global dynamic_tables_ready
    if dynamic_tables_ready:
        return
    p = await init_db()
    async with p.acquire() as conn:
        await conn.execute("""
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
        """)
    dynamic_tables_ready = True

async def add_dynamic_platform(name):
    await ensure_dynamic_tables()
    p = await init_db()
    async with p.acquire() as conn:
        return await conn.fetchrow("""
            INSERT INTO platforms(name, active)
            VALUES($1, TRUE)
            ON CONFLICT(name) DO UPDATE SET active=TRUE
            RETURNING name
        """, name.strip())

async def add_dynamic_market(platform, name):
    await ensure_dynamic_tables()
    p = await init_db()
    async with p.acquire() as conn:
        return await conn.fetchrow("""
            INSERT INTO market_categories(platform_name, name, active)
            VALUES($1, $2, TRUE)
            ON CONFLICT(platform_name, name) DO UPDATE SET active=TRUE
            RETURNING platform_name, name
        """, platform.strip(), name.strip())

async def add_dynamic_asset(platform, market, name):
    await ensure_dynamic_tables()
    p = await init_db()
    async with p.acquire() as conn:
        return await conn.fetchrow("""
            INSERT INTO trading_assets(platform_name, market_name, name, active)
            VALUES($1, $2, $3, TRUE)
            ON CONFLICT(platform_name, market_name, name) DO UPDATE SET active=TRUE
            RETURNING platform_name, market_name, name
        """, platform.strip(), market.strip(), name.strip())

async def add_dynamic_timeframe(platform, name):
    await ensure_dynamic_tables()
    p = await init_db()
    async with p.acquire() as conn:
        return await conn.fetchrow("""
            INSERT INTO signal_timeframes(platform_name, name, active)
            VALUES($1, $2, TRUE)
            ON CONFLICT(platform_name, name) DO UPDATE SET active=TRUE
            RETURNING platform_name, name
        """, platform.strip(), name.strip())

async def add_dynamic_utc(platform, name):
    await ensure_dynamic_tables()
    p = await init_db()
    async with p.acquire() as conn:
        return await conn.fetchrow("""
            INSERT INTO utc_sessions(platform_name, name, active)
            VALUES($1, $2, TRUE)
            ON CONFLICT(platform_name, name) DO UPDATE SET active=TRUE
            RETURNING platform_name, name
        """, platform.strip(), name.strip())

async def get_dynamic_platforms():
    await ensure_dynamic_tables()
    p = await init_db()
    async with p.acquire() as conn:
        rows = await conn.fetch("SELECT name FROM platforms WHERE active=TRUE ORDER BY id")
    return [r["name"] for r in rows]

async def get_dynamic_markets(platform):
    await ensure_dynamic_tables()
    p = await init_db()
    async with p.acquire() as conn:
        rows = await conn.fetch("""
            SELECT name FROM market_categories
            WHERE platform_name=$1 AND active=TRUE ORDER BY id
        """, platform)
    return [r["name"] for r in rows]

async def get_dynamic_assets(platform, market):
    await ensure_dynamic_tables()
    p = await init_db()
    async with p.acquire() as conn:
        rows = await conn.fetch("""
            SELECT name FROM trading_assets
            WHERE platform_name=$1 AND market_name=$2 AND active=TRUE ORDER BY id
        """, platform, market)
    return [r["name"] for r in rows]

async def get_dynamic_timeframes(platform):
    await ensure_dynamic_tables()
    p = await init_db()
    async with p.acquire() as conn:
        rows = await conn.fetch("""
            SELECT name FROM signal_timeframes
            WHERE platform_name=$1 AND active=TRUE ORDER BY id
        """, platform)
    return [r["name"] for r in rows]

async def get_dynamic_utc(platform):
    await ensure_dynamic_tables()
    p = await init_db()
    async with p.acquire() as conn:
        rows = await conn.fetch("""
            SELECT name FROM utc_sessions
            WHERE platform_name=$1 AND active=TRUE ORDER BY id
        """, platform)
    return [r["name"] for r in rows]


# ================= LICENSE KEY LOGIN SYSTEM =================

async def ensure_license_tables():
    global license_tables_ready
    if license_tables_ready:
        return
    p = await init_db()
    async with p.acquire() as conn:
        await conn.execute("""
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
        """)
    license_tables_ready = True

async def create_license_key(license_key, days, max_devices=1):
    await ensure_license_tables()
    p = await init_db()
    expires_at = datetime.now(timezone.utc) + timedelta(days=int(days))
    async with p.acquire() as conn:
        return await conn.fetchrow("""
            INSERT INTO license_keys(license_key, active, max_devices, used_devices, expires_at)
            VALUES($1, TRUE, $2, 0, $3)
            ON CONFLICT(license_key)
            DO UPDATE SET active=TRUE, max_devices=$2, expires_at=$3
            RETURNING *
        """, license_key.upper(), int(max_devices), expires_at)

async def login_with_license(telegram_id, license_key):
    await ensure_license_tables()
    key = license_key.upper()
    p = await init_db()
    async with p.acquire() as conn:
        lic = await conn.fetchrow("SELECT * FROM license_keys WHERE license_key=$1", key)
        if not lic:
            return False, "License key not found.", None
        if not lic["active"]:
            return False, "License key is deactivated.", lic
        if lic["expires_at"] <= datetime.now(timezone.utc):
            return False, "License key expired.", lic

        existing = await conn.fetchrow("SELECT * FROM license_sessions WHERE license_key=$1 AND telegram_id=$2", key, int(telegram_id))
        if not existing:
            devices = await conn.fetchval("SELECT COUNT(*) FROM license_sessions WHERE license_key=$1", key)
            if int(devices) >= int(lic["max_devices"]):
                return False, "Device limit reached for this license.", lic
            await conn.execute("""
                INSERT INTO license_sessions(license_key, telegram_id, first_login_at, last_login_at)
                VALUES($1, $2, NOW(), NOW())
            """, key, int(telegram_id))
        else:
            await conn.execute("""
                UPDATE license_sessions SET last_login_at=NOW()
                WHERE license_key=$1 AND telegram_id=$2
            """, key, int(telegram_id))

        used = await conn.fetchval("SELECT COUNT(*) FROM license_sessions WHERE license_key=$1", key)
        await conn.execute("UPDATE license_keys SET used_devices=$2 WHERE license_key=$1", key, int(used))
        lic = await conn.fetchrow("SELECT * FROM license_keys WHERE license_key=$1", key)
        return True, "Login successful.", lic

async def get_license_session(telegram_id):
    await ensure_license_tables()
    p = await init_db()
    async with p.acquire() as conn:
        return await conn.fetchrow("""
            SELECT ls.*, lk.expires_at, lk.active, lk.max_devices, lk.used_devices
            FROM license_sessions ls
            JOIN license_keys lk ON lk.license_key=ls.license_key
            WHERE ls.telegram_id=$1
            ORDER BY ls.last_login_at DESC
            LIMIT 1
        """, int(telegram_id))

async def license_session_active(telegram_id):
    sess = await get_license_session(telegram_id)
    if not sess:
        return False, None
    if not sess["active"] or sess["expires_at"] <= datetime.now(timezone.utc):
        await license_logout(telegram_id)
        return False, None
    return True, sess

async def license_logout(telegram_id):
    await ensure_license_tables()
    p = await init_db()
    async with p.acquire() as conn:
        old = await conn.fetchrow("SELECT license_key FROM license_sessions WHERE telegram_id=$1", int(telegram_id))
        await conn.execute("DELETE FROM license_sessions WHERE telegram_id=$1", int(telegram_id))
        if old:
            used = await conn.fetchval("SELECT COUNT(*) FROM license_sessions WHERE license_key=$1", old["license_key"])
            await conn.execute("UPDATE license_keys SET used_devices=$2 WHERE license_key=$1", old["license_key"], int(used))

async def list_license_keys(limit=100):
    await ensure_license_tables()
    p = await init_db()
    async with p.acquire() as conn:
        return await conn.fetch("SELECT * FROM license_keys ORDER BY created_at DESC LIMIT $1", int(limit))

async def set_license_active(license_key, active=True):
    await ensure_license_tables()
    p = await init_db()
    async with p.acquire() as conn:
        return await conn.fetchrow("UPDATE license_keys SET active=$2 WHERE license_key=$1 RETURNING *", license_key.upper(), bool(active))

async def delete_license_key(license_key):
    await ensure_license_tables()
    p = await init_db()
    async with p.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM license_keys WHERE license_key=$1", license_key.upper())
        await conn.execute("DELETE FROM license_keys WHERE license_key=$1", license_key.upper())
        return row


# ================= ACCURACY RATE SETTINGS =================

async def ensure_bot_settings():
    global bot_settings_ready
    if bot_settings_ready:
        return
    p = await init_db()
    async with p.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS bot_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        INSERT INTO bot_settings(key, value)
        VALUES('accuracy_mode', 'auto')
        ON CONFLICT(key) DO NOTHING;
        """)
    bot_settings_ready = True

async def set_accuracy_mode(value):
    await ensure_bot_settings()
    p = await init_db()
    async with p.acquire() as conn:
        await conn.execute("""
            INSERT INTO bot_settings(key, value)
            VALUES('accuracy_mode', $1)
            ON CONFLICT(key) DO UPDATE SET value=$1
        """, value)

async def get_accuracy_mode():
    await ensure_bot_settings()
    p = await init_db()
    async with p.acquire() as conn:
        val = await conn.fetchval("SELECT value FROM bot_settings WHERE key='accuracy_mode'")
    return val or "auto"


# ================= LICENSE SESSION SIGNAL FLOW UPDATE OVERRIDE V54 =================

async def ensure_signal_session_columns():
    global signal_session_columns_ready
    if signal_session_columns_ready:
        return
    await ensure_license_tables()
    p = await init_db()
    async with p.acquire() as conn:
        await conn.execute("""
        ALTER TABLE license_sessions ADD COLUMN IF NOT EXISTS platform TEXT;
        ALTER TABLE license_sessions ADD COLUMN IF NOT EXISTS market_type TEXT;
        ALTER TABLE license_sessions ADD COLUMN IF NOT EXISTS asset TEXT;
        ALTER TABLE license_sessions ADD COLUMN IF NOT EXISTS timeframe TEXT;
        ALTER TABLE license_sessions ADD COLUMN IF NOT EXISTS utc_time TEXT;
        """)
    signal_session_columns_ready = True

async def update_session(telegram_id, **kwargs):
    await ensure_signal_session_columns()
    p = await init_db()
    async with p.acquire() as conn:
        sess = await conn.fetchrow("""
            SELECT id FROM license_sessions
            WHERE telegram_id=$1
            ORDER BY last_login_at DESC
            LIMIT 1
        """, int(telegram_id))
        if not sess:
            return None

        sets = []
        vals = []
        idx = 1

        for col in ["platform", "market_type", "asset", "timeframe", "utc_time"]:
            if kwargs.get(f"clear_{col}") is True:
                sets.append(f"{col}=NULL")
            elif col in kwargs and kwargs[col] is not None:
                sets.append(f"{col}=${idx}")
                vals.append(kwargs[col])
                idx += 1

        if not sets:
            return await conn.fetchrow("SELECT * FROM license_sessions WHERE id=$1", sess["id"])

        vals.append(sess["id"])
        query = f"UPDATE license_sessions SET {', '.join(sets)}, last_login_at=NOW() WHERE id=${idx} RETURNING *"
        return await conn.fetchrow(query, *vals)
