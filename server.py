from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os, time, requests
from typing import List, Optional

app = FastAPI(title="Signals Backend", version="3.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- Config --------------------
SYMBOLS = ["XAUUSD", "BTCUSDT", "EURUSD", "GBPUSD", "USDJPY"]
TFS = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]

TWELVE_KEY = (os.getenv("TWELVE_DATA_API_KEY") or "").strip()

TD_TF = {"1m":"1min","5m":"5min","15m":"15min","30m":"30min","1h":"1h","4h":"4h","1d":"1day"}
TD_SYM = {"XAUUSD":"XAU/USD","EURUSD":"EUR/USD","GBPUSD":"GBP/USD","USDJPY":"USD/JPY"}

TF_BINANCE = {"1m":"1m","5m":"5m","15m":"15m","30m":"30m","1h":"1h","4h":"4h","1d":"1d"}

# -------------------- Indicators --------------------
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
        d = values[i] - values[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    out: List[Optional[float]] = [None] * period
    out.append(100.0 if avg_loss == 0 else 100 - (100 / (1 + (avg_gain / avg_loss))))

    for i in range(period + 1, len(values)):
        d = values[i] - values[i - 1]
        gain = max(d, 0)
        loss = max(-d, 0)
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

# -------------------- Data fetchers --------------------
def binance_klines_btc(tf: str, limit: int = 600):
    interval = TF_BINANCE.get(tf)
    if not interval:
        raise HTTPException(422, "Unsupported timeframe")

    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": "BTCUSDT", "interval": interval, "limit": min(limit, 1000)}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    j = r.json()

    o,h,l,c = [],[],[],[]
    for k in j:
        o.append(float(k[1])); h.append(float(k[2])); l.append(float(k[3])); c.append(float(k[4]))
    return o,h,l,c, "Binance:BTCUSDT"

def binance_quote_btc():
    r = requests.get("https://api.binance.com/api/v3/ticker/bookTicker?symbol=BTCUSDT", timeout=10)
    r.raise_for_status()
    j = r.json()
    return float(j["bidPrice"]), float(j["askPrice"]), "Binance:BTCUSDT"

def twelvedata_series(symbol: str, tf: str, outputsize: int = 1200):
    if not TWELVE_KEY:
        raise HTTPException(500, "TWELVE_DATA_API_KEY not set on server")

    td_symbol = TD_SYM.get(symbol)
    if not td_symbol:
        raise HTTPException(422, "Symbol not supported for TwelveData")

    interval = TD_TF.get(tf)
    if not interval:
        raise HTTPException(422, "Unsupported timeframe")

    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": td_symbol,
        "interval": interval,
        "outputsize": min(outputsize, 5000),
        "apikey": TWELVE_KEY,
        "format": "JSON",
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()

    if data.get("status") == "error":
        raise HTTPException(502, f"TwelveData: {data.get('message','error')}")

    values = data.get("values") or []
    if len(values) < 220:
        raise HTTPException(422, "Not enough candles from TwelveData")

    values = list(reversed(values))  # newest->oldest to oldest->newest
    o,h,l,c = [],[],[],[]
    for v in values:
        o.append(float(v["open"]))
        h.append(float(v["high"]))
        l.append(float(v["low"]))
        c.append(float(v["close"]))
    return o,h,l,c, f"TwelveData:{td_symbol}({interval})"

# -------------------- API --------------------
@app.get("/")
def root():
    return {"message": "signals backend running"}

@app.get("/health")
def health():
    return {"ok": True, "twelvedata_key_set": bool(TWELVE_KEY)}

@app.get("/symbols")
def symbols():
    return {"symbols": SYMBOLS}

@app.get("/timeframes")
def timeframes():
    return {"timeframes": TFS}

@app.get("/quote")
def quote(symbol: str = Query("XAUUSD")):
    s = symbol.upper().strip()

    if s == "BTCUSDT":
        bid, ask, src = binance_quote_btc()
        return {"ok": True, "symbol": s, "bid": bid, "ask": ask, "source": src, "time": int(time.time())}

    if s in TD_SYM:
        # TwelveData байхгүй бол quote хийх боломжгүй
        if not TWELVE_KEY:
            return {"ok": False, "error": "Set TWELVE_DATA_API_KEY for XAU/FX quotes"}
        # 1m close-оос last гэж үзээд жижиг spread дуурайлгана
        o,h,l,c, src = twelvedata_series(s, "1m", outputsize=60)
        last = c[-1]
        bid = last - 0.05
        ask = last + 0.05
        return {"ok": True, "symbol": s, "bid": bid, "ask": ask, "source": src, "time": int(time.time())}

    return {"ok": False, "error": f"Unsupported symbol: {s}"}

@app.get("/analyze")
def analyze(symbol: str = Query("XAUUSD"), tf: str = Query("15m")):
    s = symbol.upper().strip()
    if s not in SYMBOLS:
        raise HTTPException(422, "Unsupported symbol")
    if tf not in TFS:
        raise HTTPException(422, "Unsupported timeframe")

    # OHLC авах
    if s == "BTCUSDT":
        o,h,l,c, source = binance_klines_btc(tf, limit=600)
    else:
        # XAU/FX нь TwelveData шаардлагатай
        if s not in TD_SYM:
            raise HTTPException(422, f"OHLC not configured for {s}")
        if not TWELVE_KEY:
            raise HTTPException(500, "TWELVE_DATA_API_KEY not set (needed for XAU/FX analysis)")
        o,h,l,c, source = twelvedata_series(s, tf, outputsize=1200)

    ema50 = ema(c, 50)
    ema200 = ema(c, 200)
    rsi14 = rsi(c, 14)
    atr14 = atr(h, l, c, 14)

    last = len(c) - 1
    e50 = ema50[last]; e200 = ema200[last]; r = rsi14[last]; a = atr14[last]
    if e50 is None or e200 is None or r is None or a is None:
        raise HTTPException(422, "Indicators not ready")

    trend = "BUY" if e50 > e200 else "SELL"
    entry = c[last]

    sl_mult = 1.2
    rr = 2.0
    if trend == "BUY":
        sl = entry - a * sl_mult
        tp = entry + (entry - sl) * rr
    else:
        sl = entry + a * sl_mult
        tp = entry - (sl - entry) * rr

    sep = abs(e50 - e200) / entry
    sep_score = min(40, sep * 4000)
    if trend == "BUY":
        rsi_score = 30 if r >= 55 else 15 if r >= 50 else 5
    else:
        rsi_score = 30 if r <= 45 else 15 if r <= 50 else 5
    conf = int(max(35, min(90, 30 + sep_score + rsi_score)))

    dp = 2 if s in ["XAUUSD", "BTCUSDT"] else 5

    return {
        "ok": True,
        "symbol": s,
        "timeframe": tf,
        "trend": trend,
        "entry": round(entry, dp),
        "stop_loss": round(sl, dp),
        "take_profit": round(tp, dp),
        "confidence": f"{conf}%",
        "source": source,
        "indicators": {
            "ema50": round(e50, dp),
            "ema200": round(e200, dp),
            "rsi14": round(r, 2),
            "atr14": round(a, 6),
        },
        "note": "Public API mode (no PC). XAU/FX uses TwelveData; BTC uses Binance.",
    }
