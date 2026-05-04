#!/usr/bin/env python3
"""
Rolling Training for US Stocks (LightGBM / DoubleEnsemble)
============================================================
Monthly rolling retraining using Qlib's RollingGen.

Rolling modes:
  expanding (ROLL_EX): Train start fixed, window grows each step
  sliding  (ROLL_SD): Fixed-size sliding window

Usage:
  # Default: expanding window, step=20 (~1 month), LightGBM
  python scripts/rolling_train_us.py

  # Sliding window with DoubleEnsemble
  python scripts/rolling_train_us.py --rtype sliding --model densemble

  # Custom step size
  python scripts/rolling_train_us.py --step 60 --output results/rolling_quarterly/
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import qlib
from qlib.constant import REG_US
from qlib.data.dataset.handler import DataHandlerLP
from qlib.model.trainer import task_train
from qlib.workflow import R
from qlib.workflow.task.gen import RollingGen

from research.workflow.experiment_manager import ExperimentManager, save_results_json

# ============================================================
# Constants
# ============================================================
QLIB_US_DATA = "~/.qlib/qlib_data/us_data"

TRAIN_START = "2008-01-01"
TRAIN_END = "2014-12-31"
VALID_START = "2015-01-01"
VALID_END = "2016-12-31"
TEST_START = "2017-01-01"
TEST_END = "2020-08-01"
FIT_START = "2008-01-01"
FIT_END = "2014-12-31"

DEFAULT_LGB_PARAMS = {
    "loss": "mse",
    "colsample_bytree": 0.8879,
    "learning_rate": 0.0421,
    "subsample": 0.8789,
    "lambda_l1": 205.6999,
    "lambda_l2": 580.9768,
    "max_depth": 8,
    "num_leaves": 250,
    "num_threads": 8,
}


def build_base_task(
    model_type: str,
    instruments: str,
    train_start: str,
    train_end: str,
    valid_start: str,
    valid_end: str,
    test_start: str,
    test_end: str,
    fit_start: str,
    fit_end: str,
) -> dict:
    """Build the base task dict for RollingGen."""
    if model_type == "lgbm":
        model_config = {
            "class": "LGBModel",
            "module_path": "qlib.contrib.model.gbdt",
            "kwargs": DEFAULT_LGB_PARAMS,
        }
    elif model_type == "densemble":
        model_config = {
            "class": "DEnsembleModel",
            "module_path": "qlib.contrib.model.double_ensemble",
            "kwargs": {
                "base_model": "gbm",
                "loss": "mse",
                "num_models": 6,
                "enable_sr": True,
                "enable_fs": True,
                "epochs": 100,
            },
        }
    else:
        raise ValueError(f"Unknown model type: {model_type}")

    task = {
        "model": model_config,
        "dataset": {
            "class": "DatasetH",
            "module_path": "qlib.data.dataset",
            "kwargs": {
                "handler": {
                    "class": "Alpha158",
                    "module_path": "qlib.contrib.data.handler",
                    "kwargs": {
                        "instruments": instruments,
                        "start_time": train_start,
                        "end_time": test_end,
                        "fit_start_time": fit_start,
                        "fit_end_time": fit_end,
                        "infer_processors": [
                            {"class": "ProcessInf", "kwargs": {}},
                            {"class": "ZScoreNorm", "kwargs": {}},
                            {"class": "Fillna", "kwargs": {}},
                        ],
                        "learn_processors": [
                            {"class": "DropnaLabel"},
                            {"class": "CSZScoreNorm", "kwargs": {"fields_group": "label"}},
                        ],
                    },
                },
                "segments": {
                    "train": (train_start, train_end),
                    "valid": (valid_start, valid_end),
                    "test": (test_start, test_end),
                },
            },
        },
        "record": [
            {"class": "SignalRecord", "module_path": "qlib.workflow.record_temp"},
            {
                "class": "SigAnaRecord",
                "module_path": "qlib.workflow.record_temp",
                "kwargs": {"ana_long_short": True, "ann_scaler": 252},
            },
        ],
    }
    return task


def collect_rolling_predictions(exp_name: str) -> pd.Series:
    """Collect and merge predictions from all rolling recorders."""
    exp = R.get_exp(experiment_name=exp_name)
    recorders = exp.list_recorders()

    all_preds = []
    for rid, recorder in recorders.items():
        try:
            pred = recorder.load_object("pred.pkl")
            if isinstance(pred, pd.DataFrame):
                pred = pred.iloc[:, 0] if "score" not in pred.columns else pred["score"]
            all_preds.append(pred)
        except Exception:
            continue

    if not all_preds:
        return pd.Series(dtype=float)

    # Merge: later windows override earlier for overlapping dates
    merged = pd.concat(all_preds)
    # Remove duplicates, keep last (most recent rolling window)
    merged = merged[~merged.index.duplicated(keep="last")]
    return merged.sort_index()


def evaluate_ic_by_window(preds: pd.Series, dataset_labels: pd.Series) -> pd.DataFrame:
    """Compute daily IC and group by rolling window month."""
    common_idx = preds.index.intersection(dataset_labels.index)
    pred = preds.loc[common_idx]
    label = dataset_labels.loc[common_idx]

    dates = common_idx.get_level_values("datetime").unique()
    rows = []
    for dt in dates:
        mask = common_idx.get_level_values("datetime") == dt
        p, l = pred[mask], label[mask]
        if len(p) < 10:
            continue
        ic = p.corr(l)
        ric = p.rank().corr(l.rank())
        if np.isfinite(ic):
            rows.append({"date": dt, "IC": ic, "RankIC": ric})

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df


def main():
    parser = argparse.ArgumentParser(description="Rolling Training for US Stocks")
    parser.add_argument("--step", type=int, default=20, help="Rolling step in trading days (~1 month=20)")
    parser.add_argument("--rtype", type=str, default="expanding", choices=["expanding", "sliding"])
    parser.add_argument("--model", type=str, default="lgbm", choices=["lgbm", "densemble"])
    parser.add_argument("--instruments", type=str, default="sp500")
    parser.add_argument("--train-start", type=str, default=TRAIN_START)
    parser.add_argument("--train-end", type=str, default=TRAIN_END)
    parser.add_argument("--valid-start", type=str, default=VALID_START)
    parser.add_argument("--valid-end", type=str, default=VALID_END)
    parser.add_argument("--test-start", type=str, default=TEST_START)
    parser.add_argument("--test-end", type=str, default=TEST_END)
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--no-mlflow", action="store_true")

    args = parser.parse_args()

    output_dir = Path(args.output) if args.output else PROJECT_ROOT / "results" / f"rolling_{args.model}_us"
    output_dir.mkdir(parents=True, exist_ok=True)

    exp_name = f"rolling_{args.model}_{args.rtype}_{args.instruments}"

    windows = {
        "train_start": args.train_start,
        "train_end": args.train_end,
        "valid_start": args.valid_start,
        "valid_end": args.valid_end,
        "test_start": args.test_start,
        "test_end": args.test_end,
    }

    print(f"\n{'='*70}")
    print(f"  Rolling Training - {args.model.upper()}")
    print(f"  Type: {args.rtype} | Step: {args.step} trading days")
    print(f"  Instruments: {args.instruments}")
    print(f"  Train: {windows['train_start']} ~ {windows['train_end']}")
    print(f"  Valid: {windows['valid_start']} ~ {windows['valid_end']}")
    print(f"  Test:  {windows['test_start']} ~ {windows['test_end']}")
    print(f"  Output: {output_dir}")
    print(f"{'='*70}\n")

    # Step 1: Init Qlib
    print("[1/4] Initializing Qlib (US)...")
    qlib.init(provider_uri=QLIB_US_DATA, region=REG_US)

    # Step 2: Build base task and generate rolling tasks
    print("\n[2/4] Generating rolling tasks...")
    base_task = build_base_task(
        model_type=args.model,
        instruments=args.instruments,
        train_start=windows["train_start"],
        train_end=windows["train_end"],
        valid_start=windows["valid_start"],
        valid_end=windows["valid_end"],
        test_start=windows["test_start"],
        test_end=windows["test_end"],
        fit_start=FIT_START,
        fit_end=FIT_END,
    )

    rg = RollingGen(step=args.step, rtype=args.rtype)
    rolling_tasks = rg.generate(base_task)
    print(f"  Generated {len(rolling_tasks)} rolling windows")

    if not rolling_tasks:
        print("  ERROR: No rolling tasks generated. Check time windows.")
        sys.exit(1)

    # Step 3: Train each rolling window
    print(f"\n[3/4] Training {len(rolling_tasks)} rolling windows...")
    t0 = time.time()

    for i, task in enumerate(rolling_tasks):
        # Extract segments for display
        segs = task["dataset"]["kwargs"]["segments"]
        train_seg = segs.get("train", ("?", "?"))
        test_seg = segs.get("test", ("?", "?"))
        print(f"\n  --- Window {i+1}/{len(rolling_tasks)} ---")
        print(f"  Train: {train_seg[0]} ~ {train_seg[1]}")
        print(f"  Test:  {test_seg[0]} ~ {test_seg[1]}")

        t_win = time.time()
        recorder = task_train(task, experiment_name=exp_name)
        print(f"  Completed in {time.time()-t_win:.1f}s (recorder: {recorder.info['id'][:8]})")

    total_time = time.time() - t0
    print(f"\n  Total rolling training time: {total_time:.1f}s")

    # Step 4: Collect and evaluate merged predictions
    print(f"\n[4/4] Collecting and evaluating predictions...")
    merged_pred = collect_rolling_predictions(exp_name)
    print(f"  Merged predictions: {len(merged_pred)} samples")

    if len(merged_pred) == 0:
        print("  WARNING: No predictions collected. Check recorder outputs.")
        sys.exit(1)

    merged_pred.to_pickle(str(output_dir / "rolling_pred.pkl"))

    # IC timeline
    # We need labels from the dataset for IC calculation
    from qlib.contrib.data.handler import Alpha158
    from qlib.data.dataset import DatasetH

    handler = Alpha158(
        instruments=args.instruments,
        start_time=windows["train_start"],
        end_time=windows["test_end"],
        fit_start_time=FIT_START,
        fit_end_time=FIT_END,
    )
    eval_dataset = DatasetH(
        handler=handler,
        segments={"test": (windows["test_start"], windows["test_end"])},
    )
    df_test = eval_dataset.prepare("test", col_set=["feature", "label"], data_key=DataHandlerLP.DK_L)
    labels = df_test["label"].iloc[:, 0]

    ic_timeline = evaluate_ic_by_window(merged_pred, labels)
    if not ic_timeline.empty:
        ic_timeline.to_csv(output_dir / "rolling_ic_timeline.csv", index=False)

    # Compute overall metrics
    common_idx = merged_pred.index.intersection(labels.index)
    pred_aligned = merged_pred.loc[common_idx]
    label_aligned = labels.loc[common_idx]

    dates = common_idx.get_level_values("datetime").unique()
    daily_ic, daily_rank_ic = [], []
    for dt in dates:
        mask = common_idx.get_level_values("datetime") == dt
        p, l = pred_aligned[mask], label_aligned[mask]
        if len(p) < 10:
            continue
        ic = p.corr(l)
        ric = p.rank().corr(l.rank())
        if np.isfinite(ic):
            daily_ic.append(ic)
        if np.isfinite(ric):
            daily_rank_ic.append(ric)

    daily_ic = np.array(daily_ic)
    daily_rank_ic = np.array(daily_rank_ic)

    results = {
        "model": args.model,
        "rtype": args.rtype,
        "step": args.step,
        "n_windows": len(rolling_tasks),
        "n_predictions": len(merged_pred),
        "total_time_s": round(total_time, 1),
        "IC_mean": float(daily_ic.mean()) if len(daily_ic) > 0 else 0,
        "IC_std": float(daily_ic.std()) if len(daily_ic) > 0 else 0,
        "ICIR": float(daily_ic.mean() / (daily_ic.std() + 1e-12)) if len(daily_ic) > 0 else 0,
        "RankIC_mean": float(daily_rank_ic.mean()) if len(daily_rank_ic) > 0 else 0,
        "RankICIR": float(
            daily_rank_ic.mean() / (daily_rank_ic.std() + 1e-12)
        ) if len(daily_rank_ic) > 0 else 0,
        "num_ic_days": len(daily_ic),
        "time_windows": windows,
    }

    save_results_json(results, output_dir / "rolling_eval_results.json")

    # MLflow logging
    if not args.no_mlflow:
        em = ExperimentManager()
        em.log_run(
            experiment_name=exp_name,
            params={
                "model": args.model,
                "rtype": args.rtype,
                "step": args.step,
                "instruments": args.instruments,
                "n_windows": len(rolling_tasks),
                **windows,
            },
            metrics={
                "IC_mean": results["IC_mean"],
                "ICIR": results["ICIR"],
                "RankIC_mean": results["RankIC_mean"],
                "RankICIR": results["RankICIR"],
            },
            artifacts=[
                str(output_dir / "rolling_eval_results.json"),
                str(output_dir / "rolling_ic_timeline.csv"),
            ],
            tags={"phase": "4", "pipeline": "rolling"},
        )

    # Print summary
    print(f"\n{'='*70}")
    print(f"  Rolling Training Results")
    print(f"{'='*70}")
    print(f"  Model:       {args.model.upper()} ({args.rtype})")
    print(f"  Windows:     {len(rolling_tasks)} (step={args.step})")
    print(f"  ---")
    print(f"  IC:          {results['IC_mean']:.6f} (std={results['IC_std']:.4f})")
    print(f"  ICIR:        {results['ICIR']:.4f}")
    print(f"  Rank IC:     {results['RankIC_mean']:.6f}")
    print(f"  Rank ICIR:   {results['RankICIR']:.4f}")
    print(f"  ---")
    print(f"  IC Days:     {results['num_ic_days']}")
    print(f"  Total Time:  {total_time:.1f}s")
    if not ic_timeline.empty:
        # Monthly IC summary
        ic_timeline["month"] = ic_timeline["date"].dt.to_period("M")
        monthly = ic_timeline.groupby("month")["IC"].mean()
        print(f"  ---")
        print(f"  Monthly IC:")
        for month, ic in monthly.items():
            print(f"    {month}: {ic:.4f}")
    print(f"\n  Output: {output_dir}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
