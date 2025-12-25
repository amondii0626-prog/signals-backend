from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os, time, requests
from typing import List, Optional

app = FastAPI(title="Signals Backend", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Supported symbols
# -----------------------------
SYMBOLS = ["XAUUSD", "BTCUSD", "EURUSD", "GBPUSD", "USDJPY"]

# Timeframes: we keep your UI set
TF_MAP = {
    "1m":  ("1min",  300),
    "5m":  ("5min",  300),
    "15m": ("15min", 500),
    "30m": ("30min", 600),
    "1h":  ("1h",    800),
    "4h":  ("4h",    1200),
    "1d":  ("1day",  1200),
}

# Twelve Data API key (Render -> Environment)
TWELVE_KEY = os.getenv("TWELVE_DATA_API_KEY", "").strip()

# -----------------------------
# Indicators
# -----------------------------
def ema(values: List[float], period: int) -> List[Optional[float]]:
    if len(values) < period:
        return [None] * len(values)
    k = 2 / (period + 1)
    out: List[Optional[float]] = [None] * (period - 1)
    sma = sum(values[:period]) / period
    out.append(sma)
    prev = sma
    for v in values[period:]:
        prev = (v - prev) * k + prev
        out.append(prev)
    return out

def rsi(values: List[float], period: int = 14) -> List[Optional[float]]:
    if len(values) < period + 1:
        return [None] * len(values)

    gains, losses = [], []
    for i in range(1, period + 1):
        diff = values[i] - values[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    out: List[Optional[float]] = [None] * period
    out.append(100.0 if avg_loss == 0 else 100 - (100 / (1 + (avg_gain / avg_loss))))

    for i in range(period + 1, len(values)):
        diff = values[i] - values[i - 1]
        gain = max(diff, 0)
        loss = max(-diff, 0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        out.append(100.0 if avg_loss == 0 else 100 - (100 / (1 + (avg_gain / avg_loss))))
    return out

def atr(high: List[float], low: List[float], close: List[float], period: int = 14) -> List[Optional[float]]:
    if len(close) < period + 1:
        return [None] * len(close)
    trs = []
    for i in range(1, len(close)):
        tr = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )
        trs.append(tr)

    out: List[Optional[float]] = [None] * period
    first = sum(trs[:period]) / period
    out.append(first)
    prev = first
    for tr in trs[period:]:
        prev = (prev * (period - 1) + tr) / period
        out.append(prev)

    if len(out) < len(close):
        out += [None] * (len(close) - len(out))
    return out[:len(close)]

# -----------------------------
# Data fetchers
# -----------------------------
def fetch_binance_ohlc(symbol: str, tf: str, limit: int):
    # Binance uses symbols like BTCUSDT. We'll map BTCUSD -> BTCUSDT.
    if symbol != "BTCUSD":
        raise HTTPException(422, "Binance fetch only used for BTCUSD")
    tf_to_binance = {
        "1m":"1m","5m":"5m","15m":"15m","30m":"30m","1h":"1h","4h":"4h","1d":"1d"
    }
    interval = tf_to_binance.get(tf)
    if not interval:
        raise HTTPException(422, "Unsupported tf for Binance")

    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": "BTCUSDT", "interval": interval, "limit": min(limit, 1000)}
    r = requests.get(url, params=params, timeout=15)
    if r.status_code != 200:
        raise HTTPException(502, f"Binance error {r.status_code}")

    j = r.json()
    o, h, l, c = [], [], [], []
    for k in j:
        o.append(float(k[1])); h.append(float(k[2])); l.append(float(k[3])); c.append(float(k[4]))
    return o, h, l, c, "Binance:BTCUSDT"

def fetch_twelvedata_ohlc(symbol: str, tf: str, limit: int):
    if not TWELVE_KEY:
        raise HTTPException(500, "Missing TWELVE_DATA_API_KEY on server")

    interval, _need = TF_MAP[tf]
    # Twelve Data uses symbols like XAU/USD, EUR/USD, USD/JPY
    td_symbol_map = {
        "XAUUSD": "XAU/USD",
        "EURUSD": "EUR/USD",
        "GBPUSD": "GBP/USD",
        "USDJPY": "USD/JPY",
    }
    td_sym = td_symbol_map.get(symbol)
    if not td_sym:
        raise HTTPException(422, "Unsupported symbol for Twelve Data")

    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": td_sym,
        "interval": interval,
        "outputsize": min(limit, 5000),
        "apikey": TWELVE_KEY,
        "format": "JSON",
    }
    r = requests.get(url, params=params, timeout=20)
    if r.status_code != 200:
        raise HTTPException(502, f"TwelveData error {r.status_code}")

    data = r.json()
    if data.get("status") == "error":
        raise HTTPException(502, f"TwelveData: {data.get('message','error')}")

    values = data.get("values") or []
    if len(values) < 60:
        raise HTTPException(422, "Not enough candles from Twelve Data")

    # values is newest first -> reverse
    values = list(reversed(values))
    o, h, l, c = [], [], [], []
    for v in values:
        o.append(float(v["open"]))
        h.append(float(v["high"]))
        l.append(float(v["low"]))
        c.append(float(v["close"]))
    return o, h, l, c, f"TwelveData:{td_sym}({interval})"

def fetch_ohlc(symbol: str, tf: str):
    # choose provider per symbol
    interval, need = TF_MAP[tf]
    if symbol == "BTCUSD":
        return fetch_binance_ohlc(symbol, tf, need)
    else:
        return fetch_twelvedata_ohlc(symbol, tf, need)

# -----------------------------
# API
# -----------------------------
@app.get("/")
def root():
    return {"message": "signals backend running"}

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/symbols")
def symbols():
    return {"symbols": SYMBOLS}

@app.get("/timeframes")
def timeframes():
    return {"timeframes": list(TF_MAP.keys())}

@app.get("/analyze")
def analyze(
    symbol: str = Query("XAUUSD"),
    tf: str = Query("15m"),
):
    sym = symbol.upper().strip()
    if sym not in SYMBOLS:
        raise HTTPException(422, f"Unsupported symbol: {sym}")
    if tf not in TF_MAP:
        raise HTTPException(422, f"Unsupported timeframe: {tf}")

    o, h, l, c, source = fetch_ohlc(sym, tf)

    ema50 = ema(c, 50)
    ema200 = ema(c, 200)
    rsi14 = rsi(c, 14)
    atr14 = atr(h, l, c, 14)

    last = len(c) - 1
    e50 = ema50[last]; e200 = ema200[last]; r = rsi14[last]; a = atr14[last]
    if e50 is None or e200 is None or r is None or a is None:
        raise HTTPException(422, "Indicators not ready")

    entry = c[last]
    trend = "BUY" if e50 > e200 else "SELL"

    sl_mult = 1.2
    rr = 2.0

    if trend == "BUY":
        stop_loss = entry - a * sl_mult
        take_profit = entry + (entry - stop_loss) * rr
    else:
        stop_loss = entry + a * sl_mult
        take_profit = entry - (stop_loss - entry) * rr

    # Confidence (simple)
    sep = abs(e50 - e200) / entry
    sep_score = min(40, sep * 4000)
    if trend == "BUY":
        rsi_score = 30 if r >= 55 else 15 if r >= 50 else 5
    else:
        rsi_score = 30 if r <= 45 else 15 if r <= 50 else 5
    atr_rel = a / entry
    vol_penalty = 10 if atr_rel > 0.01 else 0
    vol_penalty = 20 if atr_rel > 0.02 else vol_penalty

    conf = int(max(35, min(90, 30 + sep_score + rsi_score - vol_penalty)))

    # decimals: gold 2dp, forex 5dp, crypto 2dp
    if sym == "XAUUSD" or sym == "BTCUSD":
        dp = 2
    else:
        dp = 5

    return {
        "symbol": sym,
        "timeframe": tf,
        "source": source,
        "trend": trend,
        "entry": round(entry, dp),
        "stop_loss": round(stop_loss, dp),
        "take_profit": round(take_profit, dp),
        "indicators": {
            "ema50": round(e50, dp),
            "ema200": round(e200, dp),
            "rsi14": round(r, 2),
            "atr14": round(a, 6),
        },
        "confidence": f"{conf}%",
    }
