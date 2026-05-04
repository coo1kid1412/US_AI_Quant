"""Alpha158 DataHandler configuration for US stocks.

Alpha158 is Qlib's built-in feature set containing 158+ factors covering:
- KBAR: Candlestick patterns (9 features)
- PRICE: Relative price features (4 features)
- ROLLING: Rolling statistics at multiple windows (154 features)

This module provides configuration helpers to instantiate Alpha158 with
proper US stock market settings.
"""

from typing import Any


# Default time segments for US stock backtesting.
# Qlib US default windows (compatible with offline data ~2020-11)
DEFAULT_SEGMENTS = {
    "train": ("2008-01-01", "2014-12-31"),
    "valid": ("2015-01-01", "2016-12-31"),
    "test": ("2017-01-01", "2020-08-01"),
}


def get_alpha158_config(
    instruments: str = "sp500",
    start_time: str = "2008-01-01",
    end_time: str = "2020-08-01",
    fit_start_time: str = "2008-01-01",
    fit_end_time: str = "2014-12-31",
) -> dict[str, Any]:
    """Get Alpha158 DataHandler configuration for US stocks.

    Args:
        instruments: Stock pool. One of "all", "sp500", "nasdaq100".
        start_time: Data loading start date.
        end_time: Data loading end date.
        fit_start_time: Processor fitting start date.
        fit_end_time: Processor fitting end date. MUST be < test start.

    Returns:
        Dict suitable for use as ``handler.kwargs`` in a Qlib workflow YAML.
    """
    return {
        "start_time": start_time,
        "end_time": end_time,
        "fit_start_time": fit_start_time,
        "fit_end_time": fit_end_time,
        "instruments": instruments,
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


def get_enhanced_alpha158_config(
    instruments: str = "sp500",
    start_time: str = "2008-01-01",
    end_time: str = "2020-08-01",
    fit_start_time: str = "2008-01-01",
    fit_end_time: str = "2014-12-31",
    custom_factor_exprs: list[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """Get Alpha158 + custom factors DataHandler configuration.

    Uses Qlib's Alpha158 as base, with additional custom factor expressions
    appended via extra feature fields.

    Args:
        instruments: Stock pool.
        start_time: Data loading start date.
        end_time: Data loading end date.
        fit_start_time: Processor fitting start date.
        fit_end_time: Processor fitting end date.
        custom_factor_exprs: List of (expression, name) tuples for custom factors.
            If None, uses the default US stock custom factors.

    Returns:
        Dict config for DataHandler with enhanced feature set.
    """
    if custom_factor_exprs is None:
        from .custom_factors import get_custom_factor_expressions

        custom_factor_exprs = get_custom_factor_expressions()

    expressions = [expr for expr, _name in custom_factor_exprs]
    names = [name for _expr, name in custom_factor_exprs]

    config = get_alpha158_config(
        instruments=instruments,
        start_time=start_time,
        end_time=end_time,
        fit_start_time=fit_start_time,
        fit_end_time=fit_end_time,
    )

    # Store custom expressions in config for DataLoader extension
    config["_custom_expressions"] = expressions
    config["_custom_names"] = names

    return config


def get_dataset_config(
    handler_config: dict[str, Any] | None = None,
    segments: dict[str, tuple[str, str]] | None = None,
    handler_class: str = "Alpha158",
    handler_module: str = "qlib.contrib.data.handler",
) -> dict[str, Any]:
    """Get DatasetH configuration combining handler and time segments.

    Args:
        handler_config: DataHandler kwargs. Defaults to Alpha158 US config.
        segments: Train/valid/test time segments.
        handler_class: DataHandler class name.
        handler_module: DataHandler module path.

    Returns:
        Dict config for DatasetH.
    """
    if handler_config is None:
        handler_config = get_alpha158_config()
    if segments is None:
        segments = DEFAULT_SEGMENTS

    return {
        "class": "DatasetH",
        "module_path": "qlib.data.dataset",
        "kwargs": {
            "handler": {
                "class": handler_class,
                "module_path": handler_module,
                "kwargs": handler_config,
            },
            "segments": segments,
        },
    }
