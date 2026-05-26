import os, random, aiohttp, time

_cache = {}

async def get_binance_klines(symbol="BTCUSDT", interval="1m", limit=100):
    key = f"{symbol}:{interval}:{limit}"
    now = time.time()
    if key in _cache and now - _cache[key]["time"] < 20:
        return _cache[key]["data"]

    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    timeout = aiohttp.ClientTimeout(total=8)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as resp:
            resp.raise_for_status()
            data = await resp.json()

    candles = [{"open": float(k[1]), "high": float(k[2]), "low": float(k[3]), "close": float(k[4]), "volume": float(k[5])} for k in data]
    _cache[key] = {"time": now, "data": candles}
    return candles

def demo_candles(limit=100):
    price = random.uniform(80, 150)
    candles = []
    for _ in range(limit):
        change = random.uniform(-1.9, 1.9)
        open_p = price
        close_p = max(1, open_p + change)
        high = max(open_p, close_p) + random.uniform(0.1, 1.2)
        low = min(open_p, close_p) - random.uniform(0.1, 1.2)
        candles.append({"open": open_p, "high": high, "low": low, "close": close_p, "volume": random.uniform(900, 12000)})
        price = close_p
    return candles

async def get_market_candles(platform, market_type, asset, timeframe):
    use_live = os.getenv("USE_LIVE_BINANCE", "false").lower() == "true"
    if use_live and market_type == "USDT" and str(asset).upper().endswith("USDT"):
        try:
            return await get_binance_klines(str(asset).upper(), timeframe, 100)
        except Exception:
            return demo_candles()
    return demo_candles()
