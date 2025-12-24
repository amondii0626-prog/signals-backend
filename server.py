from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPPORTED_SYMBOLS: List[str] = ["XAUUSD", "XAGUSD", "BTCUSD", "EURUSD", "GBPUSD", "USDJPY"]
SUPPORTED_TIMEFRAMES: List[str] = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "signals-backend is running ✅",
        "how_to_use": "/analyze?symbol=XAUUSD&tf=15m",
        "supported_symbols": SUPPORTED_SYMBOLS,
        "supported_timeframes": SUPPORTED_TIMEFRAMES,
    }


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/analyze")
def analyze(
    symbol: str = Query("XAUUSD"),
    tf: str = Query("15m"),
):
    symbol = symbol.upper().strip()
    tf = tf.strip()

    if symbol not in SUPPORTED_SYMBOLS:
        return {"error": "Unsupported symbol", "supported_symbols": SUPPORTED_SYMBOLS}

    if tf not in SUPPORTED_TIMEFRAMES:
        return {"error": "Unsupported timeframe", "supported_timeframes": SUPPORTED_TIMEFRAMES}

    # ✅ Түр demo логик (дараа нь жинхэнэ анализ нэмнэ)
    base = {
        "XAUUSD": 2026.00,
        "XAGUSD": 24.80,
        "BTCUSD": 42000.0,
        "EURUSD": 1.0900,
        "GBPUSD": 1.2700,
        "USDJPY": 156.00,
    }[symbol]

    trend = "BUY" if symbol in ["BTCUSD", "EURUSD"] else "SELL"

    # timeframe-аас шалтгаалж алхам өөр болгоё
    step = {
        "1m": 0.15,
        "5m": 0.35,
        "15m": 0.60,
        "30m": 0.90,
        "1h": 1.20,
        "4h": 1.80,
        "1d": 2.50,
    }[tf]

    # SL/TP тооцоо (demo)
    if symbol in ["EURUSD", "GBPUSD"]:
        step = step / 100  # FX жижиг алхам
    if symbol == "USDJPY":
        step = step / 10

    entry = round(base, 4)
    if trend == "BUY":
        stop_loss = round(entry - step * 1.6, 4)
        take_profit = round(entry + step * 2.8, 4)
    else:
        stop_loss = round(entry + step * 1.6, 4)
        take_profit = round(entry - step * 2.8, 4)

    confidence = "74%"

    return {
        "symbol": symbol,
        "timeframe": tf,
        "trend": trend,
        "entry": entry,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "confidence": confidence,
    }
