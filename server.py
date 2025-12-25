from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
import time

app = FastAPI(title="Signals Backend", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_SYMBOLS = ["XAUUSD", "BTCUSDT", "EURUSD", "GBPUSD", "USDJPY"]
DEFAULT_TFS = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]

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

def get_btc_binance():
    r = requests.get("https://api.binance.com/api/v3/ticker/bookTicker?symbol=BTCUSDT", timeout=10)
    r.raise_for_status()
    j = r.json()
    return float(j["bidPrice"]), float(j["askPrice"])

def get_xau_yahoo():
    # Yahoo: Gold futures GC=F (approx), not exactly XAUUSD broker feed
    url = "https://query1.finance.yahoo.com/v7/finance/quote?symbols=GC=F"
    r = requests.get(url, timeout=10, headers={"User-Agent":"Mozilla/5.0"})
    r.raise_for_status()
    j = r.json()
    result = j["quoteResponse"]["result"]
    if not result:
        raise RuntimeError("Yahoo no data")
    p = result[0].get("regularMarketPrice")
    if p is None:
        raise RuntimeError("Yahoo price missing")
    price = float(p)
    # Fake bid/ask as +/- small spread (public feed does not provide)
    bid = price - 0.1
    ask = price + 0.1
    return bid, ask, price

@app.get("/quote")
def quote(symbol: str = Query("XAUUSD")):
    symbol = symbol.upper()

    try:
        if symbol == "BTCUSDT":
            bid, ask = get_btc_binance()
            return {"ok": True, "symbol": symbol, "bid": bid, "ask": ask, "time": int(time.time())}

        if symbol == "XAUUSD":
            bid, ask, last = get_xau_yahoo()
            return {"ok": True, "symbol": symbol, "bid": bid, "ask": ask, "last": last, "source": "Yahoo GC=F", "time": int(time.time())}

        return {"ok": False, "error": f"Quote source not implemented for {symbol}. Use BTCUSDT or XAUUSD."}

    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/analyze")
def analyze(
    symbol: str = Query("XAUUSD"),
    tf: str = Query("15m"),
    rr: float = Query(2.0),
):
    symbol = symbol.upper()

    q = quote(symbol)
    if not q.get("ok"):
        return {"ok": False, "error": q.get("error", "quote failed")}

    bid = float(q["bid"])
    ask = float(q["ask"])
    spread = max(ask - bid, 0.0)

    # Demo direction (replace later with real strategy)
    direction = "BUY" if int(bid * 10) % 2 == 0 else "SELL"
    entry = ask if direction == "BUY" else bid

    # SL distance: spread*3 + buffer
    buf = 0.5 if symbol == "XAUUSD" else 20.0
    sl_dist = spread * 3 + buf

    if direction == "BUY":
        sl = entry - sl_dist
        tp = entry + sl_dist * rr
    else:
        sl = entry + sl_dist
        tp = entry - sl_dist * rr

    return {
        "ok": True,
        "symbol": symbol,
        "timeframe": tf,
        "trend": direction,
        "entry": round(entry, 2),
        "stop_loss": round(sl, 2),
        "take_profit": round(tp, 2),
        "bid": round(bid, 2),
        "ask": round(ask, 2),
        "spread": round(spread, 2),
        "source": q.get("source", "Binance"),
        "note": "Render uses public feed. FTMO/MT5 price will differ slightly.",
    }
