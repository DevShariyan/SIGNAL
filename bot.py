
import os
import re
import random
import string
from html import escape
from datetime import datetime
from dotenv import load_dotenv
from telegram import (
    Bot,
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    InputFile,
)
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from database import (
    init_db, create_user, get_user, user_is_active, list_users, set_ban,
    login_session, logout_session, session_active, update_session,
    add_signal, get_history, create_license_key, login_with_license, license_session_active, license_logout, list_license_keys, set_license_active, delete_license_key, set_accuracy_mode, get_accuracy_mode, add_dynamic_platform, add_dynamic_market, add_dynamic_asset, add_dynamic_timeframe, add_dynamic_utc, get_dynamic_platforms, get_dynamic_markets, get_dynamic_assets, get_dynamic_timeframes, get_dynamic_utc
)
from market_data import get_market_candles
from indicators import analyze_signal

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def clear_old_webhook():
    try:
        bot = Bot(BOT_TOKEN)
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

ACCURACY_RANGE = None


DEFAULT_PLATFORMS = [
    "Quotex", "Pocket Option", "Binomo", "IQ Option", "Olymp Trade",
    "ExpertOption", "Exnova", "Deriv", "Stockity", "Bullex"
]

PLATFORM_CONFIG = {
    "Quotex": {
        "markets": {
            "🔥 OTC Market": ["🔥 USD/INR OTC", "💵 USD/BDT OTC", "🇧🇷 USD/BRL OTC", "💶 EUR/USD OTC", "💷 GBP/USD OTC", "💴 USD/JPY OTC"],
            "💱 Forex Market": ["💶 EUR/USD", "💷 GBP/USD", "💴 USD/JPY", "🇨🇦 USD/CAD", "🇦🇺 AUD/USD"],
            "🪙 Crypto Market": ["🟡 BTC/USD", "🔷 ETH/USD", "🟢 SOL/USD", "⚡ XRP/USD"]
        },
        "timeframes": ["5s", "10s", "15s", "30s", "M1", "M2", "M3", "M5", "M10", "M15", "M30", "H1", "H4", "⏱ Custom Timeframe"],
        "utc": ["UTC-12", "UTC-11", "UTC-10", "UTC-9", "UTC-8", "UTC-7", "UTC-6", "UTC-5", "UTC-4", "UTC-3", "UTC-2", "UTC-1", "UTC+0", "UTC+1", "UTC+2", "UTC+3", "UTC+4", "UTC+5", "UTC+6", "UTC+7", "UTC+8", "UTC+9", "UTC+10", "UTC+11", "UTC+12", "UTC+13", "UTC+14"]
    },
    "Binomo": {
        "markets": {
            "🔥 OTC Market": ["💶 EUR/USD OTC", "💷 GBP/USD OTC", "💴 USD/JPY OTC", "🇧🇷 USD/BRL OTC", "💵 USD/BDT OTC"],
            "💱 Forex Market": ["💶 EUR/USD", "💷 GBP/USD", "🇨🇦 USD/CAD", "🇳🇿 NZD/USD"],
            "🥇 Commodities": ["🥇 GOLD/USD", "🥈 SILVER/USD", "🛢️ OIL/USD"]
        },
        "timeframes": ["5s", "10s", "15s", "30s", "M1", "M2", "M3", "M5", "M10", "M15", "M30", "H1", "H4", "⏱ Custom Timeframe"],
        "utc": ["UTC-12", "UTC-11", "UTC-10", "UTC-9", "UTC-8", "UTC-7", "UTC-6", "UTC-5", "UTC-4", "UTC-3", "UTC-2", "UTC-1", "UTC+0", "UTC+1", "UTC+2", "UTC+3", "UTC+4", "UTC+5", "UTC+6", "UTC+7", "UTC+8", "UTC+9", "UTC+10", "UTC+11", "UTC+12", "UTC+13", "UTC+14"]
    },
    "Pocket Option": {
        "markets": {
            "🪙 Crypto Market": ["🟡 BTC/USD", "🔷 ETH/USD", "🟣 BNB/USD", "🟢 SOL/USD", "🐶 DOGE/USD"],
            "💱 Forex Market": ["💶 EUR/USD", "💷 GBP/USD", "💴 USD/JPY", "🇦🇺 AUD/USD"],
            "🔥 OTC Market": ["🔥 USD/INR OTC", "💶 EUR/USD OTC", "💷 GBP/USD OTC", "💴 USD/JPY OTC"]
        },
        "timeframes": ["5s", "10s", "15s", "30s", "M1", "M2", "M3", "M5", "M10", "M15", "M30", "H1", "H4", "⏱ Custom Timeframe"],
        "utc": ["UTC-12", "UTC-11", "UTC-10", "UTC-9", "UTC-8", "UTC-7", "UTC-6", "UTC-5", "UTC-4", "UTC-3", "UTC-2", "UTC-1", "UTC+0", "UTC+1", "UTC+2", "UTC+3", "UTC+4", "UTC+5", "UTC+6", "UTC+7", "UTC+8", "UTC+9", "UTC+10", "UTC+11", "UTC+12", "UTC+13", "UTC+14"]
    },
    "Olymp Trade": {
        "markets": {
            "💱 Forex Market": ["💶 EUR/USD", "💷 GBP/USD", "💴 USD/JPY", "🇨🇦 USD/CAD"],
            "🥇 Commodities": ["🥇 GOLD/USD", "🥈 SILVER/USD", "🛢️ OIL/USD"],
            "🪙 Crypto Market": ["🟡 BTC/USD", "🔷 ETH/USD", "⚡ XRP/USD"]
        },
        "timeframes": ["5s", "10s", "15s", "30s", "M1", "M2", "M3", "M5", "M10", "M15", "M30", "H1", "H4", "⏱ Custom Timeframe"],
        "utc": ["UTC-12", "UTC-11", "UTC-10", "UTC-9", "UTC-8", "UTC-7", "UTC-6", "UTC-5", "UTC-4", "UTC-3", "UTC-2", "UTC-1", "UTC+0", "UTC+1", "UTC+2", "UTC+3", "UTC+4", "UTC+5", "UTC+6", "UTC+7", "UTC+8", "UTC+9", "UTC+10", "UTC+11", "UTC+12", "UTC+13", "UTC+14"]
    },
    "ExpertOption": {
        "markets": {
            "🔥 OTC Market": ["💶 EUR/USD OTC", "💷 GBP/USD OTC", "💴 USD/JPY OTC"],
            "🪙 Crypto Market": ["🟡 BTC/USD", "🔷 ETH/USD", "🟢 SOL/USD"],
            "💱 Forex Market": ["💶 EUR/USD", "💷 GBP/USD", "🇦🇺 AUD/USD"]
        },
        "timeframes": ["5s", "10s", "15s", "30s", "M1", "M2", "M3", "M5", "M10", "M15", "M30", "H1", "H4", "⏱ Custom Timeframe"],
        "utc": ["UTC-12", "UTC-11", "UTC-10", "UTC-9", "UTC-8", "UTC-7", "UTC-6", "UTC-5", "UTC-4", "UTC-3", "UTC-2", "UTC-1", "UTC+0", "UTC+1", "UTC+2", "UTC+3", "UTC+4", "UTC+5", "UTC+6", "UTC+7", "UTC+8", "UTC+9", "UTC+10", "UTC+11", "UTC+12", "UTC+13", "UTC+14"]
    }
}

# Admin editable in-memory additions. Default flow never depends on this.
CUSTOM_PLATFORMS = []

def clean_license_key(text):
    return re.sub(r"[^A-Za-z0-9]", "", text.upper())

def make_license_key(prefix="", suffix="", length=16):
    prefix = clean_license_key(prefix)[:5]
    suffix = clean_license_key(suffix)[:5]
    chars = string.ascii_uppercase + string.digits
    middle = "".join(random.choice(chars) for _ in range(max(0, length - len(prefix) - len(suffix))))
    return (prefix + middle + suffix)[:length]

def license_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ Auto Generate License", callback_data="admin_auto_license")],
        [InlineKeyboardButton("🔢 Bulk Generate Keys", callback_data="admin_bulk_license")],
        [InlineKeyboardButton("✍️ Custom License", callback_data="admin_custom_license")],
        [InlineKeyboardButton("📋 License List", callback_data="admin_license_list")],
        [InlineKeyboardButton("🚫 Deactivate Key", callback_data="admin_deactivate_key")],
        [InlineKeyboardButton("✅ Activate Key", callback_data="admin_activate_key")],
        [InlineKeyboardButton("🗑 Delete Key", callback_data="admin_delete_key")],
        [InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="admin_home")]
    ])

def bulk_license_count_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("10 Keys", callback_data="admin_bulk_count:10"),
            InlineKeyboardButton("15 Keys", callback_data="admin_bulk_count:15"),
            InlineKeyboardButton("20 Keys", callback_data="admin_bulk_count:20"),
        ],
        [InlineKeyboardButton("⬅️ Back", callback_data="admin_license_panel")]
    ])

