from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Signals Backend",
    version="1.0.0"
)

# ===== CORS =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== ROOT =====
@app.get("/")
def root():
    return {"message": "Signals backend running"}

# ===== HEALTH =====
@app.get("/health")
def health():
    return {"ok": True}

# ===== ANALYZE =====
@app.get("/analyze")
def analyze(
    symbol: str = Query(..., description="XAUUSD, BTCUSD, EURUSD"),
    timeframe: str = Query("15m", description="1m, 5m, 15m, 1h")
):
    """
    Analyze trading signal
    """

    # ✅ FRONTEND-ЭЭС ИРСЭН timeframe-г ШУУД ашиглана
    tf = timeframe

    # ----- MOCK ANALYSIS -----
    if symbol.upper() == "BTCUSD":
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
        "symbol": symbol.upper(),
        "timeframe": tf,   # ✅ ОДОО ЗӨВ
        "trend": trend,
        "entry": entry,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "confidence": "74%"
    }
