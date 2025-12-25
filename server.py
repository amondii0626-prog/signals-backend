from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Signals Backend",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"ok": True}

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/symbols")
def symbols():
    return {
        "symbols": ["XAUUSD", "BTCUSD", "EURUSD"]
    }

@app.get("/timeframes")
def timeframes():
    return {
        "timeframes": ["1m", "5m", "15m", "1h", "4h", "1d"]
    }

@app.get("/analyze")
def analyze(
    symbol: str = Query(...),
    tf: str = Query("15m")
):
    if symbol.upper() == "XAUUSD":
        trend = "SELL"
        entry = 4479.0
        stop_loss = 4485.0
        take_profit = 4465.0
    else:
        trend = "BUY"
        entry = 100.0
        stop_loss = 95.0
        take_profit = 110.0

    return {
        "symbol": symbol.upper(),
        "timeframe": tf,
        "trend": trend,
        "entry": entry,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "confidence": "74%"
    }
