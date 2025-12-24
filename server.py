from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "signals-backend running"}

@app.get("/analyze")
def analyze(symbol: str = "XAUUSD", tf: str = "15m"):
    signal = {
        "symbol": symbol,
        "timeframe": tf,
        "trend": "BUY",
        "entry": 2034.5,
        "stop_loss": 2028.0,
        "take_profit": 2050.0,
        "confidence": "78%"
    }
    return signal
