#!/usr/bin/env python3
"""
Build stock2concept and stock_index matrices for US stocks (HIST model).

Workflow:
1. Read sp500.txt from Qlib US data to get instrument list
2. Fetch GICS sector data via yfinance (with disk cache)
3. Generate stock_index_sp500.npy  (dict: symbol -> int index)
4. Generate stock2concept_sp500.npy (matrix: num_stocks x num_sectors, one-hot)

GICS Sectors (11):
  Communication Services, Consumer Discretionary, Consumer Staples,
  Energy, Financials, Healthcare, Industrials, Technology,
  Basic Materials, Real Estate, Utilities

Usage:
  python scripts/build_us_concept_data.py [--market sp500] [--output data/hist]
"""
import os
import sys
import json
import argparse
import numpy as np
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
QLIB_US_DATA = os.path.expanduser("~/.qlib/qlib_data/us_data")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "hist"

# 11 GICS sectors (canonical names used by yfinance)
GICS_SECTORS = [
    "Communication Services",
    "Consumer Cyclical",       # yfinance name for Consumer Discretionary
    "Consumer Defensive",      # yfinance name for Consumer Staples
    "Energy",
    "Financial Services",      # yfinance name for Financials
    "Healthcare",
    "Industrials",
    "Technology",
    "Basic Materials",
    "Real Estate",
    "Utilities",
]