def is_admin(uid: int) -> bool:
    return uid == ADMIN_ID

async def safe_edit(q, text, reply_markup=None, parse_mode=None):
    try:
        return await q.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            return None
        raise

def clean_label(value: str) -> str:
    return re.sub(r"^[^\w$€£¥🇦-🇿]+", "", value).strip()

def accuracy_mode_text():
    global ACCURACY_RANGE
    if ACCURACY_RANGE:
        return f"{ACCURACY_RANGE[0]}% - {ACCURACY_RANGE[1]}%"
    return "AUTO / DEFAULT"

def get_platforms():
    platforms = DEFAULT_PLATFORMS + [p for p in CUSTOM_PLATFORMS if p not in DEFAULT_PLATFORMS]
    return platforms

def get_platform_config(platform: str):
    if platform in PLATFORM_CONFIG:
        return PLATFORM_CONFIG[platform]
    return {
        "markets": {
            "🪙 Crypto Market": ["🟡 BTC/USD", "🔷 ETH/USD", "🟢 SOL/USD"],
            "💱 Forex Market": ["💶 EUR/USD", "💷 GBP/USD", "💴 USD/JPY"],
            "🔥 OTC Market": ["💶 EUR/USD OTC", "💷 GBP/USD OTC", "💴 USD/JPY OTC"]
        },
        "timeframes": ["5s", "10s", "15s", "30s", "M1", "M2", "M3", "M5", "M10", "M15", "M30", "H1", "H4", "⏱ Custom Timeframe"],
        "utc": ["UTC-12", "UTC-11", "UTC-10", "UTC-9", "UTC-8", "UTC-7", "UTC-6", "UTC-5", "UTC-4", "UTC-3", "UTC-2", "UTC-1", "UTC+0", "UTC+1", "UTC+2", "UTC+3", "UTC+4", "UTC+5", "UTC+6", "UTC+7", "UTC+8", "UTC+9", "UTC+10", "UTC+11", "UTC+12", "UTC+13", "UTC+14"]
    }

async def load_platforms():
    platforms = get_platforms()
    try:
        dyn = await get_dynamic_platforms()
        for p in dyn:
            if p not in platforms:
                platforms.append(p)
    except Exception:
        pass
    return platforms

async def load_markets(platform):
    cfg = get_platform_config(platform)
    markets = list(cfg["markets"].keys())
    try:
        dyn = await get_dynamic_markets(platform)
        for m in dyn:
            if m not in markets:
                markets.append(m)
    except Exception:
        pass
    return markets

async def load_assets(platform, market):
    cfg = get_platform_config(platform)
    assets = cfg["markets"].get(market, [])
    try:
        dyn = await get_dynamic_assets(platform, market)
        for a in dyn:
            if a not in assets:
                assets.append(a)
    except Exception:
        pass
    if not assets:
        assets = ["🟡 BTC/USD", "🔷 ETH/USD", "💶 EUR/USD", "💷 GBP/USD"]
    return assets

async def load_timeframes(platform):
    cfg = get_platform_config(platform)
    items = list(cfg["timeframes"])
    try:
        dyn = await get_dynamic_timeframes(platform)
        for t in dyn:
            if t not in items:
                items.append(t)
    except Exception:
        pass
    return items

async def load_utc(platform):
    cfg = get_platform_config(platform)
    items = list(cfg["utc"])
    try:
        dyn = await get_dynamic_utc(platform)
        for u in dyn:
            if u not in items:
                items.append(u)
    except Exception:
        pass
    return items

def user_bottom_keyboard():
    return ReplyKeyboardMarkup(
        [["📊 Get Signal"], ["🕘 History", "📤 Export History"], ["ℹ️ Info Bot"], ["🚪 Logout"]],
        resize_keyboard=True
    )

def guest_bottom_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🔐 Login")],
            [KeyboardButton("ℹ️ Info Bot")],
        ],
        resize_keyboard=True
    )

def admin_bottom_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton("👑 Admin Panel")]], resize_keyboard=True)



def profile_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Get Signal", callback_data="menu_signal")],
        [InlineKeyboardButton("🕘 History", callback_data="menu_history"),
         InlineKeyboardButton("📤 Export History", callback_data="menu_export_history")],
        [InlineKeyboardButton("ℹ️ Info Bot", callback_data="menu_info")]
    ])

def main_menu_only():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_home")]
    ])

def result_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔁 Re-signal", callback_data="menu_resignal")],
        [InlineKeyboardButton("🕘 History", callback_data="menu_history"),
         InlineKeyboardButton("📤 Export History", callback_data="menu_export_history")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_home")]
    ])

def user_inline_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Get Signal", callback_data="menu_signal")],
        [InlineKeyboardButton("👤 Profile", callback_data="menu_account"), InlineKeyboardButton("🕘 History", callback_data="menu_history")],
        [InlineKeyboardButton("📤 Export History", callback_data="menu_export_history"), InlineKeyboardButton("ℹ️ Info Bot", callback_data="menu_info")],])

def buttons(items, prefix, cols=1):
    rows, row = [], []
    for item in items:
        row.append(InlineKeyboardButton(item, callback_data=f"{prefix}:{item}"))
        if len(row) >= cols:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)

def buttons_with_back(items, prefix, back_callback, cols=1):
    rows, row = [], []
    for item in items:
        row.append(InlineKeyboardButton(item, callback_data=f"{prefix}:{item}"))
        if len(row) >= cols:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data=back_callback)])
    return InlineKeyboardMarkup(rows)


def admin_market_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Market", callback_data="admin_add_market")],
        [InlineKeyboardButton("➖ Remove Market", callback_data="admin_remove_market")],
        [InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="admin_home")]
    ])

def admin_asset_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Asset", callback_data="admin_add_asset")],
        [InlineKeyboardButton("➖ Remove Asset", callback_data="admin_remove_asset")],
        [InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="admin_home")]
    ])

def admin_timeframe_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Timeframe", callback_data="admin_add_timeframe")],
        [InlineKeyboardButton("➖ Remove Timeframe", callback_data="admin_remove_timeframe")],
        [InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="admin_home")]
    ])

def admin_utc_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add UTC", callback_data="admin_add_utc")],
        [InlineKeyboardButton("➖ Remove UTC", callback_data="admin_remove_utc")],
        [InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="admin_home")]
    ])

def user_detail_menu(license_key):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚫 Ban", callback_data=f"ban_key:{license_key}"),
         InlineKeyboardButton("✅ Unban", callback_data=f"unban_key:{license_key}")],
        [InlineKeyboardButton("🗑 Delete", callback_data=f"delete_key:{license_key}")],
        [InlineKeyboardButton("⬅️ Back to Users", callback_data="admin_users")]
    ])

def users_list_menu(keys):
    rows = []
    for i, k in enumerate(keys[:50], 1):
        rows.append([InlineKeyboardButton(f"{i}. {k['license_key']} ({'Active' if k['active'] else 'Disabled'})", callback_data=f"user_detail:{k['license_key']}")])
    rows.append([InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="admin_home")])
    return InlineKeyboardMarkup(rows)

def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 License Keys", callback_data="admin_license_panel")],
        [InlineKeyboardButton("👥 Users", callback_data="admin_users")],
        [InlineKeyboardButton("🚫 Ban User", callback_data="admin_ban"),
         InlineKeyboardButton("✅ Unban User", callback_data="admin_unban")],
        [InlineKeyboardButton("🏷 Platforms", callback_data="admin_platforms"),
         InlineKeyboardButton("➕ Add Platform", callback_data="admin_add_platform")],
        [InlineKeyboardButton("➖ Remove Platform", callback_data="admin_remove_platform")],
        [InlineKeyboardButton("🏷 Market", callback_data="admin_market_menu"),
         InlineKeyboardButton("💱 Asset", callback_data="admin_asset_menu")],
        [InlineKeyboardButton("⏱ Timeframe", callback_data="admin_timeframe_menu"),
         InlineKeyboardButton("🌐 UTC", callback_data="admin_utc_menu")],
        [InlineKeyboardButton("🎯 Accuracy Settings", callback_data="admin_accuracy")],
        [InlineKeyboardButton("⚙️ Default Flow", callback_data="admin_default_flow"),
         InlineKeyboardButton("ℹ️ Help", callback_data="admin_help")]
    ])


def accuracy_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Auto / Default", callback_data="accuracy_auto")],
        [InlineKeyboardButton("🎯 Custom Accuracy", callback_data="accuracy_custom")],
        [InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="admin_home")]
    ])

def admin_back_menu():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="admin_home")]])

async def post_init(app):
    await init_db()

