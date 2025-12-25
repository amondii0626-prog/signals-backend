from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
from typing import List, Dict, Any, Optional

app = FastAPI(title="Signals Backend", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Symbol mapping (your UI symbols -> Yahoo tickers)
# -----------------------------
SYMBOL_MAP = {
    "BTCUSD": "BTC-USD",
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
    # XAUUSD (Spot) шууд Yahoo дээр тогтвортой ticker олдохгүй үед:
    # Gold futures ашиглая:
    "XAUUSD": "GC=F",
}

# -----------------------------
# Timeframe mapping (your UI tf -> Yahoo interval + range)
# Yahoo intervals: 1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo
# -----------------------------
TF_MAP = {
    "1m":  ("1m",  "1d"),
    "5m":  ("5m",  "5d"),
    "15m": ("15m", "5d"),
    "1h":  ("60m", "1mo"),
    "4h":  ("60m", "3mo"),   # Yahoo 4h байхгүй → 60m татаж аваад доор нь 4 цагт агрегат хийх (хялбар хувилбар: 60m дээр анализ)
    "1d":  ("1d",  "6mo"),
}

DEFAULT_SYMBOLS = list(SYMBOL_MAP.keys())
DEFAULT_TFS = list(TF_MAP.keys())


# -----------------------------
# Helpers: indicators
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

    gains = []
    losses = []
    for i in range(1, period + 1):
        diff = values[i] - values[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    out: List[Optional[float]] = [None] * period
    if avg_loss == 0:
        out.append(100.0)
    else:
        rs = avg_gain / avg_loss
        out.append(100 - (100 / (1 + rs)))

    for i in range(period + 1, len(values)):
        diff = values[i] - values[i - 1]
        gain = max(diff, 0)
        loss = max(-diff, 0)

        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

        if avg_loss == 0:
            out.append(100.0)
        else:
            rs = avg_gain / avg_loss
            out.append(100 - (100 / (1 + rs)))

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

    # first ATR = SMA(TR)
    out: List[Optional[float]] = [None] * period
    first_atr = sum(trs[:period]) / period
    out.append(first_atr)
    prev = first_atr

    for tr in trs[period:]:
        prev = (prev * (period - 1) + tr) / period
        out.append(prev)

    # out length = len(close) (because trs is len-1; we aligned by padding)
    # Ensure exact length:
    if len(out) < len(close):
        out = out + [None] * (len(close) - len(out))
    return out[:len(close)]


# -----------------------------
# Yahoo fetch: OHLC
# -----------------------------
def fetch_yahoo_ohlc(yahoo_symbol: str, interval: str, range_: str) -> Dict[str, List[float]]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}"
    params = {
        "interval": interval,
        "range": range_,
        "includePrePost": "false",
        "events": "div,splits",
    }
    r = requests.get(url, params=params, timeout=15)
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Yahoo fetch failed: {r.status_code}")

    data = r.json()
    chart = data.get("chart", {})
    err = chart.get("error")
    if err:
        raise HTTPException(status_code=502, detail=f"Yahoo error: {err}")

    result = chart.get("result")
    if not result:
        raise HTTPException(status_code=502, detail="Yahoo empty result")

    res0 = result[0]
    indicators = res0.get("indicators", {})
    quote = (indicators.get("quote") or [{}])[0]

    h = quote.get("high") or []
    l = quote.get("low") or []
    c = quote.get("close") or []
    o = quote.get("open") or []

    # Remove None rows (Yahoo sometimes has None)
    high, low, close, open_ = [], [], [], []
    for i in range(len(c)):
        if c[i] is None or h[i] is None or l[i] is None or o[i] is None:
            continue
        high.append(float(h[i]))
        low.append(float(l[i]))
        close.append(float(c[i]))
        open_.append(float(o[i]))

    if len(close) < 60:
        raise HTTPException(status_code=422, detail="Not enough candles from Yahoo")

    return {"open": open_, "high": high, "low": low, "close": close}


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
    return {"symbols": DEFAULT_SYMBOLS}

@app.get("/timeframes")
def timeframes():
    return {"timeframes": DEFAULT_TFS}

@app.get("/analyze")
def analyze(
    symbol: str = Query("XAUUSD", description="XAUUSD, BTCUSD, EURUSD..."),
    tf: str = Query("15m", description="1m, 5m, 15m, 1h, 4h, 1d"),
):
    sym = symbol.upper().strip()
    if sym not in SYMBOL_MAP:
        raise HTTPException(status_code=422, detail=f"Unsupported symbol: {sym}")

    if tf not in TF_MAP:
        raise HTTPException(status_code=422, detail=f"Unsupported timeframe: {tf}")

    yahoo_symbol = SYMBOL_MAP[sym]
    interval, range_ = TF_MAP[tf]

    ohlc = fetch_yahoo_ohlc(yahoo_symbol, interval, range_)
    close = ohlc["close"]
    high = ohlc["high"]
    low = ohlc["low"]

    ema50 = ema(close, 50)
    ema200 = ema(close, 200)
    rsi14 = rsi(close, 14)
    atr14 = atr(high, low, close, 14)

    last = len(close) - 1

    e50 = ema50[last]
    e200 = ema200[last]
    r = rsi14[last]
    a = atr14[last]

    if e50 is None or e200 is None or r is None or a is None:
        raise HTTPException(status_code=422, detail="Indicators not ready (need more candles)")

    entry = close[last]

    # Trend rule (EMA50 vs EMA200)
    trend = "BUY" if e50 > e200 else "SELL"

    # SL/TP using ATR
    sl_mult = 1.2
    rr = 2.0  # take profit = 2R

    if trend == "BUY":
        stop_loss = entry - a * sl_mult
        take_profit = entry + (entry - stop_loss) * rr
    else:
        stop_loss = entry + a * sl_mult
        take_profit = entry - (stop_loss - entry) * rr

    # Confidence scoring (simple but real)
    # Factors:
    # 1) EMA separation
    # 2) RSI alignment
    # 3) ATR (too wild -> reduce)
    sep = abs(e50 - e200) / entry  # relative separation
    sep_score = min(40, sep * 4000)  # scaled

    if trend == "BUY":
        rsi_score = 30 if r >= 55 else 15 if r >= 50 else 5
    else:
        rsi_score = 30 if r <= 45 else 15 if r <= 50 else 5

    atr_rel = a / entry
    vol_penalty = 0
    if atr_rel > 0.01:
        vol_penalty = 10
    if atr_rel > 0.02:
        vol_penalty = 20

    raw = 30 + sep_score + rsi_score - vol_penalty
    conf = max(35, min(90, int(raw)))

    return {
        "symbol": sym,
        "timeframe": tf,
        "source": f"Yahoo:{yahoo_symbol} ({interval}/{range_})",
        "trend": trend,
        "entry": round(entry, 2),
        "stop_loss": round(stop_loss, 2),
        "take_profit": round(take_profit, 2),
        "indicators": {
            "ema50": round(e50, 2),
            "ema200": round(e200, 2),
            "rsi14": round(r, 2),
            "atr14": round(a, 4),
        },
        "confidence": f"{conf}%",
    }
