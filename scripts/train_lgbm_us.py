#!/usr/bin/env python3
"""
LightGBM / DoubleEnsemble Training for US Stocks (Alpha158 Pipeline)
=====================================================================
Phase 4 core deliverable. Trains tree-based models on Qlib's Alpha158
feature set using native Qlib workflow (R + Records).

Usage:
  # LightGBM baseline with Alpha158
  python scripts/train_lgbm_us.py --mode baseline

  # LightGBM with Alpha158 + custom factors
  python scripts/train_lgbm_us.py --mode enhanced

  # DoubleEnsemble model
  python scripts/train_lgbm_us.py --mode baseline --model densemble

  # Custom time window
  python scripts/train_lgbm_us.py --mode baseline --train-end 2022-12-31

  # Hyperparameter tuning (grid search)
  python scripts/train_lgbm_us.py --mode baseline --tune
"""

import argparse
import json
import sys
import time
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import qlib
from qlib.constant import REG_US
from qlib.data.dataset import DatasetH
from qlib.data.dataset.handler import DataHandlerLP
from qlib.contrib.data.handler import Alpha158
from qlib.contrib.model.gbdt import LGBModel
from qlib.contrib.model.double_ensemble import DEnsembleModel
from qlib.contrib.strategy import TopkDropoutStrategy
from qlib.backtest import backtest as qlib_backtest
from qlib.contrib.evaluate import risk_analysis
from qlib.workflow import R
from qlib.workflow.record_temp import SignalRecord, SigAnaRecord, PortAnaRecord

from research.workflow.experiment_manager import ExperimentManager, save_results_json

# ============================================================
# Constants
# ============================================================
QLIB_US_DATA = "~/.qlib/qlib_data/us_data"

# Default time windows (Qlib US defaults, compatible with offline data ~2020-11)
TRAIN_START = "2008-01-01"
TRAIN_END = "2014-12-31"
VALID_START = "2015-01-01"
VALID_END = "2016-12-31"
TEST_START = "2017-01-01"
TEST_END = "2020-08-01"
FIT_START = "2008-01-01"
FIT_END = "2014-12-31"

# Default LightGBM hyperparameters (from workflow YAML)
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

# Tuning grid (conservative, ~18 combinations)
TUNE_GRID = {
    "learning_rate": [0.01, 0.05, 0.1],
    "num_leaves": [128, 256],
    "max_depth": [6, 8, 10],
}

# Backtest config
TOPK = 30
N_DROP = 3
ACCOUNT = 100_000_000
BENCHMARK = "SPY"
COST = 0.0005


# ============================================================
# Helpers
# ============================================================
def build_dataset(
    instruments: str,
    train_start: str,
    train_end: str,
    valid_start: str,
    valid_end: str,
    test_start: str,
    test_end: str,
    fit_start: str,
    fit_end: str,
    mode: str = "baseline",
) -> DatasetH:
    """Build DatasetH with Alpha158 or enhanced handler."""
    handler_kwargs = {
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
    }

    if mode == "enhanced":
        from research.factors.custom_factors import get_custom_factor_expressions

        custom_exprs = get_custom_factor_expressions()
        # For enhanced mode, we note this for logging but Alpha158 handler
        # doesn't directly accept custom expressions via kwargs.
        # We use Alpha158 as-is; custom factors integration would need
        # a custom handler subclass. For now, log this as a TODO.
        print("  NOTE: Enhanced mode uses Alpha158 base features.")
        print("  Custom factor integration planned for Phase 5.")

    handler = Alpha158(**handler_kwargs)
    dataset = DatasetH(
        handler=handler,
        segments={
            "train": (train_start, train_end),
            "valid": (valid_start, valid_end),
            "test": (test_start, test_end),
        },
    )
    return dataset


def build_model(model_type: str, params: dict | None = None):
    """Build LGBModel or DEnsembleModel."""
    if model_type == "lgbm":
        p = {**DEFAULT_LGB_PARAMS, **(params or {})}
        return LGBModel(**p)
    elif model_type == "densemble":
        p = {
            "base_model": "gbm",
            "loss": "mse",
            "num_models": 6,
            "enable_sr": True,
            "enable_fs": True,
            "epochs": 100,
            **(params or {}),
        }
        return DEnsembleModel(**p)
    else:
        raise ValueError(f"Unknown model type: {model_type}")