# Fallback sector mapping for well-known stocks (avoids network dependency)
# Covers ~180 large-cap stocks to reduce yfinance calls
KNOWN_SECTORS = {
    "AAPL": "Technology", "MSFT": "Technology", "GOOGL": "Communication Services",
    "GOOG": "Communication Services", "AMZN": "Consumer Cyclical", "FB": "Communication Services",
    "TSLA": "Consumer Cyclical", "NVDA": "Technology", "JPM": "Financial Services",
    "JNJ": "Healthcare", "V": "Technology", "UNH": "Healthcare",
    "HD": "Consumer Cyclical", "PG": "Consumer Defensive", "MA": "Technology",
    "DIS": "Communication Services", "BAC": "Financial Services", "PYPL": "Technology",
    "ADBE": "Technology", "CMCSA": "Communication Services", "NFLX": "Communication Services",
    "XOM": "Energy", "VZ": "Communication Services", "INTC": "Technology",
    "T": "Communication Services", "PFE": "Healthcare", "KO": "Consumer Defensive",
    "MRK": "Healthcare", "PEP": "Consumer Defensive", "ABT": "Healthcare",
    "CRM": "Technology", "CSCO": "Technology", "TMO": "Healthcare",
    "AVGO": "Technology", "ABBV": "Healthcare", "ACN": "Technology",
    "MCD": "Consumer Cyclical", "COST": "Consumer Defensive", "NKE": "Consumer Cyclical",
    "DHR": "Healthcare", "MDT": "Healthcare", "LLY": "Healthcare",
    "NEE": "Utilities", "BMY": "Healthcare", "UNP": "Industrials",
    "LIN": "Basic Materials", "AMGN": "Healthcare", "PM": "Consumer Defensive",
    "TXN": "Technology", "QCOM": "Technology", "HON": "Industrials",
    "UPS": "Industrials", "IBM": "Technology", "CVX": "Energy",
    "LOW": "Consumer Cyclical", "SBUX": "Consumer Cyclical", "BA": "Industrials",
    "GS": "Financial Services", "BLK": "Financial Services", "MMM": "Industrials",
    "GILD": "Healthcare", "CAT": "Industrials", "AXP": "Financial Services",
    "ISRG": "Healthcare", "DE": "Industrials", "AMD": "Technology",
    "BKNG": "Consumer Cyclical", "GE": "Industrials", "MDLZ": "Consumer Defensive",
    "TGT": "Consumer Cyclical", "LRCX": "Technology", "SYK": "Healthcare",
    "SPGI": "Financial Services", "ADP": "Technology", "CI": "Healthcare",
    "ANTM": "Healthcare", "ZTS": "Healthcare", "MO": "Consumer Defensive",
    "CB": "Financial Services", "SCHW": "Financial Services", "MS": "Financial Services",
    "PLD": "Real Estate", "CME": "Financial Services", "DUK": "Utilities",
    "SO": "Utilities", "CL": "Consumer Defensive", "BDX": "Healthcare",
    "D": "Utilities", "ICE": "Financial Services", "REGN": "Healthcare",
    "ATVI": "Communication Services", "NSC": "Industrials", "CSX": "Industrials",
    "PNC": "Financial Services", "USB": "Financial Services", "WM": "Industrials",
    "EQIX": "Real Estate", "APD": "Basic Materials", "SHW": "Basic Materials",
    "ECL": "Basic Materials", "EMR": "Industrials", "FIS": "Technology",
    "ITW": "Industrials", "FISV": "Technology", "GD": "Industrials",
    "ETN": "Industrials", "AON": "Financial Services", "CCI": "Real Estate",
    "TFC": "Financial Services", "MCO": "Financial Services", "TRV": "Financial Services",
    "MET": "Financial Services", "AIG": "Financial Services", "AFL": "Financial Services",
    "SRE": "Utilities", "EXC": "Utilities", "AEP": "Utilities",
    "WEC": "Utilities", "XEL": "Utilities", "ED": "Utilities",
    "ES": "Utilities", "DTE": "Utilities", "PPL": "Utilities",
    "WBA": "Healthcare", "CVS": "Healthcare", "HUM": "Healthcare",
    "BIIB": "Healthcare", "VRTX": "Healthcare", "ILMN": "Healthcare",
    "DXCM": "Healthcare", "EW": "Healthcare", "A": "Healthcare",
    "IQV": "Healthcare", "IDXX": "Healthcare", "MTD": "Healthcare",
    "WAT": "Healthcare", "HOLX": "Healthcare", "COP": "Energy",
    "EOG": "Energy", "SLB": "Energy", "PSX": "Energy",
    "VLO": "Energy", "MPC": "Energy", "OXY": "Energy",
    "HAL": "Energy", "DVN": "Energy", "HES": "Energy",
    "APA": "Energy", "FANG": "Energy", "MRO": "Energy",
    "SPG": "Real Estate", "AMT": "Real Estate", "O": "Real Estate",
    "DLR": "Real Estate", "PSA": "Real Estate", "WELL": "Real Estate",
    "AVB": "Real Estate", "EQR": "Real Estate", "ARE": "Real Estate",
    "MAA": "Real Estate", "UDR": "Real Estate", "ESS": "Real Estate",
    "SBAC": "Real Estate", "WY": "Real Estate",
    "F": "Consumer Cyclical", "GM": "Consumer Cyclical", "EBAY": "Consumer Cyclical",
    "ROST": "Consumer Cyclical", "TJX": "Consumer Cyclical", "ORLY": "Consumer Cyclical",
    "AZO": "Consumer Cyclical", "DG": "Consumer Cyclical", "DLTR": "Consumer Cyclical",
    "YUM": "Consumer Cyclical", "CMG": "Consumer Cyclical", "MAR": "Consumer Cyclical",
    "HLT": "Consumer Cyclical", "LVS": "Consumer Cyclical", "WYNN": "Consumer Cyclical",
    "MGM": "Consumer Cyclical", "RCL": "Consumer Cyclical", "CCL": "Consumer Cyclical",
    "LEN": "Consumer Cyclical", "DHI": "Consumer Cyclical", "PHM": "Consumer Cyclical",
    "NVR": "Consumer Cyclical",
    "WMT": "Consumer Defensive", "MNST": "Consumer Defensive", "STZ": "Consumer Defensive",
    "KMB": "Consumer Defensive", "GIS": "Consumer Defensive", "K": "Consumer Defensive",
    "SJM": "Consumer Defensive", "HSY": "Consumer Defensive", "HRL": "Consumer Defensive",
    "CLX": "Consumer Defensive", "CHD": "Consumer Defensive", "MKC": "Consumer Defensive",
    "KR": "Consumer Defensive", "SYY": "Consumer Defensive", "ADM": "Consumer Defensive",
    "DOW": "Basic Materials", "NEM": "Basic Materials", "FCX": "Basic Materials",
    "NUE": "Basic Materials", "VMC": "Basic Materials", "MLM": "Basic Materials",
    "FMC": "Basic Materials", "CF": "Basic Materials", "ALB": "Basic Materials",
    "IP": "Basic Materials", "PKG": "Basic Materials", "IFF": "Basic Materials",
    "RTX": "Industrials", "LMT": "Industrials", "NOC": "Industrials",
    "GD": "Industrials", "TDG": "Industrials", "HII": "Industrials",
    "FDX": "Industrials", "DAL": "Industrials", "UAL": "Industrials",
    "AAL": "Industrials", "LUV": "Industrials", "ALK": "Industrials",
    "ROK": "Industrials", "SWK": "Industrials", "PH": "Industrials",
    "IR": "Industrials", "CMI": "Industrials", "PCAR": "Industrials",
    "FAST": "Industrials", "J": "Industrials", "VRSK": "Industrials",
    "LNT": "Utilities", "AES": "Utilities", "AEE": "Utilities",
    "AWK": "Utilities", "EVRG": "Utilities", "PNW": "Utilities",
    "CMS": "Utilities", "CNP": "Utilities", "FE": "Utilities",
    "NI": "Utilities", "ATMOS": "Utilities",
}


