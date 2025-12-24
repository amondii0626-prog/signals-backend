from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import random

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

@app.get("/signal")
def signal(symbol: str = "XAUUSD", tf: str = "15m"):
    directions = ["BUY", "SELL", "WAIT"]
    direction = random.choice(directions)

    return {
        "symbol": symbol,
        "timeframe": tf,
        "direction": direction,
        "entry": round(random.uniform(2300, 2400), 2),
        "sl": round(random.uniform(2280, 2295), 2),
        "tp": round(random.uniform(2410, 2450), 2),
        "time": datetime.utcnow().isoformat()
    }
