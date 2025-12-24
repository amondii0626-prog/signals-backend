from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Signals Backend", version="1.0.0")

# CORS (frontend github.io-с fetch хийхэд хэрэгтэй)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # дараа нь хүсвэл github.io domain руу хязгаарлаж болно
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Дэмжих symbol жагсаалт (хүсвэл нэмээд яв)
SUPPORTED_SYMBOLS = {
    "XAUUSD": "Gold",
    "XAGUSD": "Silver",
    "BTCUSD": "Bitcoin",
    "EURUSD": "Euro / USD",
    "GBPUSD": "Pound / USD",
    "USDJPY": "USD / JPY",
}

SUPPORTED_TF = {"1m", "5m", "15m", "30m", "1h", "4h", "1d"}


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Signals backend is running ✅",
        "how_to_use": "/analyze?symbol=XAUUSD&tf=15m",
        "supported_symbols": list(SUPPORTED_SYMBOLS.keys()),
        "supported_timeframes": list(SUPPORTED_TF),
    }


@app.get("/symbols")
def symbols():
    return SUPPORTED_SYMBOLS


@app.get("/analyze")
def analyze(
    symbol: str = Query("XAUUSD"),
    tf: str = Query("15m"),
):
    symbol = symbol.upper().replace("/", "")
    tf = tf.lower()

    # Timeframe validation
    if tf not in SUPPORTED_TF:
        return {
            "error": "Unsupported timeframe",
            "supported_timeframes": list(SUPPORTED_TF),
            "you_sent": tf,
        }

    # Symbol validation (хүсвэл validation-ийг унтрааж болно)
    if symbol not in SUPPORTED_SYMBOLS:
        return {
            "error": "Unsupported symbol",
            "supported_symbols": list(SUPPORTED_SYMBOLS.keys()),
            "you_sent": symbol,
            "tip": "Use like BTCUSD, XAUUSD, XAGUSD (no slash) or XAU/USD also works.",
        }

    # ✅ Одоохондоо demo signal (дараа нь бодит logic хийж өгнө)
    signal = {
        "symbol": symbol,
        "name": SUPPORTED_SYMBOLS[symbol],
        "timeframe": tf,
        "trend": "BUY",
        "entry": 2034.5,
        "stop_loss": 2028.0,
        "take_profit": 2050.0,
        "confidence": "78%",
    }
    return signal