def read_instruments(market: str = "sp500") -> list[str]:
    """Read stock symbols from Qlib instruments file."""
    path = os.path.join(QLIB_US_DATA, "instruments", f"{market}.txt")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Instruments file not found: {path}")
    symbols = []
    with open(path) as f:
        for line in f:
            parts = line.strip().split("\t")
            if parts:
                symbols.append(parts[0])
    return sorted(set(symbols))


def fetch_sectors_yfinance(symbols: list[str], cache_path: str) -> dict[str, str]:
    """Fetch sector data via yfinance with disk cache."""
    # Load cache
    cache = {}
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            cache = json.load(f)
        print(f"  Loaded {len(cache)} cached sectors from {cache_path}")

    # Apply known sectors first
    for sym in symbols:
        if sym not in cache and sym in KNOWN_SECTORS:
            cache[sym] = KNOWN_SECTORS[sym]

    # Find missing
    missing = [s for s in symbols if s not in cache]
    if not missing:
        print(f"  All {len(symbols)} sectors resolved (cache + known)")
        return cache

    print(f"  Fetching {len(missing)} sectors via yfinance...")
    try:
        import yfinance as yf
        batch_size = 50
        for i in range(0, len(missing), batch_size):
            batch = missing[i : i + batch_size]
            for sym in batch:
                try:
                    info = yf.Ticker(sym).info
                    sector = info.get("sector", "")
                    if sector:
                        cache[sym] = sector
                except Exception:
                    pass
            # Save cache periodically
            with open(cache_path, "w") as f:
                json.dump(cache, f, indent=2)
            done = min(i + batch_size, len(missing))
            print(f"    Progress: {done}/{len(missing)}")
    except ImportError:
        print("  yfinance not installed, using known sectors + default")
    except Exception as e:
        print(f"  yfinance error: {e}, using partial results")

    # Save final cache
    with open(cache_path, "w") as f:
        json.dump(cache, f, indent=2)

    return cache


def normalize_sector(sector: str) -> str:
    """Normalize sector names from various sources to canonical GICS names."""
    mapping = {
        "Consumer Discretionary": "Consumer Cyclical",
        "Consumer Staples": "Consumer Defensive",
        "Financials": "Financial Services",
        "Health Care": "Healthcare",
        "Information Technology": "Technology",
        "Materials": "Basic Materials",
    }
    return mapping.get(sector, sector)


