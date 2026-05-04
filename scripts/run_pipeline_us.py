#!/usr/bin/env python3
"""
End-to-End Alpha Pipeline for US Stocks
=========================================
Orchestration script chaining: train -> backtest -> signal generation.

Usage:
  # Full pipeline (train + backtest + signal)
  python scripts/run_pipeline_us.py --steps all

  # Train only
  python scripts/run_pipeline_us.py --steps train

  # Backtest + signal from existing predictions
  python scripts/run_pipeline_us.py --steps backtest,signal --pred-path results/lgbm_us/pred.pkl

  # Rolling pipeline
  python scripts/run_pipeline_us.py --steps all --rolling

  # Generate today's signal from existing model
  python scripts/run_pipeline_us.py --steps signal --pred-path results/lgbm_us/pred.pkl
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

PYTHON = str(PROJECT_ROOT / "venv" / "bin" / "python")
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


def run_step(cmd: list[str], step_name: str) -> int:
    """Run a subprocess step, print output, return exit code."""
    print(f"\n{'='*60}")
    print(f"  PIPELINE STEP: {step_name}")
    print(f"  CMD: {' '.join(cmd)}")
    print(f"{'='*60}\n")

    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        print(f"\n  ERROR: Step '{step_name}' failed (exit code {result.returncode})")
    return result.returncode


def generate_signal(
    pred_path: str,
    output_dir: Path,
    topk: int = 30,
    signal_date: str | None = None,
) -> dict | None:
    """Generate trading signal from predictions."""
    pred = pd.read_pickle(pred_path)
    if isinstance(pred, pd.DataFrame):
        pred = pred["score"] if "score" in pred.columns else pred.iloc[:, 0]

    # Get the latest date in predictions (or specified date)
    dates = pred.index.get_level_values("datetime").unique().sort_values()

    if signal_date:
        target_date = pd.Timestamp(signal_date)
        # Find nearest available date
        if target_date in dates:
            latest = target_date
        else:
            mask = dates <= target_date
            if mask.any():
                latest = dates[mask][-1]
            else:
                print(f"  WARNING: No predictions for date {signal_date}")
                return None
    else:
        latest = dates[-1]

    # Get predictions for the latest date
    mask = pred.index.get_level_values("datetime") == latest
    day_pred = pred[mask].sort_values(ascending=False)

    # Top-K signals
    top_signals = day_pred.head(topk)

    signal = {
        "date": str(latest.date()),
        "generated_at": datetime.now().isoformat(),
        "model": "pipeline",
        "topk": topk,
        "n_candidates": len(day_pred),
        "signals": [],
    }

    for rank, (idx, score) in enumerate(top_signals.items(), 1):
        symbol = idx[1] if isinstance(idx, tuple) else str(idx)
        signal["signals"].append({
            "symbol": symbol,
            "rank": rank,
            "score": round(float(score), 6),
        })

    # Save signal
    signal_dir = output_dir / "signals"
    signal_dir.mkdir(parents=True, exist_ok=True)
    date_str = str(latest.date()).replace("-", "")
    signal_path = signal_dir / f"signal_{date_str}.json"
    with open(signal_path, "w") as f:
        json.dump(signal, f, indent=2, ensure_ascii=False)

    print(f"\n  Signal for {latest.date()} ({len(top_signals)} stocks):")
    for s in signal["signals"][:10]:
        print(f"    #{s['rank']:2d} {s['symbol']:8s} score={s['score']:.6f}")
    if len(signal["signals"]) > 10:
        print(f"    ... and {len(signal['signals'])-10} more")
    print(f"\n  Saved: {signal_path}")

    return signal


def main():
    parser = argparse.ArgumentParser(description="End-to-End Alpha Pipeline")
    parser.add_argument(
        "--steps", type=str, default="all",
        help="Comma-separated steps: all, train, backtest, signal"
    )
    parser.add_argument("--mode", type=str, default="baseline", choices=["baseline", "enhanced"])
    parser.add_argument("--model", type=str, default="lgbm", choices=["lgbm", "densemble"])
    parser.add_argument("--rolling", action="store_true", help="Use rolling training instead of single")
    parser.add_argument("--rolling-step", type=int, default=20, help="Rolling step (trading days)")
    parser.add_argument("--instruments", type=str, default="sp500")
    parser.add_argument("--topk", type=int, default=30)
    parser.add_argument("--n-drop", type=int, default=3)
    parser.add_argument("--pred-path", type=str, default=None, help="Existing pred.pkl (skip train)")
    parser.add_argument("--signal-date", type=str, default=None, help="Generate signal for specific date")
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--no-mlflow", action="store_true")

    args = parser.parse_args()

    steps = set(args.steps.split(","))
    if "all" in steps:
        steps = {"train", "backtest", "signal"}

    model_tag = args.model
    if args.rolling:
        model_tag = f"rolling_{args.model}"
    output_dir = Path(args.output) if args.output else PROJECT_ROOT / "results" / "pipeline"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine pred path
    if args.pred_path:
        pred_path = Path(args.pred_path)
    elif args.rolling:
        pred_path = PROJECT_ROOT / "results" / f"rolling_{args.model}_us" / "rolling_pred.pkl"
    else:
        pred_path = PROJECT_ROOT / "results" / f"{args.model}_us" / "pred.pkl"

    print(f"\n{'='*70}")
    print(f"  US Alpha Pipeline")
    print(f"  Steps: {', '.join(sorted(steps))}")
    print(f"  Model: {args.model} | Mode: {args.mode} | Rolling: {args.rolling}")
    print(f"  Instruments: {args.instruments}")
    print(f"  TopK: {args.topk} | N_Drop: {args.n_drop}")
    print(f"  Output: {output_dir}")
    print(f"{'='*70}\n")

    t_start = time.time()
    failed = False

    # ============================
    # STEP 1: Train
    # ============================
    if "train" in steps:
        if args.rolling:
            cmd = [
                PYTHON, str(SCRIPTS_DIR / "rolling_train_us.py"),
                "--model", args.model,
                "--step", str(args.rolling_step),
                "--instruments", args.instruments,
            ]
            if args.no_mlflow:
                cmd.append("--no-mlflow")
            rc = run_step(cmd, "Rolling Training")
        else:
            cmd = [
                PYTHON, str(SCRIPTS_DIR / "train_lgbm_us.py"),
                "--mode", args.mode,
                "--model", args.model,
                "--instruments", args.instruments,
            ]
            if args.no_mlflow:
                cmd.append("--no-mlflow")
            rc = run_step(cmd, "Model Training")

        if rc != 0:
            print("\nPIPELINE ABORTED: Training failed.")
            sys.exit(1)

    # ============================
    # STEP 2: Backtest
    # ============================
    if "backtest" in steps:
        if not pred_path.exists():
            print(f"\n  ERROR: Predictions not found: {pred_path}")
            print(f"  Run with --steps train first, or specify --pred-path")
            sys.exit(1)

        cmd = [
            PYTHON, str(SCRIPTS_DIR / "backtest_us.py"),
            "--pred-path", str(pred_path),
            "--topk", str(args.topk),
            "--n-drop", str(args.n_drop),
            "--output", str(output_dir / "backtest"),
        ]
        rc = run_step(cmd, "Backtest")
        if rc != 0:
            print("\n  WARNING: Backtest failed, continuing...")
            failed = True

    # ============================
    # STEP 3: Signal Generation
    # ============================
    if "signal" in steps:
        if not pred_path.exists():
            print(f"\n  ERROR: Predictions not found: {pred_path}")
            print(f"  Run with --steps train first, or specify --pred-path")
            sys.exit(1)

        print(f"\n{'='*60}")
        print(f"  PIPELINE STEP: Signal Generation")
        print(f"{'='*60}")

        signal = generate_signal(
            pred_path=str(pred_path),
            output_dir=output_dir,
            topk=args.topk,
            signal_date=args.signal_date,
        )
        if signal is None:
            print("\n  WARNING: Signal generation failed.")
            failed = True

    total_time = time.time() - t_start

    # ============================
    # Summary
    # ============================
    print(f"\n{'='*70}")
    print(f"  Pipeline Complete {'(with warnings)' if failed else ''}")
    print(f"{'='*70}")
    print(f"  Steps:       {', '.join(sorted(steps))}")
    print(f"  Total Time:  {total_time:.1f}s")
    print(f"  Output:      {output_dir}")

    # List generated files
    for f in sorted(output_dir.rglob("*")):
        if f.is_file():
            size = f.stat().st_size
            if size > 1024 * 1024:
                size_str = f"{size/1024/1024:.1f}MB"
            elif size > 1024:
                size_str = f"{size/1024:.1f}KB"
            else:
                size_str = f"{size}B"
            print(f"    {f.relative_to(output_dir)}: {size_str}")

    print(f"{'='*70}\n")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
