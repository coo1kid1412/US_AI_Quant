"""Custom Alpha factors designed for US stock market.

Each factor is defined as a Qlib expression string paired with a descriptive name.
Factors are designed to complement Alpha158's built-in feature set, focusing on
US market-specific patterns.

Factor categories:
- Multi-scale momentum: Capture trend at different time horizons
- Volatility regime: Differentiate high/low volatility environments
- Volume-price dynamics: Detect divergence between price and volume
- Mean reversion: Short-term reversal signals
- Relative strength: Stock performance vs market/peers
"""


# Custom factor definitions: (expression, name)
# All expressions use Qlib's expression engine syntax.
#
# Qlib Ref() convention:
#   Ref($close, N) where N>0 means N periods IN THE PAST (look-back)
#   Negative N is for forward-looking (label use), not for D.features()
CUSTOM_US_FACTORS: list[tuple[str, str]] = [
    # ── Multi-scale Momentum ──────────────────────────────────────────
    # 5-day return: current close / close 5 days ago - 1
    (
        "$close / Ref($close, 5) - 1",
        "MOM5",
    ),
    # 20-day return
    (
        "$close / Ref($close, 20) - 1",
        "MOM20",
    ),
    # 60-day return
    (
        "$close / Ref($close, 60) - 1",
        "MOM60",
    ),
    # Momentum divergence: short-term vs long-term momentum difference.
    # Captures momentum regime transitions.
    (
        "$close / Ref($close, 5) - $close / Ref($close, 60)",
        "MOM_DIVERGE",
    ),
    # Momentum acceleration: current 20d momentum minus previous 20d momentum.
    (
        "$close / Ref($close, 20) - Ref($close, 20) / Ref($close, 40)",
        "MOM_ACCEL",
    ),

    # ── Volatility Regime ─────────────────────────────────────────────
    # Volatility ratio: recent vol vs longer-term vol.
    # High values = vol expansion (risk-off), low values = compression.
    (
        "Std($close, 5) / (Std($close, 20) + 1e-8)",
        "VOL_RATIO_5_20",
    ),
    # Realized volatility change (20d vs 60d).
    (
        "Std($close, 20) / (Std($close, 60) + 1e-8)",
        "VOL_RATIO_20_60",
    ),
    # High-low range relative to close (intraday volatility proxy).
    (
        "Mean(($high - $low) / ($close + 1e-8), 10)",
        "AVG_RANGE_10",
    ),

    # ── Volume-Price Dynamics ─────────────────────────────────────────
    # Volume surge: ratio of recent volume vs longer-term average.
    (
        "Mean($volume, 5) / (Mean($volume, 20) + 1e-8)",
        "VOL_SURGE_5_20",
    ),
    # Volume-price correlation: positive = price and volume co-move.
    (
        "Corr($close / Ref($close, 1), Log($volume + 1), 20)",
        "VP_CORR_20",
    ),
    # On-Balance Volume derivative: cumulative volume direction over 10 days.
    (
        "Sum(If($close > Ref($close, 1), $volume, 0), 10)"
        " / (Sum($volume, 10) + 1e-8)",
        "OBV_RATIO_10",
    ),

    # ── Mean Reversion ────────────────────────────────────────────────
    # Distance from 20-day moving average (normalized by std).
    (
        "($close - Mean($close, 20)) / (Std($close, 20) + 1e-8)",
        "DIST_MA20",
    ),
    # RSI-like indicator (14-day): fraction of up-moves.
    (
        "Sum(Greater($close - Ref($close, 1), 0), 14)"
        " / (Sum(Abs($close - Ref($close, 1)), 14) + 1e-8)",
        "RSI_14",
    ),
]


def get_custom_factor_expressions() -> list[tuple[str, str]]:
    """Return all custom factor (expression, name) pairs."""
    return CUSTOM_US_FACTORS.copy()


def get_custom_factor_names() -> list[str]:
    """Return just the names of all custom factors."""
    return [name for _, name in CUSTOM_US_FACTORS]
