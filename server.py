from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import random

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPPORTED_SYMBOLS = [
    "XAUUSD", "XAGUSD",
    "BTCUSD", "ETHUSD",
    "EURUSD", "GBPUSD", "USDJPY"
]

SUPPORTED_TF = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Signals backend is running ✅",
        "how_to_use": "/analyze?symbol=XAUUSD&tf=15m",
        "supported_symbols": SUPPORTED_SYMBOLS,
        "supported_timeframes": SUPPORTED_TF
    }


@app.get("/analyze")
def analyze(
    symbol: str = Query(..., description="Trading symbol"),
    tf: str = Query("15m", description="Timeframe")
):
    symbol = symbol.upper()

    if symbol not in SUPPORTED_SYMBOLS:
        return {"error": f"Unsupported symbol: {symbol}"}

    if tf not in SUPPORTED_TF:
        return {"error": f"Unsupported timeframe: {tf}"}

    trend = random.choice(["BUY", "SELL"])

    base_price = {
        "XAUUSD": 2035,
        "XAGUSD": 24.5,
        "BTCUSD": 43000,
        "ETHUSD": 2300,
        "EURUSD": 1.09,
        "GBPUSD": 1.27,
        "USDJPY": 148
    }[symbol]

    entry = round(base_price * random.uniform(0.995, 1.005), 2)

    sl = round(entry * (0.995 if trend == "BUY" else 1.005), 2)
    tp = round(entry * (1.01 if trend == "BUY" else 0.99), 2)

    confidence = f"{random.randint(65, 85)}%"

    return {
        "symbol": symbol,
        "timeframe": tf,
        "trend": trend,
        "entry": entry,
        "stop_loss": sl,
        "take_profit": tp,
        "confidence": confidence
    }