def build_concept_data(
    symbols: list[str],
    sector_map: dict[str, str],
    default_sector: str = "",
) -> tuple[np.ndarray, dict]:
    """Build stock2concept matrix and stock_index dict.

    Returns:
        stock2concept: np.ndarray of shape (num_stocks, num_sectors), one-hot
        stock_index: dict mapping symbol -> int index
    """
    num_stocks = len(symbols)
    num_sectors = len(GICS_SECTORS)
    sector_to_idx = {s: i for i, s in enumerate(GICS_SECTORS)}

    stock_index = {}
    stock2concept = np.zeros((num_stocks, num_sectors), dtype=np.float32)

    unknown_count = 0
    for idx, sym in enumerate(symbols):
        stock_index[sym] = idx
        raw_sector = sector_map.get(sym, default_sector)
        sector = normalize_sector(raw_sector)
        if sector in sector_to_idx:
            stock2concept[idx, sector_to_idx[sector]] = 1.0
        else:
            # Assign uniform distribution for unknown sectors
            stock2concept[idx, :] = 1.0 / num_sectors
            unknown_count += 1

    return stock2concept, stock_index, unknown_count


def main():
    parser = argparse.ArgumentParser(description="Build US stock concept data for HIST")
    parser.add_argument("--market", type=str, default="sp500", help="Stock pool: sp500, nasdaq100, all")
    parser.add_argument("--output", type=str, default=None, help="Output directory")
    parser.add_argument("--skip-yfinance", action="store_true", help="Skip yfinance, use only known sectors")
    args = parser.parse_args()

    output_dir = Path(args.output) if args.output else DEFAULT_OUTPUT
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  Build US Stock Concept Data for HIST")
    print(f"  Market: {args.market}")
    print(f"  Output: {output_dir}")
    print(f"{'='*60}\n")

    # Step 1: Read instruments
    print("[1/4] Reading instruments...")
    symbols = read_instruments(args.market)
    print(f"  Found {len(symbols)} stocks in {args.market}")

    # Step 2: Get sector data
    print("\n[2/4] Getting sector data...")
    cache_path = str(output_dir / f"sector_cache_{args.market}.json")
    if args.skip_yfinance:
        sector_map = {s: KNOWN_SECTORS.get(s, "") for s in symbols}
        print(f"  Using known sectors only: {sum(1 for v in sector_map.values() if v)}/{len(symbols)} resolved")
    else:
        sector_map = fetch_sectors_yfinance(symbols, cache_path)

    # Step 3: Build matrices
    print("\n[3/4] Building concept matrices...")
    stock2concept, stock_index, unknown_count = build_concept_data(symbols, sector_map)

    # Sector distribution
    sector_counts = {}
    for sym in symbols:
        raw = sector_map.get(sym, "Unknown")
        sector = normalize_sector(raw) if raw else "Unknown"
        sector_counts[sector] = sector_counts.get(sector, 0) + 1

    print(f"  stock2concept shape: {stock2concept.shape}")
    print(f"  stock_index entries: {len(stock_index)}")
    print(f"  Unknown sectors: {unknown_count}/{len(symbols)}")
    print(f"\n  Sector distribution:")
    for sector, count in sorted(sector_counts.items(), key=lambda x: -x[1]):
        pct = count * 100 / len(symbols)
        print(f"    {sector:<30s} {count:>4d} ({pct:.1f}%)")

    # Step 4: Save
    print(f"\n[4/4] Saving...")
    s2c_path = output_dir / f"stock2concept_{args.market}.npy"
    si_path = output_dir / f"stock_index_{args.market}.npy"

    np.save(str(s2c_path), stock2concept)
    np.save(str(si_path), stock_index)

    # Also save metadata
    meta = {
        "market": args.market,
        "num_stocks": len(symbols),
        "num_sectors": len(GICS_SECTORS),
        "sectors": GICS_SECTORS,
        "unknown_count": unknown_count,
        "sector_distribution": sector_counts,
        "symbols": symbols,
    }
    meta_path = output_dir / f"concept_meta_{args.market}.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"  stock2concept: {s2c_path}")
    print(f"  stock_index:   {si_path}")
    print(f"  metadata:      {meta_path}")
    print(f"\n{'='*60}")
    print(f"  Done! {len(symbols)} stocks, {len(GICS_SECTORS)} sectors")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
