def ema(values, period):
    if not values:
        return []
    k = 2 / (period + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(v*k + out[-1]*(1-k))
    return out

def rsi(values, period=14):
    if len(values) <= period:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(values)):
        d = values[i] - values[i-1]
        gains.append(max(d, 0))
        losses.append(abs(min(d, 0)))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def macd(values):
    if len(values) < 35:
        return 0, 0, 0
    e12, e26 = ema(values, 12), ema(values, 26)
    line = [a-b for a, b in zip(e12[-len(e26):], e26)]
    sig = ema(line, 9)
    return line[-1], sig[-1], line[-1] - sig[-1]

def candle_pattern(candles):
    if len(candles) < 2:
        return "Neutral"
    p, c = candles[-2], candles[-1]
    body = abs(c["close"] - c["open"])
    rng = max(c["high"] - c["low"], 0.00001)
    upper = c["high"] - max(c["open"], c["close"])
    lower = min(c["open"], c["close"]) - c["low"]
    if c["close"] > c["open"] and p["close"] < p["open"] and c["close"] > p["open"]:
        return "Bullish Engulfing"
    if c["close"] < c["open"] and p["close"] > p["open"] and c["close"] < p["open"]:
        return "Bearish Engulfing"
    if lower > body * 2 and upper < body:
        return "Hammer"
    if upper > body * 2 and lower < body:
        return "Shooting Star"
    if body / rng < 0.15:
        return "Doji"
    return "Neutral"

def analyze_signal(candles):
    closes = [c["close"] for c in candles]
    ema9 = ema(closes, 9)[-1]
    ema21 = ema(closes, 21)[-1]
    r = rsi(closes)
    _, _, m_hist = macd(closes)
    pattern = candle_pattern(candles)
    score, reasons = 0, []

    if ema9 > ema21:
        score += 1; reasons.append("EMA trend bullish")
    else:
        score -= 1; reasons.append("EMA trend bearish")
    if m_hist > 0:
        score += 1; reasons.append("MACD momentum bullish")
    else:
        score -= 1; reasons.append("MACD momentum bearish")
    if r < 30:
        score += 1; reasons.append("RSI oversold bounce zone")
    elif r > 70:
        score -= 1; reasons.append("RSI overbought risk zone")
    else:
        reasons.append("RSI neutral")
    if pattern in ["Bullish Engulfing", "Hammer"]:
        score += 1; reasons.append(f"Candle bullish: {pattern}")
    elif pattern in ["Bearish Engulfing", "Shooting Star"]:
        score -= 1; reasons.append(f"Candle bearish: {pattern}")
    else:
        reasons.append(f"Candle: {pattern}")

    signal = "BUY" if score >= 2 else "SELL" if score <= -2 else "WAIT"
    confidence = min(91, max(55, 60 + abs(score)*8))
    strength = "High" if abs(score) >= 3 else "Medium" if abs(score) == 2 else "Low"
    return {"signal": signal, "confidence": confidence, "trend_strength": strength, "rsi": round(r,2), "ema9": round(ema9,4), "ema21": round(ema21,4), "macd_hist": round(m_hist,5), "pattern": pattern, "reasons": reasons}
