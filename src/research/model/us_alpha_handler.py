"""
US Alpha360 Handler: Alpha360 variant without $vwap for US stock data.

US stock data from Yahoo Finance does not include VWAP.
Standard Alpha360 generates 360 features (6 fields x 60 days) including VWAP.
This handler generates 300 features (5 fields x 60 days) using only OHLCV.

Usage with HIST model: set d_feat=5 so reshape produces (N, 5, 60) -> (N, 60, 5).
"""

from qlib.data.dataset.loader import QlibDataLoader
from qlib.data.dataset.handler import DataHandlerLP
from qlib.contrib.data.handler import check_transform_proc


_DEFAULT_INFER_PROCESSORS = [
    {"class": "RobustZScoreNorm", "kwargs": {"fields_group": "feature", "clip_outlier": True}},
    {"class": "Fillna", "kwargs": {"fields_group": "feature"}},
]

_DEFAULT_LEARN_PROCESSORS = [
    {"class": "DropnaLabel"},
    {"class": "CSRankNorm", "kwargs": {"fields_group": "label"}},
]


class USAlpha360DL(QlibDataLoader):
    """DataLoader for US stocks: Alpha360 without VWAP (300 features)."""

    def __init__(self, config=None, **kwargs):
        _config = {"feature": self.get_feature_config()}
        if config is not None:
            _config.update(config)
        super().__init__(config=_config, **kwargs)

    @staticmethod
    def get_feature_config():
        fields = []
        names = []
        # CLOSE: 60 features
        for i in range(59, 0, -1):
            fields.append("Ref($close, %d)/$close" % i)
            names.append("CLOSE%d" % i)
        fields.append("$close/$close")
        names.append("CLOSE0")
        # OPEN: 60 features
        for i in range(59, 0, -1):
            fields.append("Ref($open, %d)/$close" % i)
            names.append("OPEN%d" % i)
        fields.append("$open/$close")
        names.append("OPEN0")
        # HIGH: 60 features
        for i in range(59, 0, -1):
            fields.append("Ref($high, %d)/$close" % i)
            names.append("HIGH%d" % i)
        fields.append("$high/$close")
        names.append("HIGH0")
        # LOW: 60 features
        for i in range(59, 0, -1):
            fields.append("Ref($low, %d)/$close" % i)
            names.append("LOW%d" % i)
        fields.append("$low/$close")
        names.append("LOW0")
        # VOLUME: 60 features (skip VWAP)
        for i in range(59, 0, -1):
            fields.append("Ref($volume, %d)/($volume+1e-12)" % i)
            names.append("VOLUME%d" % i)
        fields.append("$volume/($volume+1e-12)")
        names.append("VOLUME0")
        return fields, names


class USAlpha360(DataHandlerLP):
    """Alpha360 handler for US stocks (no VWAP, 300 features, d_feat=5).

    Follows the same pattern as qlib.contrib.data.handler.Alpha360:
    uses check_transform_proc to inject fit_start_time/fit_end_time
    into processors that need them (e.g. RobustZScoreNorm).
    """

    def __init__(
        self,
        instruments="sp500",
        start_time=None,
        end_time=None,
        freq="day",
        infer_processors=_DEFAULT_INFER_PROCESSORS,
        learn_processors=_DEFAULT_LEARN_PROCESSORS,
        fit_start_time=None,
        fit_end_time=None,
        filter_pipe=None,
        inst_processors=None,
        **kwargs,
    ):
        infer_processors = check_transform_proc(infer_processors, fit_start_time, fit_end_time)
        learn_processors = check_transform_proc(learn_processors, fit_start_time, fit_end_time)

        data_loader = {
            "class": "QlibDataLoader",
            "kwargs": {
                "config": {
                    "feature": USAlpha360DL.get_feature_config(),
                    "label": kwargs.pop("label", (
                        ["Ref($close, -2)/Ref($close, -1) - 1"],
                        ["LABEL0"],
                    )),
                },
                "filter_pipe": filter_pipe,
                "freq": freq,
                "inst_processors": inst_processors,
            },
        }

        super().__init__(
            instruments=instruments,
            start_time=start_time,
            end_time=end_time,
            data_loader=data_loader,
            learn_processors=learn_processors,
            infer_processors=infer_processors,
            **kwargs,
        )
