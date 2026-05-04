"""Verify Alpha158 factor library on US stock data.

This script:
1. Initializes Qlib with US stock data
2. Loads Alpha158 features for S&P 500 stocks
3. Computes custom US factors
4. Runs factor evaluation (IC, ICIR, Rank IC)
5. Detects collinear factors
6. Saves evaluation report

Usage:
    cd /Users/lailixiang/WorkSpace/QoderWorkspace/US_AI_Quant
    source venv/bin/activate
    python scripts/verify_alpha158.py
"""

import sys
import logging
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    import qlib
    from qlib.data import D
    from qlib.contrib.data.handler import Alpha158

    from src.research.factors.custom_factors import get_custom_factor_expressions
    from src.research.factors.factor_evaluator import FactorEvaluator

    # ── Step 1: Initialize Qlib ──────────────────────────────────────
    logger.info("Initializing Qlib with US stock data...")
    qlib.init(
        provider_uri="~/.qlib/qlib_data/us_data",
        region="us",
    )
    logger.info("Qlib initialized successfully.")

    # ── Step 2: Load Alpha158 features ───────────────────────────────
    logger.info("Loading Alpha158 features for S&P 500...")
    handler = Alpha158(
        instruments="sp500",
        start_time="2015-01-01",
        end_time="2020-08-01",
        fit_start_time="2015-01-01",
        fit_end_time="2018-12-31",
    )

    # Get learn data (with label)
    learn_df = handler.fetch(data_key="learn")
    logger.info(
        "Alpha158 learn data loaded: %d rows, %d columns",
        len(learn_df),
        len(learn_df.columns),
    )
    logger.info("Columns sample: %s", list(learn_df.columns[:10]))
    logger.info("Date range: %s to %s",
                learn_df.index.get_level_values("datetime").min(),
                learn_df.index.get_level_values("datetime").max())

    # Check for NaN ratio
    nan_ratio = learn_df.isna().mean()
    high_nan = nan_ratio[nan_ratio > 0.3]
    if len(high_nan) > 0:
        logger.warning(
            "%d columns have >30%% NaN: %s",
            len(high_nan),
            list(high_nan.index[:5]),
        )

    # ── Step 3: Compute custom factors ───────────────────────────────
    logger.info("Computing custom US stock factors...")
    custom_factors = get_custom_factor_expressions()
    expressions = [expr for expr, _name in custom_factors]
    names = [name for _expr, name in custom_factors]

    instruments = D.instruments("sp500")
    custom_df = D.features(
        instruments=instruments,
        fields=expressions,
        start_time="2015-01-01",
        end_time="2020-08-01",
    )
    custom_df.columns = names
    logger.info(
        "Custom factors computed: %d rows, %d factors",
        len(custom_df),
        len(custom_df.columns),
    )

    # ── Step 4: Evaluate Alpha158 factors ────────────────────────────
    logger.info("Evaluating Alpha158 factor quality...")

    # Separate features and label
    if "LABEL0" in learn_df.columns:
        label = learn_df["LABEL0"]
        features = learn_df.drop(columns=["LABEL0"])
    else:
        logger.error("LABEL0 column not found in learn data.")
        return

    # Evaluate built-in Alpha158 factors
    evaluator_158 = FactorEvaluator(features, label)
    results_158 = evaluator_158.evaluate()

    print("\n\n" + "#" * 80)
    print("# ALPHA158 FACTOR EVALUATION (US Stocks - S&P 500)")
    print("#" * 80)
    FactorEvaluator.print_summary(results_158)

    # Save Alpha158 evaluation report
    output_dir = PROJECT_ROOT / "results" / "factors" / "alpha158_evaluation"
    FactorEvaluator.save_report(results_158, output_dir)
    logger.info("Alpha158 evaluation saved to %s", output_dir)

    # ── Step 5: Evaluate custom factors ──────────────────────────────
    logger.info("Evaluating custom factors...")

    # Debug index formats
    logger.info(
        "Custom factor index: names=%s, sample=%s",
        custom_df.index.names,
        custom_df.index[:3].tolist(),
    )
    logger.info(
        "Label index: names=%s, sample=%s",
        label.index.names,
        label.index[:3].tolist(),
    )

    # D.features() returns (instrument, datetime) but handler returns (datetime, instrument)
    # Swap levels to match handler's format
    if custom_df.index.names != label.index.names:
        logger.info("Swapping custom factor index levels to match handler format...")
        custom_df = custom_df.swaplevel()
        custom_df = custom_df.sort_index()

    # Align via reindex on features DataFrame (which shares index with label)
    aligned_custom = custom_df.reindex(features.index)
    n_valid = aligned_custom.notna().all(axis=1).sum()
    logger.info(
        "Custom factors aligned via reindex: %d/%d valid rows",
        n_valid,
        len(features),
    )

    if n_valid > 100:
        evaluator_custom = FactorEvaluator(aligned_custom.dropna(), label)
        results_custom = evaluator_custom.evaluate()

        print("\n\n" + "#" * 80)
        print("# CUSTOM FACTOR EVALUATION (US Stocks - S&P 500)")
        print("#" * 80)
        FactorEvaluator.print_summary(results_custom)

        # Save custom factor evaluation
        output_dir_custom = PROJECT_ROOT / "results" / "factors" / "custom_evaluation"
        FactorEvaluator.save_report(results_custom, output_dir_custom)
        logger.info("Custom factor evaluation saved to %s", output_dir_custom)

    # ── Step 6: Summary ──────────────────────────────────────────────
    print("\n\n" + "#" * 80)
    print("# COMBINED SUMMARY")
    print("#" * 80)

    ic_158 = results_158["ic_summary"]
    effective_158 = ic_158[ic_158["RankIC_mean"].abs() > 0.03]
    print(f"\nAlpha158: {len(ic_158)} factors, {len(effective_158)} effective (|RankIC|>0.03)")

    if n_valid > 100:
        ic_custom = results_custom["ic_summary"]
        effective_custom = ic_custom[ic_custom["RankIC_mean"].abs() > 0.03]
        print(f"Custom:   {len(ic_custom)} factors, {len(effective_custom)} effective (|RankIC|>0.03)")

    print("\nPhase 4 ACT_16 verification complete!")


if __name__ == "__main__":
    main()