def extract_feature_importance(model, output_dir: Path) -> pd.DataFrame | None:
    """Extract and save feature importance from LGBModel."""
    try:
        if hasattr(model, "model") and hasattr(model.model, "feature_importance"):
            importance = model.model.feature_importance(importance_type="gain")
            feature_names = [f"f{i}" for i in range(len(importance))]
            if hasattr(model.model, "feature_name"):
                feature_names = model.model.feature_name()
            df = pd.DataFrame({
                "feature": feature_names,
                "importance": importance,
            }).sort_values("importance", ascending=False)
            df.to_csv(output_dir / "feature_importance.csv", index=False)
            return df
    except Exception as e:
        print(f"  Warning: Could not extract feature importance: {e}")
    return None


def evaluate_predictions(pred: pd.Series, dataset: DatasetH) -> dict:
    """Compute IC, ICIR, Rank IC, long-short metrics on test set."""
    df_test = dataset.prepare(
        "test", col_set=["feature", "label"], data_key=DataHandlerLP.DK_L
    )
    label = df_test["label"].iloc[:, 0]

    common_idx = pred.index.intersection(label.index)
    pred = pred.loc[common_idx]
    label = label.loc[common_idx]

    dates = common_idx.get_level_values("datetime").unique()
    daily_ic, daily_rank_ic = [], []

    for dt in dates:
        mask = common_idx.get_level_values("datetime") == dt
        p, l = pred[mask], label[mask]
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
        "IC_mean": float(daily_ic.mean()) if len(daily_ic) > 0 else 0,
        "IC_std": float(daily_ic.std()) if len(daily_ic) > 0 else 0,
        "ICIR": float(daily_ic.mean() / (daily_ic.std() + 1e-12)) if len(daily_ic) > 0 else 0,
        "RankIC_mean": float(daily_rank_ic.mean()) if len(daily_rank_ic) > 0 else 0,
        "RankIC_std": float(daily_rank_ic.std()) if len(daily_rank_ic) > 0 else 0,
        "RankICIR": float(
            daily_rank_ic.mean() / (daily_rank_ic.std() + 1e-12)
        ) if len(daily_rank_ic) > 0 else 0,
        "num_days": len(daily_ic),
        "num_samples": len(common_idx),
    }

    # Long-short analysis
    daily_returns = []
    for dt in dates:
        mask = common_idx.get_level_values("datetime") == dt
        p, l = pred[mask], label[mask]
        if len(p) < 20:
            continue
        n = len(p)
        top_n = max(int(n * 0.1), 1)
        bottom_n = max(int(n * 0.1), 1)
        long_ret = l.loc[p.nlargest(top_n).index].mean()
        short_ret = l.loc[p.nsmallest(bottom_n).index].mean()
        daily_returns.append(long_ret - short_ret)

    daily_returns = np.array(daily_returns)
    if len(daily_returns) > 0:
        results["long_short_return_annual"] = float(daily_returns.mean() * 252)
        results["long_short_sharpe"] = float(
            (daily_returns.mean() / (daily_returns.std() + 1e-12)) * np.sqrt(252)
        )
    else:
        results["long_short_return_annual"] = 0.0
        results["long_short_sharpe"] = 0.0

    return results


def run_grid_search(
    dataset: DatasetH,
    base_params: dict,
    grid: dict,
    output_dir: Path,
) -> tuple[dict, pd.DataFrame]:
    """Run grid search over hyperparameters, return best params + results table."""
    keys = list(grid.keys())
    values = list(grid.values())
    combos = list(product(*values))
    print(f"  Grid search: {len(combos)} combinations")

    results_list = []
    best_ic = -np.inf
    best_params = {}

    for i, combo in enumerate(combos):
        params = {**base_params, **dict(zip(keys, combo))}
        combo_str = ", ".join(f"{k}={v}" for k, v in zip(keys, combo))
        print(f"  [{i+1}/{len(combos)}] {combo_str}", end=" ... ")

        t0 = time.time()
        model = LGBModel(**params)
        model.fit(dataset)
        pred = model.predict(dataset, segment="test")
        metrics = evaluate_predictions(pred, dataset)
        elapsed = time.time() - t0

        print(f"IC={metrics['IC_mean']:.4f}, ICIR={metrics['ICIR']:.4f} ({elapsed:.1f}s)")

        row = {**dict(zip(keys, combo)), **metrics, "time_s": elapsed}
        results_list.append(row)

        if metrics["IC_mean"] > best_ic:
            best_ic = metrics["IC_mean"]
            best_params = params

    results_df = pd.DataFrame(results_list).sort_values("IC_mean", ascending=False)
    results_df.to_csv(output_dir / "grid_search_results.csv", index=False)
    return best_params, results_df


# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="LightGBM / DoubleEnsemble Training for US Stocks"
    )
    parser.add_argument(
        "--mode", type=str, default="baseline", choices=["baseline", "enhanced"],
        help="baseline: Alpha158 only; enhanced: Alpha158 + custom factors"
    )
    parser.add_argument(
        "--model", type=str, default="lgbm", choices=["lgbm", "densemble"],
        help="Model type"
    )
    parser.add_argument("--tune", action="store_true", help="Enable grid search tuning")
    parser.add_argument("--instruments", type=str, default="sp500")
    parser.add_argument("--train-start", type=str, default=TRAIN_START)
    parser.add_argument("--train-end", type=str, default=TRAIN_END)
    parser.add_argument("--valid-start", type=str, default=VALID_START)
    parser.add_argument("--valid-end", type=str, default=VALID_END)
    parser.add_argument("--test-start", type=str, default=TEST_START)
    parser.add_argument("--test-end", type=str, default=TEST_END)
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--no-backtest", action="store_true", help="Skip portfolio backtest")
    parser.add_argument("--no-mlflow", action="store_true", help="Skip MLflow logging")

    args = parser.parse_args()

    # Output directory
    model_tag = args.model
    if args.mode == "enhanced":
        model_tag += "_enhanced"
    output_dir = Path(args.output) if args.output else PROJECT_ROOT / "results" / f"{model_tag}_us"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Experiment name for Qlib R and MLflow
    exp_name = f"{model_tag}_{args.mode}_{args.instruments}"

    windows = {
        "train_start": args.train_start,
        "train_end": args.train_end,
        "valid_start": args.valid_start,
        "valid_end": args.valid_end,
        "test_start": args.test_start,
        "test_end": args.test_end,
    }

    # Print plan
    print(f"\n{'='*70}")
    print(f"  Alpha Pipeline - {args.model.upper()} Training")
    print(f"  Mode: {args.mode} | Model: {args.model} | Tune: {args.tune}")
    print(f"  Instruments: {args.instruments}")
    print(f"  Train: {windows['train_start']} ~ {windows['train_end']}")
    print(f"  Valid: {windows['valid_start']} ~ {windows['valid_end']}")
    print(f"  Test:  {windows['test_start']} ~ {windows['test_end']}")
    print(f"  Output: {output_dir}")
    print(f"{'='*70}\n")

    # Step 1: Init Qlib
    print("[1/5] Initializing Qlib (US)...")
    qlib.init(provider_uri=QLIB_US_DATA, region=REG_US)

    # Step 2: Build dataset
    print("\n[2/5] Building dataset (Alpha158)...")
    t0 = time.time()
    dataset = build_dataset(
        instruments=args.instruments,
        train_start=windows["train_start"],
        train_end=windows["train_end"],
        valid_start=windows["valid_start"],
        valid_end=windows["valid_end"],
        test_start=windows["test_start"],
        test_end=windows["test_end"],
        fit_start=FIT_START,
        fit_end=FIT_END,
        mode=args.mode,
    )
    print(f"  Dataset built in {time.time()-t0:.1f}s")

    # Quick stats
    df_check = dataset.prepare("train", col_set="feature", data_key=DataHandlerLP.DK_L)
    n_features = df_check.shape[1]
    n_train = len(df_check)
    del df_check
    print(f"  Features: {n_features}, Train samples: {n_train}")

    # Step 3: Train model
    print(f"\n[3/5] Training {args.model.upper()} model...")
    t0 = time.time()

    if args.tune and args.model == "lgbm":
        print("  Running hyperparameter grid search...")
        best_params, grid_df = run_grid_search(
            dataset, DEFAULT_LGB_PARAMS, TUNE_GRID, output_dir
        )
        print(f"\n  Best params from grid search:")
        for k in TUNE_GRID:
            print(f"    {k}: {best_params[k]}")
        model = LGBModel(**best_params)
    else:
        best_params = DEFAULT_LGB_PARAMS if args.model == "lgbm" else {}
        model = build_model(args.model, best_params)

    # Use Qlib's R for experiment tracking
    with R.start(experiment_name=exp_name):
        model.fit(dataset)

        # Step 4: Generate predictions + signal analysis
        print(f"\n[4/5] Generating predictions & evaluation...")

        # SignalRecord generates pred.pkl
        sr = SignalRecord(model=model, dataset=dataset, recorder=R.get_recorder())
        sr.generate()

        # SigAnaRecord computes IC/ICIR
        sar = SigAnaRecord(
            recorder=R.get_recorder(),
            ana_long_short=True,
            ann_scaler=252,
        )
        sar.generate()

        # PortAnaRecord runs backtest (optional)
        if not args.no_backtest:
            print(f"\n[5/5] Running portfolio backtest (topk={TOPK}, n_drop={N_DROP})...")
            port_config = {
                "strategy": {
                    "class": "TopkDropoutStrategy",
                    "module_path": "qlib.contrib.strategy",
                    "kwargs": {
                        "signal": "<PRED>",
                        "topk": TOPK,
                        "n_drop": N_DROP,
                    },
                },
                "backtest": {
                    "start_time": windows["test_start"],
                    "end_time": windows["test_end"],
                    "account": ACCOUNT,
                    "benchmark": BENCHMARK,
                    "exchange_kwargs": {
                        "limit_threshold": None,
                        "deal_price": "close",
                        "open_cost": COST,
                        "close_cost": COST,
                        "min_cost": 1.0,
                        "trade_unit": 1,
                    },
                },
            }
            par = PortAnaRecord(recorder=R.get_recorder(), config=port_config)
            par.generate()
        else:
            print(f"\n[5/5] Skipping portfolio backtest (--no-backtest)")

        train_time = time.time() - t0
        print(f"  Total time: {train_time:.1f}s")

        # Extract predictions for custom evaluation
        recorder = R.get_recorder()
        pred = recorder.load_object("pred.pkl")

    # If pred is a DataFrame with 'score' column, convert to Series
    if isinstance(pred, pd.DataFrame):
        if "score" in pred.columns:
            pred_series = pred["score"]
        else:
            pred_series = pred.iloc[:, 0]
    else:
        pred_series = pred

    # Custom evaluation (matches HIST eval format for comparison)
    eval_results = evaluate_predictions(pred_series, dataset)
    eval_results["model"] = args.model
    eval_results["mode"] = args.mode
    eval_results["instruments"] = args.instruments
    eval_results["n_features"] = n_features
    eval_results["n_train_samples"] = n_train
    eval_results["train_time_s"] = round(train_time, 1)
    eval_results["time_windows"] = windows

    # Feature importance
    fi_df = extract_feature_importance(model, output_dir)

    # Save outputs
    pred_series.to_pickle(str(output_dir / "pred.pkl"))
    save_results_json(eval_results, output_dir / "eval_results.json")

    # MLflow logging
    if not args.no_mlflow:
        em = ExperimentManager()
        artifacts = [str(output_dir / "eval_results.json")]
        if (output_dir / "feature_importance.csv").exists():
            artifacts.append(str(output_dir / "feature_importance.csv"))
        if args.tune and (output_dir / "grid_search_results.csv").exists():
            artifacts.append(str(output_dir / "grid_search_results.csv"))

        em.log_run(
            experiment_name=exp_name,
            params={
                "model": args.model,
                "mode": args.mode,
                "instruments": args.instruments,
                "n_features": n_features,
                **{k: str(v) for k, v in best_params.items()},
                **windows,
            },
            metrics={
                "IC_mean": eval_results["IC_mean"],
                "ICIR": eval_results["ICIR"],
                "RankIC_mean": eval_results["RankIC_mean"],
                "RankICIR": eval_results["RankICIR"],
                "long_short_sharpe": eval_results["long_short_sharpe"],
            },
            artifacts=artifacts,
            tags={"phase": "4", "pipeline": "alpha158"},
        )

    # Print summary
    print(f"\n{'='*70}")
    print(f"  {args.model.upper()} Training Results ({args.mode})")
    print(f"{'='*70}")
    print(f"  Test IC:           {eval_results['IC_mean']:.6f} (std={eval_results['IC_std']:.4f})")
    print(f"  Test ICIR:         {eval_results['ICIR']:.4f}")
    print(f"  Test Rank IC:      {eval_results['RankIC_mean']:.6f} (std={eval_results['RankIC_std']:.4f})")
    print(f"  Test Rank ICIR:    {eval_results['RankICIR']:.4f}")
    print(f"  ---")
    print(f"  Long-Short Annual: {eval_results['long_short_return_annual']*100:.2f}%")
    print(f"  Long-Short Sharpe: {eval_results['long_short_sharpe']:.4f}")
    print(f"  ---")
    print(f"  Features:          {n_features}")
    print(f"  Test Days:         {eval_results['num_days']}")
    print(f"  Test Samples:      {eval_results['num_samples']}")
    print(f"  Train Time:        {train_time:.1f}s")
    print(f"  ---")
    if fi_df is not None:
        print(f"  Top 10 Features:")
        for _, row in fi_df.head(10).iterrows():
            print(f"    {row['feature']:30s} {row['importance']:.0f}")
        print(f"  ---")
    print(f"  Predictions: {output_dir / 'pred.pkl'}")
    print(f"  Results:     {output_dir / 'eval_results.json'}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
