#!/usr/bin/env python3
"""
Standalone Backtest Engine for US Stocks
=========================================
Runs portfolio backtest from any prediction file (pred.pkl).

Usage:
  # Backtest LightGBM predictions
  python scripts/backtest_us.py --pred-path results/lgbm_us/pred.pkl

  # Custom strategy params
  python scripts/backtest_us.py --pred-path results/lgbm_us/pred.pkl --topk 50 --n-drop 5

  # Custom time range
  python scripts/backtest_us.py --pred-path results/lgbm_us/pred.pkl \
      --start-time 2025-01-01 --end-time 2026-05-02
"""

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import qlib
from qlib.constant import REG_US
from qlib.backtest import backtest as qlib_backtest
from qlib.contrib.evaluate import risk_analysis
from qlib.contrib.strategy import TopkDropoutStrategy

from research.workflow.experiment_manager import save_results_json

# ============================================================
# Constants
# ============================================================
QLIB_US_DATA = "~/.qlib/qlib_data/us_data"
DEFAULT_START = "2017-01-01"
DEFAULT_END = "2020-08-01"


def load_predictions(pred_path: str) -> pd.Series:
    """Load predictions from pickle file."""
    pred = pd.read_pickle(pred_path)
    if isinstance(pred, pd.DataFrame):
        if "score" in pred.columns:
            return pred["score"]
        return pred.iloc[:, 0]
    return pred


def run_backtest(
    pred: pd.Series,
    start_time: str,
    end_time: str,
    topk: int = 30,
    n_drop: int = 3,
    account: float = 1e8,
    benchmark: str = "SPY",
    cost: float = 0.0005,
) -> dict:
    """Run backtest and return portfolio metrics."""
    strategy_config = {
        "class": "TopkDropoutStrategy",
        "module_path": "qlib.contrib.strategy",
        "kwargs": {
            "signal": pred,
            "topk": topk,
            "n_drop": n_drop,
        },
    }

    exchange_kwargs = {
        "limit_threshold": None,
        "deal_price": "close",
        "open_cost": cost,
        "close_cost": cost,
        "min_cost": 1.0,
        "trade_unit": 1,
    }

    port_metric, indicator = qlib_backtest(
        start_time=start_time,
        end_time=end_time,
        strategy=strategy_config,
        executor=None,
        benchmark=benchmark,
        account=account,
        exchange_kwargs=exchange_kwargs,
    )

    return port_metric, indicator


def format_risk_report(analysis: dict) -> dict:
    """Convert risk_analysis output to a flat JSON-serializable dict."""
    report = {}
    for freq, df in analysis.items():
        if isinstance(df, pd.DataFrame):
            for col in df.columns:
                for idx in df.index:
                    key = f"{freq}_{col}_{idx}"
                    val = df.loc[idx, col]
                    if pd.notna(val):
                        report[key] = float(val)
        elif isinstance(df, pd.Series):
            for idx in df.index:
                key = f"{freq}_{idx}"
                val = df[idx]
                if pd.notna(val):
                    report[key] = float(val)
    return report


def main():
    parser = argparse.ArgumentParser(description="US Stock Backtest Engine")
    parser.add_argument("--pred-path", type=str, required=True, help="Path to pred.pkl")
    parser.add_argument("--topk", type=int, default=30, help="Top-K stocks to hold")
    parser.add_argument("--n-drop", type=int, default=3, help="Stocks to drop per rebalance")
    parser.add_argument("--account", type=float, default=1e8, help="Initial account value")
    parser.add_argument("--benchmark", type=str, default="SPY")
    parser.add_argument("--cost", type=float, default=0.0005, help="One-side transaction cost")
    parser.add_argument("--start-time", type=str, default=None, help="Backtest start")
    parser.add_argument("--end-time", type=str, default=None, help="Backtest end")
    parser.add_argument("--output", type=str, default=None, help="Output directory")

    args = parser.parse_args()

    pred_path = Path(args.pred_path)
    if not pred_path.exists():
        print(f"ERROR: Prediction file not found: {pred_path}")
        sys.exit(1)

    output_dir = Path(args.output) if args.output else pred_path.parent / "backtest"
    output_dir.mkdir(parents=True, exist_ok=True)

    start_time = args.start_time or DEFAULT_START
    end_time = args.end_time or DEFAULT_END

    print(f"\n{'='*70}")
    print(f"  US Stock Backtest")
    print(f"  Predictions: {pred_path}")
    print(f"  Strategy:    TopkDropout(topk={args.topk}, n_drop={args.n_drop})")
    print(f"  Period:      {start_time} ~ {end_time}")
    print(f"  Account:     {args.account:,.0f} | Benchmark: {args.benchmark}")
    print(f"  Cost:        {args.cost*100:.2f}% (one-side)")
    print(f"  Output:      {output_dir}")
    print(f"{'='*70}\n")

    # Step 1: Init Qlib
    print("[1/3] Initializing Qlib (US)...")
    qlib.init(provider_uri=QLIB_US_DATA, region=REG_US)

    # Step 2: Load predictions
    print("[2/3] Loading predictions...")
    pred = load_predictions(str(pred_path))
    print(f"  Loaded {len(pred)} predictions")
    print(f"  Date range: {pred.index.get_level_values(0).min()} ~ {pred.index.get_level_values(0).max()}")

    # Step 3: Run backtest
    print("[3/3] Running backtest...")
    t0 = time.time()
    port_metric, indicator = run_backtest(
        pred=pred,
        start_time=start_time,
        end_time=end_time,
        topk=args.topk,
        n_drop=args.n_drop,
        account=args.account,
        benchmark=args.benchmark,
        cost=args.cost,
    )
    elapsed = time.time() - t0
    print(f"  Backtest completed in {elapsed:.1f}s")

    # Risk analysis
    analysis = {}
    for freq in ["day", "month"]:
        try:
            ra = risk_analysis(port_metric["return"], freq=freq)
            analysis[freq] = ra
        except Exception as e:
            print(f"  Warning: risk_analysis({freq}) failed: {e}")

    # Save outputs
    pd.to_pickle(port_metric, str(output_dir / "report_normal.pkl"))
    pd.to_pickle(indicator, str(output_dir / "indicator.pkl"))

    # Build results
    results = {
        "pred_path": str(pred_path),
        "topk": args.topk,
        "n_drop": args.n_drop,
        "start_time": start_time,
        "end_time": end_time,
        "account": args.account,
        "benchmark": args.benchmark,
        "cost": args.cost,
        "elapsed_s": round(elapsed, 1),
    }

    # Extract key metrics from risk analysis
    if "day" in analysis:
        risk_flat = format_risk_report({"day": analysis["day"]})
        results.update(risk_flat)

    save_results_json(results, output_dir / "backtest_report.json")

    # Print summary
    print(f"\n{'='*70}")
    print(f"  Backtest Results")
    print(f"{'='*70}")
    if "day" in analysis:
        ra = analysis["day"]
        if isinstance(ra, pd.DataFrame):
            print(ra.to_string())
        else:
            print(ra)
    print(f"\n  Output: {output_dir}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
