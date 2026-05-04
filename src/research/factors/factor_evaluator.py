"""Factor evaluation toolkit for computing IC, ICIR, Rank IC, and turnover.

This module provides tools to evaluate factor quality by measuring how well
factor values predict future stock returns.

Key Metrics:
- IC (Information Coefficient): Pearson correlation between factor and future return
- Rank IC: Spearman rank correlation (more robust to outliers)
- ICIR: IC / std(IC), measures IC consistency across time
- Factor Turnover: How much factor rankings change day-to-day
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class FactorEvaluator:
    """Evaluate factor quality using IC, ICIR, Rank IC, and turnover metrics.

    Usage:
        evaluator = FactorEvaluator(factor_data, return_data)
        report = evaluator.evaluate()
        evaluator.save_report(report, "results/factors/report.csv")
    """

    def __init__(
        self,
        factor_df: pd.DataFrame,
        label_df: pd.Series | pd.DataFrame | None = None,
        forward_periods: int = 1,
    ):
        """Initialize the factor evaluator.

        Args:
            factor_df: DataFrame with MultiIndex (datetime, instrument) and
                factor columns. This is the standard Qlib data format.
            label_df: Series or single-column DataFrame with forward returns,
                sharing the same MultiIndex. If None, assumes factor_df already
                contains a 'LABEL0' column.
            forward_periods: Number of forward periods for return calculation
                (only used if label_df is None and no LABEL0 column exists).
        """
        self.factor_df = factor_df
        self.forward_periods = forward_periods

        if label_df is not None:
            if isinstance(label_df, pd.DataFrame):
                self.label = label_df.iloc[:, 0]
            else:
                self.label = label_df
        elif "LABEL0" in factor_df.columns:
            self.label = factor_df["LABEL0"]
            self.factor_df = factor_df.drop(columns=["LABEL0"])
        else:
            raise ValueError(
                "Either provide label_df or ensure factor_df has a 'LABEL0' column."
            )

    def compute_ic(self, method: str = "pearson") -> pd.DataFrame:
        """Compute daily IC for each factor (vectorized implementation).

        Args:
            method: Correlation method. "pearson" for IC, "spearman" for Rank IC.

        Returns:
            DataFrame with datetime index and factor columns, containing daily IC.
        """
        aligned = self.factor_df.copy()
        aligned["_label"] = self.label
        aligned = aligned.dropna(subset=["_label"])

        if method == "spearman":
            # Rank within each day for Spearman correlation
            grouped = aligned.groupby(level="datetime")
            ranked = grouped.rank(pct=True)
            ranked["_label"] = grouped["_label"].rank(pct=True)
            # Pearson of ranks = Spearman
            return self._vectorized_corr(ranked)
        else:
            return self._vectorized_corr(aligned)

    @staticmethod
    def _vectorized_corr(df: pd.DataFrame) -> pd.DataFrame:
        """Compute per-day correlation of each column with '_label' column."""
        label_col = "_label"
        factor_cols = [c for c in df.columns if c != label_col]

        # Use transform to broadcast group means back to original shape
        group_means = df.groupby(level="datetime").transform("mean")
        deviations = df - group_means

        dev_label = deviations[label_col]
        sq_label = (dev_label ** 2).groupby(level="datetime").sum()

        results = {}
        for col in factor_cols:
            dev_f = deviations[col]
            prod = (dev_f * dev_label).groupby(level="datetime").sum()
            sq_f = (dev_f ** 2).groupby(level="datetime").sum()
            denom = np.sqrt(sq_f * sq_label)
            results[col] = prod / denom.replace(0, np.nan)

        return pd.DataFrame(results).sort_index()

    def compute_ic_summary(
        self,
        ic_pearson: pd.DataFrame | None = None,
        ic_spearman: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        """Compute comprehensive IC statistics for each factor.

        Args:
            ic_pearson: Pre-computed Pearson IC (avoids recomputation).
            ic_spearman: Pre-computed Spearman IC (avoids recomputation).

        Returns:
            DataFrame with factors as rows and metrics as columns.
        """
        if ic_pearson is None:
            ic_pearson = self.compute_ic(method="pearson")
        if ic_spearman is None:
            ic_spearman = self.compute_ic(method="spearman")

        summary = pd.DataFrame(
            {
                "IC_mean": ic_pearson.mean(),
                "IC_std": ic_pearson.std(),
                "ICIR": ic_pearson.mean() / (ic_pearson.std() + 1e-8),
                "RankIC_mean": ic_spearman.mean(),
                "RankIC_std": ic_spearman.std(),
                "RankICIR": ic_spearman.mean() / (ic_spearman.std() + 1e-8),
                "IC_positive_ratio": (ic_pearson > 0).mean(),
                "abs_IC_mean": ic_pearson.abs().mean(),
            }
        )
        return summary.sort_values("abs_IC_mean", ascending=False)

    def compute_turnover(
        self, quantile: float = 0.2, max_factors: int = 20
    ) -> pd.DataFrame:
        """Compute daily factor turnover (how much top-quantile changes).

        Turnover measures the fraction of stocks that enter/exit the top quantile
        from one day to the next. Lower turnover means lower trading costs.

        Args:
            quantile: Top quantile threshold (e.g., 0.2 = top 20%).
            max_factors: Max number of factors to evaluate (for speed).

        Returns:
            DataFrame with datetime index and factor columns.
        """
        # Limit number of factors for performance
        factor_cols = self.factor_df.columns.tolist()
        if len(factor_cols) > max_factors:
            logger.info(
                "Turnover: sampling %d/%d factors for speed.",
                max_factors,
                len(factor_cols),
            )
            factor_cols = factor_cols[:max_factors]

        dates = self.factor_df.index.get_level_values("datetime").unique().sort_values()

        results = {}
        prev_top = {}

        for date in dates:
            try:
                day_data = self.factor_df.xs(date, level="datetime")
            except KeyError:
                continue

            turnover_row = {}
            for col in factor_cols:
                vals = day_data[col].dropna()
                if len(vals) < 10:
                    turnover_row[col] = np.nan
                    continue

                threshold = vals.quantile(1 - quantile)
                current_top = set(vals[vals >= threshold].index)

                if col in prev_top and prev_top[col]:
                    prev = prev_top[col]
                    union = prev | current_top
                    if len(union) > 0:
                        changed = len(prev.symmetric_difference(current_top))
                        turnover_row[col] = changed / (len(union))
                    else:
                        turnover_row[col] = np.nan
                else:
                    turnover_row[col] = np.nan

                prev_top[col] = current_top

            results[date] = turnover_row

        return pd.DataFrame(results).T.sort_index()

    def compute_factor_correlation(self) -> pd.DataFrame:
        """Compute pairwise correlation between factors (for collinearity detection).

        Returns:
            Correlation matrix DataFrame.
        """
        # Sample dates to speed up computation
        dates = self.factor_df.index.get_level_values("datetime").unique()
        if len(dates) > 60:
            sample_dates = np.random.choice(dates, 60, replace=False)
            sampled = self.factor_df.loc[
                self.factor_df.index.get_level_values("datetime").isin(sample_dates)
            ]
        else:
            sampled = self.factor_df

        return sampled.corr()

    def detect_collinear_factors(self, threshold: float = 0.7) -> list[tuple[str, str, float]]:
        """Find factor pairs with correlation above threshold.

        Args:
            threshold: Absolute correlation threshold.

        Returns:
            List of (factor_a, factor_b, correlation) tuples.
        """
        corr_matrix = self.compute_factor_correlation()
        pairs = []
        cols = corr_matrix.columns.tolist()
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                c = abs(corr_matrix.iloc[i, j])
                if c > threshold:
                    pairs.append((cols[i], cols[j], round(c, 4)))
        return sorted(pairs, key=lambda x: -x[2])

    def evaluate(self) -> dict[str, pd.DataFrame]:
        """Run full factor evaluation and return all results.

        Returns:
            Dict with keys:
            - "ic_summary": IC/ICIR/RankIC summary per factor
            - "daily_ic": Daily IC time series
            - "daily_rank_ic": Daily Rank IC time series
            - "turnover": Daily turnover per factor
            - "correlation": Factor correlation matrix
            - "collinear_pairs": Collinear factor pairs
        """
        logger.info("Computing Pearson IC...")
        daily_ic = self.compute_ic(method="pearson")

        logger.info("Computing Rank IC...")
        daily_rank_ic = self.compute_ic(method="spearman")

        logger.info("Computing IC summary...")
        ic_summary = self.compute_ic_summary(
            ic_pearson=daily_ic, ic_spearman=daily_rank_ic
        )

        logger.info("Computing turnover...")
        turnover = self.compute_turnover()

        logger.info("Computing factor correlations...")
        correlation = self.compute_factor_correlation()
        collinear = self.detect_collinear_factors()

        logger.info(
            "Factor evaluation complete. %d factors evaluated over %d days.",
            len(ic_summary),
            len(daily_ic),
        )

        return {
            "ic_summary": ic_summary,
            "daily_ic": daily_ic,
            "daily_rank_ic": daily_rank_ic,
            "turnover_summary": turnover.mean().to_frame("avg_turnover"),
            "correlation": correlation,
            "collinear_pairs": pd.DataFrame(
                collinear, columns=["factor_a", "factor_b", "correlation"]
            ),
        }

    @staticmethod
    def save_report(
        results: dict[str, pd.DataFrame],
        output_dir: str | Path,
    ) -> None:
        """Save evaluation results to CSV files.

        Args:
            results: Output from evaluate().
            output_dir: Directory to save CSV files.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for name, df in results.items():
            path = output_dir / f"{name}.csv"
            df.to_csv(path)
            logger.info("Saved %s to %s", name, path)

    @staticmethod
    def print_summary(results: dict[str, pd.DataFrame]) -> None:
        """Print a concise summary of factor evaluation results."""
        summary = results["ic_summary"]
        print("\n" + "=" * 80)
        print("FACTOR EVALUATION SUMMARY")
        print("=" * 80)
        print(f"\nTotal factors evaluated: {len(summary)}")

        # Effective factors (|Rank IC| > 0.03)
        effective = summary[summary["RankIC_mean"].abs() > 0.03]
        print(f"Effective factors (|Rank IC| > 0.03): {len(effective)}")

        # Top factors
        print("\n--- Top 10 Factors by |Rank IC| ---")
        top = summary.nlargest(10, "abs_IC_mean")
        for factor_name in top.index:
            row = top.loc[factor_name]
            print(
                f"  {factor_name:30s}  RankIC={row['RankIC_mean']:+.4f}  "
                f"ICIR={row['ICIR']:+.4f}  RankICIR={row['RankICIR']:+.4f}"
            )

        # Collinear pairs
        collinear = results["collinear_pairs"]
        if len(collinear) > 0:
            print(f"\n--- Collinear Factor Pairs (|corr| > 0.7): {len(collinear)} ---")
            for _, row in collinear.head(10).iterrows():
                print(
                    f"  {row['factor_a']:20s} <-> {row['factor_b']:20s}  "
                    f"corr={row['correlation']:.4f}"
                )

        # Turnover
        turnover = results["turnover_summary"]
        print("\n--- Average Factor Turnover (top 5 lowest) ---")
        lowest = turnover.nsmallest(5, "avg_turnover")
        for factor_name in lowest.index:
            print(
                f"  {factor_name:30s}  turnover={lowest.loc[factor_name, 'avg_turnover']:.4f}"
            )

        print("\n" + "=" * 80)
