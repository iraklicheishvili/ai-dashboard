"""
Stock and ETF data via yfinance.
Pulls daily price, day-over-day change, 1-year return, AUM, and 90-day spark history.
"""

from typing import List, Dict, Optional
import yfinance as yf

import config


def fetch_etf_data(ticker: str) -> Optional[Dict]:
    """
    Fetch current price, DoD change, 1-year return, AUM, and 90-day price history.
    """
    try:
        t = yf.Ticker(ticker)
        info = t.info

        hist = t.history(period="1y")
        if hist.empty:
            return None

        current = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current
        dod_change = current - prev
        dod_pct = (dod_change / prev * 100) if prev else 0

        year_ago = float(hist["Close"].iloc[0])
        yr_return_pct = ((current - year_ago) / year_ago * 100) if year_ago else 0

        # 90-day spark
        spark = [round(float(p), 2) for p in hist["Close"].tail(90).tolist()]
        # Reduce to 12 evenly-spaced points for the row spark
        if len(spark) > 12:
            step = len(spark) // 12
            spark12 = spark[::step][:12]
        else:
            spark12 = spark

        # AUM — yfinance reports it under several keys depending on fund type
        aum_raw = info.get("totalAssets") or info.get("netAssets")
        aum_str = format_aum(aum_raw)
        aum_n = (aum_raw / 1e9) if aum_raw else 0

        return {
            "ticker": ticker,
            "price": round(current, 2),
            "prev_close": round(prev, 2),
            "dod_change": round(dod_change, 2),
            "dod_pct": round(dod_pct, 2),
            "year_return_pct": round(yr_return_pct, 1),
            "aum": aum_str,
            "aum_billions": round(aum_n, 2),
            "spark_12d": spark12,
            "spark_90d": spark,
        }
    except Exception as e:
        print(f"  ! Error fetching {ticker}: {e}")
        return None


def format_aum(value: Optional[float]) -> str:
    """Format AUM in $X.XB or $XXXM."""
    if not value:
        return "n/a"
    if value >= 1e9:
        return f"${value / 1e9:.1f}B"
    if value >= 1e6:
        return f"${value / 1e6:.0f}M"
    return f"${value:.0f}"


def fetch_all_etfs() -> List[Dict]:
    """Pull data for every tracked AI ETF."""
    print(f"Fetching ETF data for {len(config.TRACKED_ETFS)} ETFs...")
    results = []
    for etf_cfg in config.TRACKED_ETFS:
        data = fetch_etf_data(etf_cfg["ticker"])
        if data:
            results.append({**etf_cfg, **data})
            print(f"  {etf_cfg['ticker']}: ${data['price']:.2f} ({data['dod_pct']:+.2f}%)")
        else:
            results.append(etf_cfg)  # Fall back to config-only data
            print(f"  {etf_cfg['ticker']}: data unavailable, using config only")
    print()
    return results


def fetch_public_ai_market_caps() -> List[Dict]:
    """Pull market cap and DoD change for tracked public AI companies."""
    print(f"Fetching market caps for {len(config.TRACKED_PUBLIC_AI)} public AI companies...")
    results = []
    for company in config.TRACKED_PUBLIC_AI:
        try:
            t = yf.Ticker(company["ticker"])
            info = t.info
            hist = t.history(period="5d")
            if hist.empty:
                continue
            current = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current
            dod_pct = ((current - prev) / prev * 100) if prev else 0
            mcap = info.get("marketCap", 0)
            mcap_b = round(mcap / 1e9, 1) if mcap else 0

            results.append({
                "ticker": company["ticker"],
                "name": company["name"],
                "market_cap_billions": mcap_b,
                "dod_pct": round(dod_pct, 2),
                "price": round(current, 2),
            })
            print(f"  {company['ticker']}: ${mcap_b}B ({dod_pct:+.2f}%)")
        except Exception as e:
            print(f"  ! {company['ticker']}: {e}")

    # Sort descending by market cap
    results.sort(key=lambda r: r["market_cap_billions"], reverse=True)
    print()
    return results