async def show_admin_panel(target):
    text = (
        "👑 <b>Admin Panel</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "⚙️ Manage users, licenses, platforms, markets and signal settings.\n\n"
        "🔑 <b>License Keys</b> — create/manage licenses\n"
        "👥 <b>Users</b> — view users and details\n"
        "🚫/✅ <b>Ban/Unban</b> — access control\n"
        "🏷 <b>Platforms</b> — add/remove marketplaces\n"
        "🏷 <b>Market</b> — add/remove market category\n"
        "💱 <b>Asset</b> — add/remove trading asset\n"
        "⏱ <b>Timeframe</b> — add/remove timeframe\n"
        "🌐 <b>UTC</b> — add/remove UTC session\n"
        "🎯 <b>Accuracy Settings</b> — signal rate\n"
        "⚙️ <b>Default Flow</b> — view default setup\n\n"
        "🎲 Select a menu below:"
    )

    if hasattr(target, "message") and target.message:
        return await target.message.reply_text(
            text,
            reply_markup=admin_menu(),
            parse_mode="HTML"
        )

    return await safe_edit(
        target,
        text,
        reply_markup=admin_menu(),
        parse_mode="HTML"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_admin(update.effective_user.id):
        await update.message.reply_text("✅ Admin keyboard active.", reply_markup=admin_bottom_keyboard())
        return await show_admin_panel(update)

    ok, sess = await license_session_active(update.effective_user.id)
    if ok:
        await update.message.reply_text(
            "✅ <b>You are logged in</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🔑 <b>License:</b> <code>{sess['license_key']}</code>\n"
            f"📅 <b>Expiry:</b> {sess['expires_at']}",
            reply_markup=user_bottom_keyboard(),
            parse_mode="HTML"
        )
        return await update.message.reply_text(
            "🏠 <b>User Dashboard</b>",
            reply_markup=profile_menu(),
            parse_mode="HTML"
        )

    await update.message.reply_text(
        "🤖 <b>PREMIUM SIGNAL ACCESS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🔐 <b>Secure License Login</b>\n\n"
        "Tap <b>🔐 Login</b> and send your 16-character license key.\n\n"
        "Example: <code>VIPA1B2C3D4E5F6</code>",
        reply_markup=guest_bottom_keyboard(),
        parse_mode="HTML"
    )

async def signal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if is_admin(uid):
        return await show_admin_panel(update)

    ok, sess = await license_session_active(uid)
    if not ok:
        return await update.message.reply_text(
            "❌ Please login first with your license key.",
            reply_markup=guest_bottom_keyboard(),
            parse_mode="HTML"
        )

    await update_session(
        uid,
        platform=None,
        market_type=None,
        asset=None,
        timeframe=None,
        utc_time=None
    )

    return await update.message.reply_text(
        "📊 <b>Select Trading Platform</b>",
        reply_markup=buttons(await load_platforms(), "platform"),
        parse_mode="HTML"
    )


async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_admin(update.effective_user.id):
        return await show_admin_panel(update)

    if context.args:
        return await do_license_login(update, context, "".join(context.args))

    context.user_data["user_flow"] = "license_login"
    await update.message.reply_text(
        "🔐 <b>SECURE LICENSE LOGIN</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Please send your 16-character license key.\n\n"
        "Example: <code>VIPA1B2C3D4E5F6</code>",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML"
    )

async def do_license_login(update: Update, context: ContextTypes.DEFAULT_TYPE, license_key: str):
    key = clean_license_key(license_key)
    if len(key) != 16:
        return await update.message.reply_text(
            "❌ <b>Invalid License Key</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            "License key must be exactly 16 characters.\n\n"
            "Example: <code>VIPA1B2C3D4E5F6</code>",
            reply_markup=guest_bottom_keyboard(),
            parse_mode="HTML"
        )

    ok, msg, lic = await login_with_license(update.effective_user.id, key)
    if not ok:
        return await update.message.reply_text(
            "⛔ <b>LICENSE LOGIN FAILED</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            f"{msg}\n\nPlease check your license key or contact admin.",
            reply_markup=guest_bottom_keyboard(),
            parse_mode="HTML"
        )

    context.user_data.pop("user_flow", None)
    await update.message.reply_text(
        "✅ <b>LICENSE LOGIN SUCCESSFUL</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🔑 <b>License Key:</b> <code>{key}</code>\n"
        f"🕘 <b>Login Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"📅 <b>Expiry Date:</b> {lic['expires_at']}\n\n"
        "🏠 Your dashboard is ready.",
        reply_markup=user_bottom_keyboard(),
        parse_mode="HTML"
    )
    await update.message.reply_text(
        "🏠 <b>USER DASHBOARD</b>",
        reply_markup=profile_menu(),
        parse_mode="HTML"
    )

async def createuser_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("Access denied.")
    if len(context.args) < 3:
        return await update.message.reply_text("Use: /createuser license_key days")
    u = await create_user(context.args[0], context.args[1], context.args[2])
    await update.message.reply_text(f"✅ User created\nUsername: {u['username']}\nExpiry: {u['expires_at']}")

async def build_history_text(uid):
    rows = await get_history(uid, 100)
    rows = [r for r in rows if is_valid_signal_record(r)]
    if not rows:
        return "🕘 <b>Signal History</b>\n━━━━━━━━━━━━━━━━━━━━\nNo valid signal history found."

    lines = ["🕘 <b>Signal History</b>", "━━━━━━━━━━━━━━━━━━━━"]
    for i, r in enumerate(rows[:5], 1):
        direction = r.get("signal") or r.get("direction") or "N/A"
        confidence = r.get("confidence", r.get("accuracy", "N/A"))
        lines.append(
            f"<b>{i}.</b> {r.get('asset', 'N/A')} — <b>{direction}</b>\n"
            f"📊 {r.get('platform', 'N/A')} | {r.get('market_type', 'N/A')}\n"
            f"⏱ {r.get('timeframe', 'N/A')} | 🌐 {r.get('utc_time', 'N/A')}\n"
            f"🎯 Accuracy: {confidence}"
        )
    return "\n\n".join(lines)

async def send_history_export(obj, context, uid):
    rows = await get_history(uid, 100)
    rows = [r for r in rows if is_valid_signal_record(r)]

    if not rows:
        if hasattr(obj, "message") and obj.message:
            return await obj.message.reply_text("🕘 No valid history found.", reply_markup=user_bottom_keyboard())
        return await safe_edit(obj, "🕘 No valid history found.", reply_markup=profile_menu())

    file_path = f"/tmp/signal_history_{uid}.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("SIGNAL HISTORY - LAST 100 VALID SIGNALS\n")
        f.write("=====================================\n\n")
        for i, r in enumerate(rows[:100], 1):
            direction = r.get("signal") or r.get("direction") or "N/A"
            confidence = r.get("confidence", r.get("accuracy", "N/A"))
            f.write(f"{i}. {r.get('asset', 'N/A')} - {direction}\n")
            f.write(f"Platform: {r.get('platform', 'N/A')}\n")
            f.write(f"Market: {r.get('market_type', 'N/A')}\n")
            f.write(f"Timeframe: {r.get('timeframe', 'N/A')}\n")
            f.write(f"UTC: {r.get('utc_time', 'N/A')}\n")
            f.write(f"Accuracy: {confidence}\n")
            f.write("-------------------------------------\n")

    if hasattr(obj, "message") and obj.message:
        return await obj.message.reply_document(document=open(file_path, "rb"), filename="signal_history_last_100.txt")
    return await context.bot.send_document(chat_id=obj.message.chat_id, document=open(file_path, "rb"), filename="signal_history_last_100.txt")

async def apply_accuracy(record):
    mode = "auto"
    try:
        mode = await get_accuracy_mode()
    except Exception:
        mode = "auto"

    if mode and mode != "auto" and "-" in mode:
        try:
            low, high = [int(x) for x in mode.split("-", 1)]
            if low > high:
                low, high = high, low
            low = max(60, low)
            high = min(99, high)
            record["confidence"] = float(random.randint(low, high))
        except Exception:
            pass

    return record

def accuracy_mode_text_sync_placeholder():
    return "AUTO / DEFAULT"


def is_valid_signal_record(record):
    if not record:
        return False
    try:
        return bool(
            record.get("platform") and
            record.get("asset") and
            (record.get("signal") or record.get("direction"))
        )
    except Exception:
        return False

def signal_direction(value):
    signal = str(value or "").upper()
    if signal == "BUY":
        return "BUY"
    if signal == "SELL":
        return "SELL"
    if signal == "WAIT":
        return "WAIT"
    return signal or "WAIT"

def signal_icon(value):
    signal = str(value or "").upper()
    if signal == "BUY":
        return "🟢"
    if signal == "SELL":
        return "🔴"
    return "🟡"

def build_signal_message(record):
    if not is_valid_signal_record(record):
        return None

    created = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
    asset = escape(clean_label(str(record["asset"])))
    platform = escape(str(record.get("platform", "N/A")))
    market_type = escape(str(record.get("market_type", "N/A")))
    utc_time = escape(str(record.get("utc_time", "N/A")))
    timeframe = escape(str(record.get("timeframe", "N/A")))
    trend_strength = escape(str(record.get("trend_strength", "N/A")))
    pattern = escape(str(record.get("pattern", "N/A")))
    direction = signal_direction(record["signal"])
    icon = signal_icon(record["signal"])
    confidence = f"{float(record['confidence']):.8f}"
    reasons = record.get("reasons") or []
    if isinstance(reasons, str):
        reasons = [reasons]

    reason_lines = "\n".join([f"• {escape(str(r))}" for r in reasons[:6]]) or "• Market structure and indicators aligned"

    return (
        "<pre>"
        "╔═════════ SIGNAL ═════════╗\n\n"
        f"🔥 {asset}\n"
        f"🕐 {utc_time}\n"
        f"⏳ {timeframe}\n"
        f"{icon} {direction}\n"
        f"🎯 {confidence}\n\n"
        f"🔁 SIGNAL: {created}\n"
        "╚═════════ ***** ═════════╝"
        "</pre>\n"
        "<pre>"
        "╔══════ ANALYSIS INFO ═════╗\n\n"
        f"📌 Platform : {platform}\n"
        f"🏷 Market   : {market_type}\n"
        f"📈 Trend    : {trend_strength}\n"
        f"📊 EMA      : {record['ema9']} / {record['ema21']}\n"
        f"〽️ MACD     : {record['macd_hist']}\n"
        f"⚡ RSI Zone : {record['rsi']}\n"
        f"🕯 Candle   : {pattern}\n\n"
        "╚══════════════════════════╝"
        "</pre>\n"
        "<pre>"
        "╔══ MARKET-BASED REASONS ══╗\n\n"
        f"{reason_lines}\n\n"
        "╚══════════════════════════╝"
        "</pre>"
    )

async def users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("Access denied.")
    rows = await list_users()
    if not rows:
        return await update.message.reply_text("No users.")
    lines = ["👥 License List:"]
    for u in rows:
        lines.append(f"{u['username']} | banned={u['banned']} | exp={u['expires_at']}")
    await update.message.reply_text("\n".join(lines))

async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("Access denied.")
    if not context.args:
        return await update.message.reply_text("Use: /ban username")
    await set_ban(context.args[0], True)
    await update.message.reply_text("🚫 User banned.")

async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("Access denied.")
    if not context.args:
        return await update.message.reply_text("Use: /unban username")
    await set_ban(context.args[0], False)
    await update.message.reply_text("✅ User unbanned.")

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data

    if is_admin(uid) and (data.startswith("admin_") or data.startswith("accuracy_")):
        if data == "admin_home":
            return await show_admin_panel(q)

        if data == "admin_create_user":
            context.user_data["admin_flow"] = "create_username"
            context.user_data["new_user"] = {}
            return await safe_edit(q, "➕ <b>License Keys</b>\n\n<b>Step 1/3</b>\nSend username.\n\nExample: <code>rahim01</code>", reply_markup=admin_back_menu(), parse_mode="HTML")

        if data == "admin_ban_user":
            context.user_data["admin_flow"] = "ban_username"
            return await safe_edit(q, "🚫 <b>Ban User</b>\n\nSend username to ban.\n\nExample: <code>rahim01</code>", reply_markup=admin_back_menu(), parse_mode="HTML")

        if data == "admin_unban_user":
            context.user_data["admin_flow"] = "unban_username"
            return await safe_edit(q, "✅ <b>Unban User</b>\n\nSend username to unban.\n\nExample: <code>rahim01</code>", reply_markup=admin_back_menu(), parse_mode="HTML")

        if data == "admin_accuracy":
            return await safe_edit(
                q,
                "🎯 <b>Accuracy Settings</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"Current Mode: <b>{accuracy_mode_text()}</b>\n\n"
                "Choose an option below:",
                reply_markup=accuracy_menu(),
                parse_mode="HTML"
            )

        if data == "accuracy_auto":
            global ACCURACY_RANGE
            ACCURACY_RANGE = None
            return await safe_edit(
                q,
                "✅ <b>Accuracy Mode Updated</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "Current Mode: <b>AUTO / DEFAULT</b>",
                reply_markup=accuracy_menu(),
                parse_mode="HTML"
            )

        if data == "accuracy_custom":
            context.user_data["admin_flow"] = "set_accuracy"
            return await safe_edit(
                q,
                "🎯 <b>Custom Accuracy</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "Send range between 60 and 99.\n\n"
                "Examples:\n"
                "<code>80-90</code>\n"
                "<code>75-93</code>\n"
                "<code>90-93</code>",
                reply_markup=admin_back_menu(),
                parse_mode="HTML"
            )

        if data == "admin_users":
            keys = await list_license_keys(100)
            if not keys:
                return await safe_edit(q, "👥 <b>Users</b>\n━━━━━━━━━━━━━━━━━━━━\nNo users found yet.", reply_markup=admin_menu(), parse_mode="HTML")
            lines = ["👥 <b>Users</b>", "━━━━━━━━━━━━━━━━━━━━", "Tap a user below to view full details."]
            return await safe_edit(q, "\n".join(lines), reply_markup=users_list_menu(keys), parse_mode="HTML")

        if data.startswith("user_detail:"):
            key = data.split(":", 1)[1]
            all_keys = await list_license_keys(200)
            row = next((x for x in all_keys if x["license_key"] == key), None)
            if not row:
                return await safe_edit(q, "❌ User/license not found.", reply_markup=admin_menu())
            status = "✅ Active" if row["active"] else "🚫 Disabled"
            text = (
                "👤 <b>User Details</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"🔑 <b>License:</b> <code>{row['license_key']}</code>\n"
                f"📌 <b>Status:</b> {status}\n"
                f"📱 <b>Devices:</b> {row['used_devices']}/{row['max_devices']}\n"
                f"📅 <b>Expiry:</b> {row['expires_at']}\n"
                f"🕘 <b>Created:</b> {row['created_at']}"
            )
            return await safe_edit(q, text, reply_markup=user_detail_menu(key), parse_mode="HTML")

        if data.startswith("ban_key:"):
            key = data.split(":", 1)[1]
            await set_license_active(key, False)
            return await safe_edit(q, "🚫 User/license banned.", reply_markup=admin_menu())

        if data.startswith("unban_key:"):
            key = data.split(":", 1)[1]
            await set_license_active(key, True)
            return await safe_edit(q, "✅ User/license unbanned.", reply_markup=admin_menu())

        if data.startswith("delete_key:"):
            key = data.split(":", 1)[1]
            await delete_license_key(key)
            return await safe_edit(q, "🗑 User/license deleted.", reply_markup=admin_menu())

        if data == "admin_ban":
            context.user_data["admin_flow"] = "deactivate_license"
            return await safe_edit(q, "🚫 <b>Ban User</b>\n━━━━━━━━━━━━━━━━━━━━\nSend license key to ban.", reply_markup=admin_back_menu(), parse_mode="HTML")

        if data == "admin_unban":
            context.user_data["admin_flow"] = "activate_license"
            return await safe_edit(q, "✅ <b>Unban User</b>\n━━━━━━━━━━━━━━━━━━━━\nSend license key to unban.", reply_markup=admin_back_menu(), parse_mode="HTML")

        if data == "admin_platforms":
            plats = await load_platforms()
            return await safe_edit(q, "🏷 <b>Platforms</b>\n━━━━━━━━━━━━━━━━━━━━\n" + "\n".join([f"• {p}" for p in plats]), reply_markup=admin_menu(), parse_mode="HTML")

        if data == "admin_add_platform":
            context.user_data["admin_flow"] = "add_platform"
            return await safe_edit(q, "➕ <b>Add Platform</b>\n━━━━━━━━━━━━━━━━━━━━\nSend platform name.", reply_markup=admin_back_menu(), parse_mode="HTML")

        if data == "admin_remove_platform":
            context.user_data["admin_flow"] = "remove_platform"
            return await safe_edit(q, "➖ <b>Remove Platform</b>\n━━━━━━━━━━━━━━━━━━━━\nSend platform name.", reply_markup=admin_back_menu(), parse_mode="HTML")

        if data == "admin_market_menu":
            return await safe_edit(q, "🏷 <b>Market Manager</b>\n━━━━━━━━━━━━━━━━━━━━\nChoose add or remove market.", reply_markup=admin_market_menu(), parse_mode="HTML")

        if data == "admin_asset_menu":
            return await safe_edit(q, "💱 <b>Asset Manager</b>\n━━━━━━━━━━━━━━━━━━━━\nChoose add or remove asset.", reply_markup=admin_asset_menu(), parse_mode="HTML")

        if data == "admin_timeframe_menu":
            return await safe_edit(q, "⏱ <b>Timeframe Manager</b>\n━━━━━━━━━━━━━━━━━━━━\nChoose add or remove timeframe.", reply_markup=admin_timeframe_menu(), parse_mode="HTML")

        if data == "admin_utc_menu":
            return await safe_edit(q, "🌐 <b>UTC Manager</b>\n━━━━━━━━━━━━━━━━━━━━\nChoose add or remove UTC.", reply_markup=admin_utc_menu(), parse_mode="HTML")

        if data == "admin_add_market":
            context.user_data["admin_flow"] = "add_market_platform"
            return await safe_edit(q, "🏷 <b>Add Market</b>\nStep 1: Send platform name.", reply_markup=admin_back_menu(), parse_mode="HTML")

        if data == "admin_remove_market":
            context.user_data["admin_flow"] = "remove_market"
            return await safe_edit(q, "➖ <b>Remove Market</b>\nSend market name. Static defaults remain in code.", reply_markup=admin_back_menu(), parse_mode="HTML")

        if data == "admin_add_asset":
            context.user_data["admin_flow"] = "add_asset_platform"
            return await safe_edit(q, "💱 <b>Add Asset</b>\nStep 1: Send platform name.", reply_markup=admin_back_menu(), parse_mode="HTML")

        if data == "admin_remove_asset":
            context.user_data["admin_flow"] = "remove_asset"
            return await safe_edit(q, "➖ <b>Remove Asset</b>\nSend asset name. Static defaults remain in code.", reply_markup=admin_back_menu(), parse_mode="HTML")

        if data == "admin_add_timeframe":
            context.user_data["admin_flow"] = "add_timeframe_platform"
            return await safe_edit(q, "⏱ <b>Add Timeframe</b>\nStep 1: Send platform name.", reply_markup=admin_back_menu(), parse_mode="HTML")

        if data == "admin_remove_timeframe":
            context.user_data["admin_flow"] = "remove_timeframe"
            return await safe_edit(q, "➖ <b>Remove Timeframe</b>\nSend timeframe. Static defaults remain in code.", reply_markup=admin_back_menu(), parse_mode="HTML")

        if data == "admin_add_utc":
            context.user_data["admin_flow"] = "add_utc_platform"
            return await safe_edit(q, "🌐 <b>Add UTC</b>\nStep 1: Send platform name.", reply_markup=admin_back_menu(), parse_mode="HTML")

        if data == "admin_remove_utc":
            context.user_data["admin_flow"] = "remove_utc"
            return await safe_edit(q, "➖ <b>Remove UTC</b>\nSend UTC. Static defaults remain in code.", reply_markup=admin_back_menu(), parse_mode="HTML")

        if data == "admin_default_flow":
            txt = (
                "⚙️ <b>Default Flow</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "Platform → Market → Asset → Timeframe → UTC → Signal\n\n"
                "✅ Many default platforms\n"
                "✅ Many default markets and assets\n"
                "✅ 1s-5s and common timeframes\n"
                "✅ Custom timeframe\n"
                "✅ Full UTC list"
            )
            return await safe_edit(q, txt, reply_markup=admin_menu(), parse_mode="HTML")

        if data == "admin_license_panel":
            return await safe_edit(q, "🔑 <b>License Key Panel</b>", reply_markup=license_menu(), parse_mode="HTML")

        if data == "admin_auto_license":
            context.user_data["admin_flow"] = "auto_license_days"
            context.user_data["license_data"] = {"count": 1}
            return await safe_edit(
                q,
                "⚡ <b>Auto Generate License</b>\n\n"
                "Step 1/4: Send access days.\n"
                "Example: <code>7</code>",
                reply_markup=admin_back_menu(),
                parse_mode="HTML"
            )

        if data == "admin_bulk_license":
            return await safe_edit(
                q,
                "🔢 <b>Bulk Generate License Keys</b>\n\n"
                "Choose how many keys to create at once.",
                reply_markup=bulk_license_count_menu(),
                parse_mode="HTML"
            )

        if data.startswith("admin_bulk_count:"):
            count = int(data.split(":", 1)[1])
            context.user_data["admin_flow"] = "auto_license_days"
            context.user_data["license_data"] = {"count": count}
            return await safe_edit(
                q,
                f"🔢 <b>Bulk Generate {count} Keys</b>\n\n"
                "Step 1/4: Send access days.\n"
                "Example: <code>7</code>",
                reply_markup=admin_back_menu(),
                parse_mode="HTML"
            )

        if data == "admin_custom_license":
            context.user_data["admin_flow"] = "custom_license_key"
            context.user_data["license_data"] = {}
            return await safe_edit(
                q,
                "✍️ <b>Custom License</b>\n\n"
                "Send exact 16-character license key.\n"
                "Example: <code>VIPA1B2C3D4E5F6</code>",
                reply_markup=admin_back_menu(),
                parse_mode="HTML"
            )

        if data == "admin_license_list":
            keys = await list_license_keys(100)
            if not keys:
                return await safe_edit(q, "📋 No license keys found.", reply_markup=license_menu())
            lines = ["<b>📋 License Keys</b>", "━━━━━━━━━━━━━━━━━━━━"]
            for k in keys[:60]:
                status = "✅ Active" if k["active"] else "🚫 Disabled"
                lines.append(
                    f"<code>{k['license_key']}</code>\n"
                    f"{status} | Devices {k['used_devices']}/{k['max_devices']} | Exp {str(k['expires_at'])[:16]}"
                )
            return await safe_edit(q, "\n\n".join(lines), reply_markup=license_menu(), parse_mode="HTML")

        if data == "admin_deactivate_key":
            context.user_data["admin_flow"] = "deactivate_license"
            return await safe_edit(q, "🚫 Send license key to deactivate.", reply_markup=admin_back_menu())

        if data == "admin_activate_key":
            context.user_data["admin_flow"] = "activate_license"
            return await safe_edit(q, "✅ Send license key to activate.", reply_markup=admin_back_menu())

        if data == "admin_delete_key":
            context.user_data["admin_flow"] = "delete_license"
            return await safe_edit(q, "🗑 Send license key to delete.", reply_markup=admin_back_menu())

        if data == "admin_stats":
            keys = await list_license_keys(100)
            active = sum(1 for k in keys if k["active"])
            disabled = len(keys) - active
            return await safe_edit(
                q,
                f"📊 <b>License Stats</b>\n\nTotal Keys: {len(keys)}\nActive: {active}\nDisabled: {disabled}",
                reply_markup=admin_menu(),
                parse_mode="HTML"
            )


        if data == "admin_help":
            return await safe_edit(
                q,
                "ℹ️ <b>Admin Help</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "🔑 License Keys: generate/list/delete licenses\n"
                "👥 Users: show users, tap user for details\n"
                "🚫 Ban / ✅ Unban: license access control\n"
                "🏷 Platforms: view/add/remove platforms\n"
                "🏷 Market: add/remove market category\n"
                "💱 Asset: add/remove trading asset\n"
                "⏱ Timeframe: add/remove timeframe\n"
                "🌐 UTC: add/remove UTC session\n"
                "🎯 Accuracy Settings: set signal rate\n"
                "⚙️ Default Flow: view default setup",
                reply_markup=admin_menu(),
                parse_mode="HTML"
            )


    ok, sess = await license_session_active(uid)
    if not ok and not is_admin(uid):
        return await safe_edit(q, "❌ Session expired or login required.\nTap 🔐 Login or use /login license_key")

    if data == "menu_home":
        return await safe_edit(
            q,
            "🏠 <b>User Main Menu</b>",
            reply_markup=profile_menu(),
            parse_mode="HTML"
        )

    if data == "menu_signal":
        await update_session(
            uid,
            clear_platform=True,
            clear_market_type=True,
            clear_asset=True,
            clear_timeframe=True,
            clear_utc_time=True
        )
        return await safe_edit(
            q,
            "📊 <b>Select Trading Platform</b>",
            reply_markup=buttons(await load_platforms(), "platform"),
            parse_mode="HTML"
        )


    if data == "menu_resignal":
        ok2, sess2 = await license_session_active(uid)
        if not ok2 or not sess2:
            return await safe_edit(
                q,
                "⚠️ Session expired. Please login and start again.",
                reply_markup=profile_menu(),
                parse_mode="HTML"
            )

        platform = sess2.get("platform")
        market_type = sess2.get("market_type")
        asset = sess2.get("asset")
        timeframe = sess2.get("timeframe")
        utc_time = sess2.get("utc_time")

        if not all([platform, market_type, asset, timeframe, utc_time]):
            return await safe_edit(
                q,
                "⚠️ Please complete signal setup first.",
                reply_markup=profile_menu(),
                parse_mode="HTML"
            )

        candles = await get_market_candles(platform, market_type, asset, "1m")
        result = analyze_signal(candles)
        record = {
            "platform": platform,
            "market_type": market_type,
            "asset": asset,
            "timeframe": timeframe,
            "utc_time": utc_time,
            **result
        }
        record = await apply_accuracy(record)
        if is_valid_signal_record(record):
            await add_signal(uid, sess2.get("license_key", str(uid)), record)
        message = build_signal_message(record)
        if not message:
            return await safe_edit(
                q,
                "⚠️ Signal could not be generated. Please try again.",
                reply_markup=profile_menu(),
                parse_mode="HTML"
            )
        return await safe_edit(
            q,
            message,
            reply_markup=result_menu(),
            parse_mode="HTML"
        )


    if data == "menu_history":
        text = await build_history_text(uid)
        return await safe_edit(q, text, reply_markup=profile_menu(), parse_mode="HTML")

    if data == "menu_export_history":
        return await send_history_export(q, context, uid)

    if data == "menu_account":
        ok2, sess2 = await license_session_active(uid)
        if not ok2:
            return await safe_edit(q, "❌ Login required. Tap 🔐 Login and send license key.")
        return await safe_edit(
            q,
            "<b>👤 LICENSE PROFILE</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>🔑 License Key:</b> <code>{sess2['license_key']}</code>\n"
            f"<b>🆔 Telegram ID:</b> {uid}\n"
            f"<b>🕘 Login Time:</b> {sess2['first_login_at']}\n"
            f"<b>📅 Expiry Date:</b> {sess2['expires_at']}",
            reply_markup=profile_menu(),
            parse_mode="HTML"
        )


    if data == "menu_info":
        return await safe_edit(
            q,
            "<b>ℹ️ Bot Information</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🤖 This bot provides professional market signal analysis using indicator-based logic.\n\n"
            "📊 <b>How it works</b>\n"
            "Platform → Market → Asset → Timeframe → UTC → Signal Result\n\n"
            "🧠 <b>Analysis includes</b>\n"
            "EMA trend, MACD momentum, RSI zone, candle pattern, trend bias, market-based reasons, and global UTC timezone selection.\n\n"
            "⚠️ Trading involves risk. Use proper risk management.",
            reply_markup=main_menu_only(),
            parse_mode="HTML"
        )


    if data == "menu_logout":
        await license_logout(uid)
        return await safe_edit(q, "🚪 Logged out.\nTap 🔐 Login or use /login license_key")

    if data == "back_platforms":
        await update_session(uid, platform=None, market_type=None, asset=None, timeframe=None, utc_time=None)
        return await safe_edit(
            q,
            "📊 <b>Select Trading Platform</b>",
            reply_markup=buttons(await load_platforms(), "platform"),
            parse_mode="HTML"
        )

    if data == "back_markets":
        ok2, sess2 = await license_session_active(uid)
        if not ok2 or not sess2.get("platform"):
            return await safe_edit(q, "📊 <b>Select Trading Platform</b>", reply_markup=buttons(await load_platforms(), "platform"), parse_mode="HTML")
        await update_session(uid, market_type=None, asset=None, timeframe=None, utc_time=None)
        markets = await load_markets(sess2["platform"])
        return await safe_edit(
            q,
            f"📊 <b>Platform:</b> {sess2['platform']}\n\n🏷 <b>Select Market Category</b>",
            reply_markup=buttons_with_back(markets, "market", "back_platforms"),
            parse_mode="HTML"
        )

    if data == "back_assets":
        ok2, sess2 = await license_session_active(uid)
        if not ok2 or not sess2.get("platform") or not sess2.get("market_type"):
            return await safe_edit(q, "📊 <b>Select Trading Platform</b>", reply_markup=buttons(await load_platforms(), "platform"), parse_mode="HTML")
        await update_session(uid, asset=None, timeframe=None, utc_time=None)
        assets = await load_assets(sess2["platform"], sess2["market_type"])
        return await safe_edit(
            q,
            f"🏷 <b>Market:</b> {sess2['market_type']}\n\n💱 <b>Select Trading Asset</b>",
            reply_markup=buttons_with_back(assets, "asset", "back_markets"),
            parse_mode="HTML"
        )

    if data == "back_timeframes":
        ok2, sess2 = await license_session_active(uid)
        if not ok2 or not sess2.get("asset"):
            return await safe_edit(q, "📊 <b>Select Trading Platform</b>", reply_markup=buttons(await load_platforms(), "platform"), parse_mode="HTML")
        await update_session(uid, timeframe=None, utc_time=None)
        platform = sess2.get("platform") or "Quotex"
        timeframes = await load_timeframes(platform)
        return await safe_edit(
            q,
            f"💱 <b>Asset:</b> {sess2['asset']}\n\n⏱ <b>Select Signal Timeframe</b>",
            reply_markup=buttons_with_back(timeframes, "timeframe", "back_assets", cols=2),
            parse_mode="HTML"
        )

    if data == "back_utc":
        ok2, sess2 = await license_session_active(uid)
        if not ok2 or not sess2.get("timeframe"):
            return await safe_edit(q, "📊 <b>Select Trading Platform</b>", reply_markup=buttons(await load_platforms(), "platform"), parse_mode="HTML")
        await update_session(uid, utc_time=None)
        platform = sess2.get("platform") or "Quotex"
        utc_items = await load_utc(platform)
        return await safe_edit(
            q,
            f"⏱ <b>Timeframe:</b> {sess2['timeframe']}\n\n🌐 <b>Select UTC Session Time</b>",
            reply_markup=buttons_with_back(utc_items, "utc", "back_timeframes", cols=3),
            parse_mode="HTML"
        )

    if data.startswith("platform:"):
        platform = data.split(":", 1)[1]
        await update_session(
            uid,
            platform=platform,
            clear_market_type=True,
            clear_asset=True,
            clear_timeframe=True,
            clear_utc_time=True
        )
        markets = await load_markets(platform)
        return await safe_edit(
            q,
            f"📊 <b>Platform:</b> {platform}\n\n🏷 <b>Select Market Category</b>",
            reply_markup=buttons_with_back(markets, "market", "back_platforms"),
            parse_mode="HTML"
        )

    if data.startswith("market:"):
        market_type = data.split(":", 1)[1]
        ok2, sess2 = await license_session_active(uid)
        platform = (sess2 or {}).get("platform") or "Quotex"
        await update_session(
            uid,
            market_type=market_type,
            clear_asset=True,
            clear_timeframe=True,
            clear_utc_time=True
        )
        assets = await load_assets(platform, market_type)
        return await safe_edit(
            q,
            f"🏷 <b>Market:</b> {market_type}\n\n💱 <b>Select Trading Asset</b>",
            reply_markup=buttons_with_back(assets, "asset", "back_markets"),
            parse_mode="HTML"
        )

    if data.startswith("asset:"):
        asset = data.split(":", 1)[1]
        ok2, sess2 = await license_session_active(uid)
        platform = (sess2 or {}).get("platform") or "Quotex"
        await update_session(
            uid,
            asset=asset,
            clear_timeframe=True,
            clear_utc_time=True
        )
        timeframes = await load_timeframes(platform)
        return await safe_edit(
            q,
            f"💱 <b>Asset:</b> {asset}\n\n⏱ <b>Select Signal Timeframe</b>",
            reply_markup=buttons_with_back(timeframes, "timeframe", "back_assets", cols=2),
            parse_mode="HTML"
        )

    if data == "timeframe:⏱ Custom Timeframe":
        context.user_data["user_flow"] = "custom_timeframe"
        return await safe_edit(
            q,
            "⏱ <b>Custom Timeframe</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Send your custom timeframe.\n\n"
            "Examples: <code>M1</code>, <code>M5</code>, <code>30s</code>, <code>H1</code>",
            reply_markup=profile_menu(),
            parse_mode="HTML"
        )

    if data.startswith("timeframe:"):
        timeframe = data.split(":", 1)[1]
        ok2, sess2 = await license_session_active(uid)
        platform = (sess2 or {}).get("platform") or "Quotex"
        await update_session(uid, timeframe=timeframe, clear_utc_time=True)
        utc_items = await load_utc(platform)
        return await safe_edit(
            q,
            f"⏱ <b>Timeframe:</b> {timeframe}\n\n🌐 <b>Select UTC Session Time</b>",
            reply_markup=buttons_with_back(utc_items, "utc", "back_timeframes", cols=3),
            parse_mode="HTML"
        )

    if data.startswith("utc:"):
        selected_utc = data.split(":", 1)[1]
        await update_session(uid, utc_time=selected_utc)

        ok2, sess2 = await license_session_active(uid)
        if not ok2 or not sess2:
            return await safe_edit(
                q,
                "⚠️ Session expired. Please login and start again.",
                reply_markup=profile_menu(),
                parse_mode="HTML"
            )

        platform = sess2.get("platform")
        market_type = sess2.get("market_type")
        asset = sess2.get("asset")
        timeframe = sess2.get("timeframe")
        utc_time = sess2.get("utc_time")

        if not all([platform, market_type, asset, timeframe, utc_time]):
            missing = []
            if not platform: missing.append("platform")
            if not market_type: missing.append("market")
            if not asset: missing.append("asset")
            if not timeframe: missing.append("timeframe")
            if not utc_time: missing.append("UTC")
            return await safe_edit(
                q,
                "⚠️ Signal setup incomplete. Missing: " + ", ".join(missing) + "\nPlease start again.",
                reply_markup=profile_menu(),
                parse_mode="HTML"
            )

        candles = await get_market_candles(platform, market_type, asset, "1m")
        result = analyze_signal(candles)
        record = {
            "platform": platform,
            "market_type": market_type,
            "asset": asset,
            "timeframe": timeframe,
            "utc_time": utc_time,
            **result
        }
        record = await apply_accuracy(record)
        if is_valid_signal_record(record):
            await add_signal(uid, sess2.get("license_key", str(uid)), record)
        message = build_signal_message(record)
        if not message:
            return await safe_edit(
                q,
                "⚠️ Signal could not be generated. Please try again.",
                reply_markup=profile_menu(),
                parse_mode="HTML"
            )
        return await safe_edit(
            q,
            message,
            reply_markup=result_menu(),
            parse_mode="HTML"
        )


async def admin_text_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return False
    flow = context.user_data.get("admin_flow")
    if not flow:
        return False
    text = (update.message.text or "").strip()

    if flow == "create_username":
        if len(text) < 3:
            await update.message.reply_text("Username must be at least 3 characters.")
            return True
        context.user_data["new_user"] = {"username": text.lower()}
        context.user_data["admin_flow"] = "create_password"
        await update.message.reply_text("➕ License Keys\n\nStep 2/3\nSend password.\n\nExample: pass123")
        return True

    if flow == "create_password":
        if len(text) < 4:
            await update.message.reply_text("Password must be at least 4 characters.")
            return True
        context.user_data["new_user"]["password"] = text
        context.user_data["admin_flow"] = "create_days"
        await update.message.reply_text("➕ License Keys\n\nStep 3/3\nSend access days.\n\nExample: 7")
        return True

    if flow == "create_days":
        if not text.isdigit():
            await update.message.reply_text("Days must be a number. Example: 7")
            return True
        info = context.user_data.get("new_user", {})
        u = await create_user(info["username"], info["password"], int(text))
        context.user_data.pop("admin_flow", None)
        context.user_data.pop("new_user", None)
        await update.message.reply_text(f"✅ User Created\n\nUsername: {u['username']}\nPassword: {info['password']}\nDays: {text}\nExpiry: {u['expires_at']}\n\nLogin:\n/login {u['username']} {info['password']}", reply_markup=admin_bottom_keyboard())
        await show_admin_panel(update)
        return True

    if flow == "ban_username":
        row = await set_ban(text.lower(), True)
        context.user_data.pop("admin_flow", None)
        await update.message.reply_text("🚫 User banned." if row else "❌ Username not found.", reply_markup=admin_bottom_keyboard())
        await show_admin_panel(update)
        return True

    if flow == "unban_username":
        row = await set_ban(text.lower(), False)
        context.user_data.pop("admin_flow", None)
        await update.message.reply_text("✅ User unbanned." if row else "❌ Username not found.", reply_markup=admin_bottom_keyboard())
        await show_admin_panel(update)
        return True

    if flow == "add_platform":
        if text not in CUSTOM_PLATFORMS and text not in DEFAULT_PLATFORMS:
            CUSTOM_PLATFORMS.append(text)
        context.user_data.pop("admin_flow", None)
        await update.message.reply_text(f"✅ Platform added: {text}", reply_markup=admin_bottom_keyboard())
        await show_admin_panel(update)
        return True

    if flow == "remove_platform":
        if text in CUSTOM_PLATFORMS:
            CUSTOM_PLATFORMS.remove(text)
            msg = f"✅ Platform removed: {text}"
        else:
            msg = "ℹ️ Default platforms cannot be removed from the fallback list."
        context.user_data.pop("admin_flow", None)
        await update.message.reply_text(msg, reply_markup=admin_bottom_keyboard())
        await show_admin_panel(update)
        return True


    if flow == "add_market_platform":
        context.user_data["section_platform"] = text
        context.user_data["admin_flow"] = "add_market_name"
        await update.message.reply_text("🏷️ Add Market Category\n\nStep 2/2\nSend market category name.\n\nExample: 🔥 OTC Market")
        return True

    if flow == "add_market_name":
        platform = context.user_data.get("section_platform", "Quotex")
        await add_dynamic_market(platform, text)
        context.user_data.pop("admin_flow", None)
        context.user_data.pop("section_platform", None)
        await update.message.reply_text(f"✅ Market added\nPlatform: {platform}\nMarket: {text}", reply_markup=admin_bottom_keyboard())
        await show_admin_panel(update)
        return True

    if flow == "add_asset_platform":
        context.user_data["section_platform"] = text
        context.user_data["admin_flow"] = "add_asset_market"
        await update.message.reply_text("💱 Add Trading Asset\n\nStep 2/3\nSend market category name.\n\nExample: 🔥 OTC Market")
        return True

    if flow == "add_asset_market":
        context.user_data["section_market"] = text
        context.user_data["admin_flow"] = "add_asset_name"
        await update.message.reply_text("💱 Add Trading Asset\n\nStep 3/3\nSend asset/pair name.\n\nExample: 💶 EUR/USD OTC")
        return True

    if flow == "add_asset_name":
        platform = context.user_data.get("section_platform", "Quotex")
        market = context.user_data.get("section_market", "🔥 OTC Market")
        await add_dynamic_asset(platform, market, text)
        context.user_data.pop("admin_flow", None)
        context.user_data.pop("section_platform", None)
        context.user_data.pop("section_market", None)
        await update.message.reply_text(f"✅ Asset added\nPlatform: {platform}\nMarket: {market}\nAsset: {text}", reply_markup=admin_bottom_keyboard())
        await show_admin_panel(update)
        return True

    if flow == "add_timeframe_platform":
        context.user_data["section_platform"] = text
        context.user_data["admin_flow"] = "add_timeframe_name"
        await update.message.reply_text("⏱ Add Signal Timeframe\n\nStep 2/2\nSend timeframe.\n\nExample: M5")
        return True

    if flow == "add_timeframe_name":
        platform = context.user_data.get("section_platform", "Quotex")
        await add_dynamic_timeframe(platform, text)
        context.user_data.pop("admin_flow", None)
        context.user_data.pop("section_platform", None)
        await update.message.reply_text(f"✅ Timeframe added\nPlatform: {platform}\nTimeframe: {text}", reply_markup=admin_bottom_keyboard())
        await show_admin_panel(update)
        return True

    if flow == "add_utc_platform":
        context.user_data["section_platform"] = text
        context.user_data["admin_flow"] = "add_utc_name"
        await update.message.reply_text("🌐 Add UTC Session\n\nStep 2/2\nSend UTC time.\n\nExample: UTC+6")
        return True

    if flow == "add_utc_name":
        platform = context.user_data.get("section_platform", "Quotex")
        await add_dynamic_utc(platform, text)
        context.user_data.pop("admin_flow", None)
        context.user_data.pop("section_platform", None)
        await update.message.reply_text(f"✅ UTC added\nPlatform: {platform}\nUTC: {text}", reply_markup=admin_bottom_keyboard())
        await show_admin_panel(update)
        return True


    if flow == "set_accuracy":
        global ACCURACY_RANGE
        raw = text.strip().lower().replace(" ", "")
        context.user_data.pop("admin_flow", None)
        if raw in ["default", "auto", "reset"]:
            ACCURACY_RANGE = None
            await update.message.reply_text("✅ Accuracy set to AUTO / DEFAULT mode.", reply_markup=admin_bottom_keyboard())
            await show_admin_panel(update)
            return True
        try:
            parts = raw.replace(":", "-").split("-")
            low, high = int(parts[0]), int(parts[1])
            if low > high:
                low, high = high, low
            low = max(60, low)
            high = min(99, high)
            ACCURACY_RANGE = (low, high)
            await update.message.reply_text(f"✅ Accuracy updated successfully.\n🎯 Active Range: {low}% - {high}%", reply_markup=admin_bottom_keyboard())
            await show_admin_panel(update)
            return True
        except Exception:
            await update.message.reply_text("❌ Invalid format.\n\nExamples:\n80-90\n75-93\n90-93", reply_markup=admin_bottom_keyboard())
            await show_admin_panel(update)
            return True


    if flow == "auto_license_days":
        if not text.isdigit():
            return await update.message.reply_text("❌ Send days as number. Example: 7")
        context.user_data["license_data"]["days"] = int(text)
        context.user_data["admin_flow"] = "auto_license_devices"
        count = int(context.user_data["license_data"].get("count", 1))
        label = "each key" if count > 1 else "this key"
        return await update.message.reply_text(f"📱 Device limit for {label}? Example: 1 or 10")

    if flow == "auto_license_devices":
        if not text.isdigit():
            return await update.message.reply_text("❌ Send device limit as number. Example: 1")
        context.user_data["license_data"]["devices"] = int(text)
        context.user_data["admin_flow"] = "auto_license_prefix"
        return await update.message.reply_text("🔤 Prefix? Send 1-5 letters/numbers or send skip.")

    if flow == "auto_license_prefix":
        context.user_data["license_data"]["prefix"] = "" if text.lower() == "skip" else text
        context.user_data["admin_flow"] = "auto_license_suffix"
        return await update.message.reply_text("🔤 Suffix? Send 1-5 letters/numbers or send skip.")

    if flow == "auto_license_suffix":
        data = context.user_data.get("license_data", {})
        suffix = "" if text.lower() == "skip" else text
        count = max(1, min(20, int(data.get("count", 1))))
        days = data.get("days", 7)
        devices = data.get("devices", 1)
        prefix = data.get("prefix", "")
        existing_rows = await list_license_keys(10000)
        existing_keys = {r["license_key"] for r in existing_rows}
        generated_keys = set()
        rows = []
        attempts = 0

        while len(rows) < count and attempts < count * 30:
            attempts += 1
            key = make_license_key(prefix, suffix, 16)
            if key in generated_keys or key in existing_keys:
                continue
            row = await create_license_key(key, days, devices)
            rows.append(row)
            generated_keys.add(row["license_key"])
            existing_keys.add(row["license_key"])

        context.user_data.pop("admin_flow", None)
        context.user_data.pop("license_data", None)

        if not rows:
            await update.message.reply_text(
                "❌ Could not generate a unique license key. Try again with a shorter prefix/suffix.",
                reply_markup=admin_bottom_keyboard()
            )
            await show_admin_panel(update)
            return True

        if count == 1:
            row = rows[0]
            message = (
                f"✅ License Generated\n\n"
                f"🔑 Key: <code>{row['license_key']}</code>\n"
                f"📱 Devices: {row['max_devices']}\n"
                f"📅 Expiry: {row['expires_at']}"
            )
        else:
            key_lines = "\n".join(f"{i}. <code>{row['license_key']}</code>" for i, row in enumerate(rows, 1))
            message = (
                f"✅ Bulk Licenses Generated\n\n"
                f"Total: {len(rows)} / {count}\n"
                f"📅 Days: {days}\n"
                f"📱 Devices: {devices}\n\n"
                f"{key_lines}"
            )

        await update.message.reply_text(message, reply_markup=admin_bottom_keyboard(), parse_mode="HTML")
        await show_admin_panel(update)
        return True

    if flow == "custom_license_key":
        key = clean_license_key(text)
        if len(key) != 16:
            return await update.message.reply_text("❌ Custom license must be exactly 16 letters/numbers.")
        context.user_data["license_data"]["key"] = key
        context.user_data["admin_flow"] = "custom_license_days"
        return await update.message.reply_text("📅 Access days? Example: 7 or 30")

    if flow == "custom_license_days":
        if not text.isdigit():
            return await update.message.reply_text("❌ Send days as number.")
        context.user_data["license_data"]["days"] = int(text)
        context.user_data["admin_flow"] = "custom_license_devices"
        return await update.message.reply_text("📱 Device limit? Example: 1 or 10")

    if flow == "custom_license_devices":
        if not text.isdigit():
            return await update.message.reply_text("❌ Send device limit as number.")
        data = context.user_data.get("license_data", {})
        row = await create_license_key(data["key"], data.get("days", 7), int(text))
        context.user_data.pop("admin_flow", None)
        context.user_data.pop("license_data", None)
        await update.message.reply_text(
            f"✅ Custom License Created\n\n🔑 Key: <code>{row['license_key']}</code>\n📱 Devices: {row['max_devices']}\n📅 Expiry: {row['expires_at']}",
            reply_markup=admin_bottom_keyboard(),
            parse_mode="HTML"
        )
        await show_admin_panel(update)
        return True

    if flow == "deactivate_license":
        key = clean_license_key(text)
        row = await set_license_active(key, False)
        context.user_data.pop("admin_flow", None)
        await update.message.reply_text("🚫 License deactivated." if row else "❌ License not found.", reply_markup=admin_bottom_keyboard())
        await show_admin_panel(update)
        return True

    if flow == "activate_license":
        key = clean_license_key(text)
        row = await set_license_active(key, True)
        context.user_data.pop("admin_flow", None)
        await update.message.reply_text("✅ License activated." if row else "❌ License not found.", reply_markup=admin_bottom_keyboard())
        await show_admin_panel(update)
        return True

    if flow == "delete_license":
        key = clean_license_key(text)
        row = await delete_license_key(key)
        context.user_data.pop("admin_flow", None)
        await update.message.reply_text("🗑 License deleted." if row else "❌ License not found.", reply_markup=admin_bottom_keyboard())
        await show_admin_panel(update)
        return True

    return False

async def user_text_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()

    if is_admin(update.effective_user.id):
        handled = await admin_text_flow(update, context)
        if handled:
            return
        if text == "👑 Admin Panel":
            return await show_admin_panel(update)
        return

    flow = context.user_data.get("user_flow")

    if text == "🔐 Login":
        context.user_data["user_flow"] = "license_login"
        return await update.message.reply_text(
            "🔐 <b>SECURE LICENSE LOGIN</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Please send your 16-character license key.\n\n"
            "Example: <code>VIPA1B2C3D4E5F6</code>",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML"
        )


    if flow == "license_login":
        return await do_license_login(update, context, text)

    ok, sess = await license_session_active(update.effective_user.id)

    if flow == "custom_timeframe":
        custom_tf = text.strip().upper()
        if len(custom_tf) < 1 or len(custom_tf) > 10:
            return await update.message.reply_text("❌ Invalid timeframe. Example: M1, M5, 30S, H1")
        context.user_data.pop("user_flow", None)
        await update_session(update.effective_user.id, timeframe=custom_tf, clear_utc_time=True)
        ok2, sess2 = await license_session_active(update.effective_user.id)
        platform = (sess2 or {}).get("platform") or "Quotex"
        utc_items = await load_utc(platform)
        return await update.message.reply_text(
            f"⏱ <b>Timeframe:</b> {custom_tf}\\n\\n🌐 <b>Select UTC Session Time</b>",
            reply_markup=buttons_with_back(utc_items, "utc", "back_timeframes", cols=3),
            parse_mode="HTML"
        )

    if text == "📊 Get Signal":
        if not ok:
            return await update.message.reply_text("Please login first.", reply_markup=guest_bottom_keyboard())
        await update_session(
            update.effective_user.id,
            clear_platform=True,
            clear_market_type=True,
            clear_asset=True,
            clear_timeframe=True,
            clear_utc_time=True
        )
        return await update.message.reply_text(
            "📊 <b>Select Trading Platform</b>",
            reply_markup=buttons(await load_platforms(), "platform"),
            parse_mode="HTML"
        )


    if text == "👤 Profile":
        if not ok:
            return await update.message.reply_text("Please login first.", reply_markup=guest_bottom_keyboard())
        return await update.message.reply_text(
            "<b>👤 LICENSE PROFILE</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>🔑 License Key:</b> <code>{sess['license_key']}</code>\n"
            f"<b>🕘 Login Time:</b> {sess['first_login_at']}\n"
            f"<b>📅 Expiry Date:</b> {sess['expires_at']}",
            reply_markup=user_bottom_keyboard(),
            parse_mode="HTML"
        )


    if text == "🕘 History":
        if not ok:
            return await update.message.reply_text("Please login first.", reply_markup=guest_bottom_keyboard())
        return await update.message.reply_text(await build_history_text(update.effective_user.id), reply_markup=user_bottom_keyboard(), parse_mode="HTML")

    if text == "📤 Export History":
        if not ok:
            return await update.message.reply_text("Please login first.", reply_markup=guest_bottom_keyboard())
        return await send_history_export(update, context, update.effective_user.id)

    if text == "ℹ️ Info Bot":
        return await update.message.reply_text("<b>ℹ️ Bot Information</b>\n━━━━━━━━━━━━━━━━━━━━\n🤖 This bot provides professional market signal analysis using indicator-based logic.\n\n📊 <b>How it works</b>\nPlatform → Market → Asset → Timeframe → UTC → Signal Result\n\n🧠 <b>Analysis includes</b>\nEMA trend, MACD momentum, RSI zone, candle pattern, trend bias, market-based reasons, and global UTC timezone selection.\n\n⚠️ Trading involves risk. Use proper risk management.", reply_markup=user_bottom_keyboard() if ok else guest_bottom_keyboard(), parse_mode="HTML")

    if text == "🚪 Logout":
        await license_logout(update.effective_user.id)
        return await update.message.reply_text("🚪 Logged out.", reply_markup=guest_bottom_keyboard())

    await update.message.reply_text("Choose an option from the menu.", reply_markup=user_bottom_keyboard() if ok else guest_bottom_keyboard())

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    err = context.error
    if err:
        print(f"Bot error: {err}")

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN missing")
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("signal", signal_cmd))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_error_handler(error_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, user_text_flow))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
