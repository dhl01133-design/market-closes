"""Fetch the latest US market closes and write markets.json.

Runs in GitHub Actions (.github/workflows/markets.yml) after the US close.
Claude's 08:17 KakaoTalk briefing reads the raw markets.json from this repo.
No API key needed (Yahoo Finance public chart data).
"""
import json
import time
import datetime as dt
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

SYMBOLS = {
    "nasdaq": "^IXIC",    # Nasdaq Composite
    "sp500": "^GSPC",     # S&P 500
    "qld": "QLD",         # ProShares Ultra QQQ
    "dxy": "DX-Y.NYB",    # US Dollar Index
}
NY = ZoneInfo("America/New_York")
HEADERS = {"User-Agent": "Mozilla/5.0 (market-closes; GitHub Actions)"}
OUT = "markets.json"


def fetch(symbol):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.parse.quote(symbol) + "?range=10d&interval=1d")
    err = ""
    for _ in range(3):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as r:
                res = json.load(r)["chart"]["result"][0]
            rows = [(t, c) for t, c in zip(res["timestamp"], res["indicators"]["quote"][0]["close"])
                    if c is not None]
            (t1, c1), (_, c0) = rows[-1], rows[-2]
            session = dt.datetime.fromtimestamp(t1, NY).date()
            now_ny = dt.datetime.now(NY)
            final = session < now_ny.date() or now_ny.time() >= dt.time(16, 15)
            return {
                "symbol": symbol,
                "session_date": session.isoformat(),
                "close": round(c1, 2),
                "prev_close": round(c0, 2),
                "change_pct": round((c1 / c0 - 1) * 100, 2),
                "final": final,
            }
        except Exception as e:  # network hiccup or odd response: retry
            err = f"{type(e).__name__}: {e}"
            time.sleep(5)
    return {"symbol": symbol, "error": err}


def main():
    try:
        old = json.load(open(OUT, encoding="utf-8")).get("data", {})
    except Exception:
        old = {}
    data = {}
    for key, sym in SYMBOLS.items():
        got = fetch(sym)
        if "error" in got and key in old and "error" not in old[key]:
            got = {**old[key], "stale": True, "last_error": got["error"]}
        data[key] = got
        print(key, got)
    out = {"updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "data": data}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
