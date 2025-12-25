from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Signals Backend",
    version="1.1.0",
)

# ---- CORS ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # GitHub Pages-д OK
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Static lists (frontend dropdown-д хэрэгтэй) ----
SYMBOLS = ["XAUUSD", "BTCUSD", "EURUSD", "GBPUSD", "USDJPY"]
TIMEFRAMES = ["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d"]

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
    return {"timeframes": TIMEFRAMES}

@app.get("/analyze")
def analyze(
    symbol: str = Query("XAUUSD", description="e.g. XAUUSD, BTCUSD, EURUSD"),
    # ✅ frontend 'tf' гэж явуулсан ч болно, 'timeframe' гэж явуулсан ч болно
    tf: str | None = Query(None, description="e.g. 1m, 5m, 15m, 1h"),
    timeframe: str | None = Query(None, description="alias for tf"),
):
    # tf / timeframe аль ирснийг сонгоё
    chosen_tf = (tf or timeframe or "15m").strip()

    if chosen_tf not in TIMEFRAMES:
        return {
            "error": "Invalid timeframe",
            "allowed": TIMEFRAMES,
            "received": chosen_tf,
        }

    sym = symbol.strip().upper()

    # ---- MOCK ANALYSIS (чи хүсвэл дараа нь бодит логик холбоно) ----
    if sym == "BTCUSD":
        trend = "BUY"
        entry = 42000
        stop_loss = 41999.04
        take_profit = 42001.68
    else:
        trend = "SELL"
        entry = 2026
        stop_loss = 2026.96
        take_profit = 2024.32

    return {
        "symbol": sym,
        "timeframe": chosen_tf,
        "trend": trend,
        "entry": entry,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "confidence": "74%",
    }
