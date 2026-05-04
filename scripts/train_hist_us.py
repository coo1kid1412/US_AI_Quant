#!/usr/bin/env python3
"""
HIST Model Training for US Stocks
==================================
Adapts HIST (Graph-based Framework for Stock Trend Forecasting) for US market.

Training modes:
  cold-start:      Full retrain from scratch (冷启)
  incremental:     Fine-tune with expanded window (追N天)
  new-features:    Full retrain after adding new alpha factors (新特征冷启)

Usage:
  # Cold start (full retrain)
  python scripts/train_hist_us.py --mode cold-start --gpu 0

  # Incremental: add 1 trading day
  python scripts/train_hist_us.py --mode incremental --days 1 --gpu 0

  # Incremental: add 5 trading days with custom epochs
  python scripts/train_hist_us.py --mode incremental --days 5 --epochs 20 --gpu 0

  # New features: full retrain after adding alpha factors
  python scripts/train_hist_us.py --mode new-features --gpu 0

  # CPU mode (for testing, much slower)
  python scripts/train_hist_us.py --mode cold-start --gpu -1 --epochs 2
"""
import os
import sys
import copy
import pickle
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Text, Union
from datetime import datetime

import torch
import torch.nn as nn
import torch.optim as optim

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import qlib
from qlib.constant import REG_US
from qlib.data import D
from qlib.model.base import Model
from qlib.data.dataset import DatasetH
from qlib.data.dataset.handler import DataHandlerLP
from qlib.contrib.model.pytorch_hist import HISTModel
from qlib.contrib.model.pytorch_gru import GRUModel
from qlib.contrib.model.pytorch_lstm import LSTMModel
from qlib.utils import get_or_create_path, init_instance_by_config
from qlib.log import get_module_logger

# Import custom US handler
from research.model.us_alpha_handler import USAlpha360, USAlpha360DL

# ============================================================
# Patch: HISTModel.forward issues:
# 1. CPU: torch.get_device(x) returns -1, torch.device(-1) raises RuntimeError.
# 2. GPU: internal torch.ones/eye/linspace create on CPU then .to(device),
#    causing slow CPU→GPU transfers every forward pass.
# Fix: On GPU, set default device so all tensor creation happens on GPU.
#      On CPU, intercept torch.device(-1) and return the input tensor's device.
# ============================================================
_original_hist_forward = HISTModel.forward

def _patched_hist_forward(self, x, concept_matrix):
    """Patched forward for both CPU and GPU correctness + GPU performance."""
    if x.device.type != "cpu":
        # GPU path: set default device so torch.ones/eye/linspace create on GPU directly
        _prev_default = None
        try:
            _prev_default = torch.get_default_device()
        except Exception:
            pass
        torch.set_default_device(x.device)
        try:
            result = _original_hist_forward(self, x, concept_matrix)
        finally:
            if _prev_default is not None:
                torch.set_default_device(_prev_default)
            else:
                torch.set_default_device('cpu')
        return result

    # CPU path: patch torch.device to handle -1 from torch.get_device
    # torch.get_device returns -1 for CPU tensors, but torch.device(-1) raises RuntimeError.
    # Fix: intercept torch.device(-1) and return the input tensor's device (cpu).
    _orig_torch_device = torch.device

    def _safe_device(*args, **kwargs):
        if len(args) == 1 and isinstance(args[0], int) and args[0] < 0:
            return x.device
        return _orig_torch_device(*args, **kwargs)

    torch.device = _safe_device
    try:
        result = _original_hist_forward(self, x, concept_matrix)
    finally:
        torch.device = _orig_torch_device
    return result

HISTModel.forward = _patched_hist_forward

# ============================================================
# Configuration
# ============================================================
QLIB_US_DATA = os.path.expanduser("~/.qlib/qlib_data/us_data")
DATA_DIR = PROJECT_ROOT / "data" / "hist"
RESULT_DIR = PROJECT_ROOT / "results" / "hist_us"

MARKET = "sp500"
D_FEAT = 5  # OHLCV without VWAP
HIDDEN_SIZE = 64
NUM_LAYERS = 2
DROPOUT = 0.0
N_EPOCHS = 100
LR = 0.0001
EARLY_STOP = 15
BASE_MODEL = "GRU"

# Default time segments (updated for 2026 data range)
FIT_START   = "2008-01-01"
TRAIN_START = "2008-01-01"
TRAIN_END   = "2023-12-31"
VALID_START = "2024-01-01"
VALID_END   = "2025-12-31"
TEST_START  = "2026-01-01"
TEST_END    = "2026-05-01"

CHECKPOINT_FORMAT_VERSION = 2


# ============================================================
# Checkpoint helpers
# ============================================================
def save_checkpoint(save_path, model_state_dict, optimizer_state_dict,
                    best_epoch, best_score, training_mode, config,
                    training_history, eval_results=None):
    """Save enhanced checkpoint with full training state."""
    checkpoint = {
        "format_version": CHECKPOINT_FORMAT_VERSION,
        "model_state_dict": model_state_dict,
        "optimizer_state_dict": optimizer_state_dict,
        "epoch": best_epoch,
        "best_score": float(best_score),
        "training_mode": training_mode,
        "config": config,
        "training_history": training_history,
        "eval_results": eval_results or {},
        "timestamp": datetime.now().isoformat(),
    }
    torch.save(checkpoint, save_path)


def load_checkpoint(path):
    """Load checkpoint with backward compatibility.

    Returns dict with 'format_version' key if new format,
    or dict with just 'model_state_dict' if old bare state_dict.
    """
    loaded = torch.load(path, map_location="cpu")
    if isinstance(loaded, dict) and "model_state_dict" in loaded:
        return loaded  # New format
    # Old format: bare state_dict (OrderedDict)
    return {
        "format_version": 1,
        "model_state_dict": loaded,
        "optimizer_state_dict": None,
        "epoch": None,
        "best_score": None,
        "training_mode": "unknown",
        "config": {},
        "training_history": {},
        "eval_results": {},
        "timestamp": None,
    }


# ============================================================
# Incremental window computation
# ============================================================
def _find_nearest_calendar_index(calendar_list, date_str):
    """Find the index of date_str in calendar, or the nearest earlier date."""
    cal = list(calendar_list)
    target = pd.Timestamp(date_str)
    for i, d in enumerate(cal):
        if pd.Timestamp(d) >= target:
            return i
    return len(cal) - 1


def compute_incremental_windows(old_config, n_days, calendar_list):
    """Compute new time windows for incremental training.

    Expanding window strategy:
    - train_start stays fixed (never changes)
    - train_end advances by n_days trading days
    - valid/test windows shift forward by n_days
    """
    cal = list(calendar_list)

    old_train_end = old_config["train_end"]
    old_valid_start = old_config["valid_start"]
    old_valid_end = old_config["valid_end"]

    idx_te = _find_nearest_calendar_index(cal, old_train_end)
    idx_vs = _find_nearest_calendar_index(cal, old_valid_start)
    idx_ve = _find_nearest_calendar_index(cal, old_valid_end)

    # Advance by n_days (cap at calendar end)
    new_idx_te = min(idx_te + n_days, len(cal) - 1)
    new_idx_vs = min(idx_vs + n_days, len(cal) - 1)
    new_idx_ve = min(idx_ve + n_days, len(cal) - 1)

    new_te = cal[new_idx_te]
    new_vs = cal[new_idx_vs]
    new_ve = cal[new_idx_ve]

    # Test starts after valid_end
    if new_idx_ve + 1 < len(cal):
        new_ts = cal[new_idx_ve + 1]
    else:
        new_ts = new_ve  # No room for test set

    new_test_end = cal[-1]  # Latest available date

    return {
        "train_start": old_config.get("train_start", TRAIN_START),  # Fixed
        "train_end": new_te,
        "valid_start": new_vs,
        "valid_end": new_ve,
        "test_start": new_ts,
        "test_end": new_test_end,
    }


def compute_incremental_hyperparams(checkpoint_lr, days, explicit_epochs=None, explicit_lr=None):
    """Compute default epochs and lr for incremental training.

    Strategy:
    - days == 1: epochs=5, lr = checkpoint_lr * 0.1
    - days > 1:  epochs=min(20, days), lr = checkpoint_lr * 0.5
    - explicit values override defaults
    """
    if days == 1:
        default_epochs = 5
        lr_multiplier = 0.1
    else:
        default_epochs = min(20, days)
        lr_multiplier = 0.5

    final_epochs = explicit_epochs if explicit_epochs is not None else default_epochs
    final_lr = explicit_lr if explicit_lr is not None else checkpoint_lr * lr_multiplier

    return final_epochs, final_lr


# ============================================================
# Custom HIST with NaN fixes (adapted from user's qlib_project)
# ============================================================
class CustomHIST(Model):
    """HIST model with division-by-zero protection in metric_fn.

    Adapted for US stocks with d_feat=5 (no VWAP).
    Supports incremental training via checkpoint_path parameter.
    """

    def __init__(
        self,
        d_feat=D_FEAT,
        hidden_size=HIDDEN_SIZE,
        num_layers=NUM_LAYERS,
        dropout=DROPOUT,
        n_epochs=N_EPOCHS,
        lr=LR,
        metric="ic",
        early_stop=EARLY_STOP,
        loss="mse",
        base_model=BASE_MODEL,
        model_path=None,
        stock2concept=None,
        stock_index=None,
        optimizer="adam",
        GPU=-1,
        seed=None,
        default_stock_index=0,
    ):
        self.logger = get_module_logger("HIST_US")
        self.logger.info("HIST US stock version...")

        self.d_feat = d_feat
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.n_epochs = n_epochs
        self.lr = lr
        self.metric = metric
        self.early_stop = early_stop
        self.optimizer_name = optimizer.lower()
        self.loss = loss
        self.base_model = base_model
        self.model_path = model_path
        self.stock2concept = stock2concept
        self.stock_index = stock_index
        self.device = torch.device(
            "cuda:%d" % GPU if torch.cuda.is_available() and GPU >= 0 else "cpu"
        )
        self.seed = seed
        self._default_stock_index = default_stock_index

        self.logger.info(
            "HIST parameters:\n"
            f"  d_feat={d_feat}, hidden_size={hidden_size}, num_layers={num_layers}\n"
            f"  dropout={dropout}, n_epochs={n_epochs}, lr={lr}\n"
            f"  metric={metric}, early_stop={early_stop}, loss={loss}\n"
            f"  base_model={base_model}, optimizer={optimizer}\n"
            f"  device={self.device}, seed={seed}"
        )

        if self.seed is not None:
            np.random.seed(self.seed)
            torch.manual_seed(self.seed)

        self.HIST_model = HISTModel(
            d_feat=self.d_feat,
            hidden_size=self.hidden_size,
            num_layers=self.num_layers,
            dropout=self.dropout,
            base_model=self.base_model,
        )
        param_count = sum(p.numel() for p in self.HIST_model.parameters())
        self.logger.info(f"Model size: {param_count * 4 / 1024 / 1024:.2f} MB ({param_count} params)")

        if self.optimizer_name == "adam":
            self.train_optimizer = optim.Adam(self.HIST_model.parameters(), lr=self.lr)
        elif self.optimizer_name == "gd":
            self.train_optimizer = optim.SGD(self.HIST_model.parameters(), lr=self.lr)
        else:
            raise NotImplementedError(f"optimizer {optimizer} is not supported!")

        self.fitted = False
        self.HIST_model.to(self.device)

    @property
    def use_gpu(self):
        return self.device != torch.device("cpu")

    def mse(self, pred, label):
        loss = (pred - label) ** 2
        return torch.mean(loss)

    def loss_fn(self, pred, label):
        mask = ~torch.isnan(label)
        if self.loss == "mse":
            return self.mse(pred[mask], label[mask])
        raise ValueError("unknown loss `%s`" % self.loss)

    def metric_fn(self, pred, label):
        """IC with division-by-zero protection."""
        mask = torch.isfinite(label)
        if mask.sum() < 5:
            return torch.tensor(0.0)
        if self.metric == "ic":
            x = pred[mask]
            y = label[mask]
            vx = x - torch.mean(x)
            vy = y - torch.mean(y)
            denom = torch.sqrt(torch.sum(vx**2)) * torch.sqrt(torch.sum(vy**2))
            return torch.sum(vx * vy) / (denom + 1e-12)
        if self.metric in ("", "loss"):
            return -self.loss_fn(pred[mask], label[mask])
        raise ValueError("unknown metric `%s`" % self.metric)

    def get_daily_inter(self, df, shuffle=False):
        daily_count = df.groupby(level=0, group_keys=False).size().values
        daily_index = np.roll(np.cumsum(daily_count), 1)
        daily_index[0] = 0
        if shuffle:
            daily_shuffle = list(zip(daily_index, daily_count))
            np.random.shuffle(daily_shuffle)
            daily_index, daily_count = zip(*daily_shuffle)
        return daily_index, daily_count

    def _prepare_stock_index(self, df):
        """Map instrument names to stock indices for concept matrix lookup."""
        stock_index_map = np.load(self.stock_index, allow_pickle=True).item()
        si = df.index.get_level_values("instrument").map(stock_index_map)
        si = si.to_series().fillna(self._default_stock_index).astype(int).values
        return si

    def train_epoch(self, x_gpu, y_gpu, si_gpu, s2c_gpu, daily_index, daily_count):
        """Train one epoch with ALL data already on GPU."""
        self.HIST_model.train()
        # Shuffle daily batches
        daily_shuffle = list(zip(daily_index, daily_count))
        np.random.shuffle(daily_shuffle)
        n_days = len(daily_shuffle)

        for i, (idx, count) in enumerate(daily_shuffle):
            batch = slice(idx, idx + count)
            feature = x_gpu[batch]
            concept_matrix = s2c_gpu[si_gpu[batch]]
            label = y_gpu[batch]
            pred = self.HIST_model(feature, concept_matrix)
            loss = self.loss_fn(pred, label)

            self.train_optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_value_(self.HIST_model.parameters(), 3.0)
            self.train_optimizer.step()

            if i == 0 or (i + 1) % 500 == 0:
                self.logger.info(f"  train batch {i+1}/{n_days}, loss={loss.item():.6f}")

    def test_epoch(self, x_gpu, y_gpu, si_gpu, s2c_gpu, daily_index, daily_count, tag=""):
        """Evaluate one epoch with ALL data already on GPU."""
        self.HIST_model.eval()

        scores = []
        losses = []
        n_days = len(daily_index)

        for i, (idx, count) in enumerate(zip(daily_index, daily_count)):
            batch = slice(idx, idx + count)
            feature = x_gpu[batch]
            concept_matrix = s2c_gpu[si_gpu[batch]]
            label = y_gpu[batch]
            with torch.no_grad():
                pred = self.HIST_model(feature, concept_matrix)
                loss = self.loss_fn(pred, label)
                losses.append(loss.item())
                score = self.metric_fn(pred, label)
                scores.append(score.item())

            if i == 0:
                self.logger.info(f"  eval({tag}) batch 1/{n_days}")

        return np.mean(losses), np.nanmean(scores)

    def fit(self, dataset: DatasetH, evals_result=None, save_path=None,
            training_mode="cold-start", checkpoint_path=None, training_config=None):
        """Train the HIST model.

        Parameters
        ----------
        dataset : DatasetH
            The qlib dataset.
        evals_result : dict, optional
            Dict to store training history.
        save_path : str, optional
            Path to save checkpoint.
        training_mode : str
            One of 'cold-start', 'incremental', 'new-features'.
        checkpoint_path : str, optional
            Path to existing checkpoint for incremental mode.
        training_config : dict, optional
            Config dict to embed in checkpoint.
        """
        if evals_result is None:
            evals_result = {}

        # Load checkpoint for incremental mode
        prev_history = {"train": [], "valid": []}
        if training_mode == "incremental" and checkpoint_path:
            ckpt = load_checkpoint(checkpoint_path)
            if ckpt["format_version"] < 2:
                raise ValueError(
                    "旧版checkpoint不支持增量训练 (缺少optimizer state和config)。"
                    "请先执行一次冷启: python scripts/train_hist_us.py --mode cold-start"
                )
            self.HIST_model.load_state_dict(ckpt["model_state_dict"])
            self.train_optimizer.load_state_dict(ckpt["optimizer_state_dict"])
            prev_history = ckpt.get("training_history", {"train": [], "valid": []})
            self.logger.info(
                f"Loaded checkpoint: mode={ckpt.get('training_mode')}, "
                f"epoch={ckpt.get('epoch')}, best_valid_ic={ckpt.get('best_score')}"
            )

        df_train, df_valid = dataset.prepare(
            ["train", "valid"],
            col_set=["feature", "label"],
            data_key=DataHandlerLP.DK_L,
        )
        if df_train.empty or df_valid.empty:
            raise ValueError("Empty data from dataset. Check your dataset config.")

        self.logger.info(f"Train samples: {len(df_train)}, Valid samples: {len(df_valid)}")

        # Prepare stock indices
        si_train = self._prepare_stock_index(df_train)
        si_valid = self._prepare_stock_index(df_valid)

        x_train, y_train = df_train["feature"], df_train["label"]
        x_valid, y_valid = df_valid["feature"], df_valid["label"]

        self.logger.info(f"Feature dim: {x_train.shape[1]} (expected: {self.d_feat * 60})")

        save_path = get_or_create_path(save_path)
        stop_steps = 0
        best_score = -np.inf
        best_epoch = 0
        best_param = None
        evals_result["train"] = []
        evals_result["valid"] = []

        # For incremental: set best_score baseline from checkpoint
        if training_mode == "incremental" and checkpoint_path:
            ckpt = load_checkpoint(checkpoint_path)
            if ckpt.get("best_score") is not None:
                best_score = ckpt["best_score"]
                self.logger.info(f"Incremental baseline: best_valid_ic={best_score:.6f}")

        # Load pretrained base model weights (only for cold-start / new-features)
        if training_mode in ("cold-start", "new-features"):
            if self.base_model == "LSTM":
                pretrained = LSTMModel(
                    d_feat=self.d_feat, hidden_size=self.hidden_size,
                    num_layers=self.num_layers, dropout=self.dropout,
                )
            elif self.base_model == "GRU":
                pretrained = GRUModel(
                    d_feat=self.d_feat, hidden_size=self.hidden_size,
                    num_layers=self.num_layers, dropout=self.dropout,
                )
            else:
                raise ValueError(f"unknown base model `{self.base_model}`")

            model_dict = self.HIST_model.state_dict()
            pretrained_dict = {k: v for k, v in pretrained.state_dict().items() if k in model_dict}
            if pretrained_dict:
                model_dict.update(pretrained_dict)
                self.HIST_model.load_state_dict(model_dict)
                self.logger.info(f"Loaded {len(pretrained_dict)} pretrained base model params")

        # Training loop
        self.logger.info(f"Starting training (mode={training_mode})...")
        self.fitted = True

        # Pre-load ALL data to GPU at once (eliminates CPU→GPU transfer per batch)
        import time as _time
        self.logger.info("Pre-loading all data to GPU...")
        t0 = _time.time()

        # Convert to numpy float32
        x_train_np = x_train.values.astype(np.float32)
        y_train_np = np.squeeze(y_train.values).astype(np.float32)
        x_valid_np = x_valid.values.astype(np.float32)
        y_valid_np = np.squeeze(y_valid.values).astype(np.float32)
        stock2concept_np = np.load(self.stock2concept).astype(np.float32)

        # Move ALL to GPU tensors
        x_train_gpu = torch.from_numpy(x_train_np).to(self.device)
        y_train_gpu = torch.from_numpy(y_train_np).to(self.device)
        x_valid_gpu = torch.from_numpy(x_valid_np).to(self.device)
        y_valid_gpu = torch.from_numpy(y_valid_np).to(self.device)
        s2c_gpu = torch.from_numpy(stock2concept_np).to(self.device)
        si_train_gpu = torch.from_numpy(si_train.astype(np.int64)).to(self.device)
        si_valid_gpu = torch.from_numpy(si_valid.astype(np.int64)).to(self.device)

        # Pre-compute daily indices (stays on CPU - just index arrays)
        train_daily_index, train_daily_count = self.get_daily_inter(x_train, shuffle=False)
        valid_daily_index, valid_daily_count = self.get_daily_inter(x_valid, shuffle=False)

        # Report memory usage
        if self.use_gpu:
            gpu_mem_mb = torch.cuda.memory_allocated(self.device) / 1024 / 1024
            self.logger.info(f"GPU pre-load done in {_time.time()-t0:.1f}s, "
                            f"GPU memory: {gpu_mem_mb:.0f}MB, "
                            f"train: {len(train_daily_count)} days, valid: {len(valid_daily_count)} days")
        else:
            self.logger.info(f"CPU pre-load done in {_time.time()-t0:.1f}s, "
                            f"train: {len(train_daily_count)} days, valid: {len(valid_daily_count)} days")

        # Free numpy arrays
        del x_train_np, y_train_np, x_valid_np, y_valid_np, stock2concept_np

        for epoch in range(self.n_epochs):
            t_epoch = _time.time()
            self.logger.info(f"--- Epoch {epoch} start ---")
            self.train_epoch(x_train_gpu, y_train_gpu, si_train_gpu, s2c_gpu,
                           train_daily_index, train_daily_count)
            self.logger.info(f"  train_epoch done in {_time.time()-t_epoch:.1f}s")

            t_eval = _time.time()
            train_loss, train_score = self.test_epoch(x_train_gpu, y_train_gpu, si_train_gpu, s2c_gpu,
                                                      train_daily_index, train_daily_count, tag="train")
            val_loss, val_score = self.test_epoch(x_valid_gpu, y_valid_gpu, si_valid_gpu, s2c_gpu,
                                                   valid_daily_index, valid_daily_count, tag="valid")
            self.logger.info(f"  eval done in {_time.time()-t_eval:.1f}s")

            evals_result["train"].append(train_score)
            evals_result["valid"].append(val_score)

            self.logger.info(
                f"Epoch {epoch:3d} | Train IC: {train_score:.6f} | Valid IC: {val_score:.6f} "
                f"| Train Loss: {train_loss:.6f} | Valid Loss: {val_loss:.6f}"
            )

            if val_score > best_score:
                best_score = val_score
                stop_steps = 0
                best_epoch = epoch
                best_param = copy.deepcopy(self.HIST_model.state_dict())
            else:
                stop_steps += 1
                if stop_steps >= self.early_stop:
                    self.logger.info(f"Early stop at epoch {epoch}")
                    break

        self.logger.info(f"Best: epoch {best_epoch}, Valid IC = {best_score:.6f}")
        self.HIST_model.load_state_dict(best_param)

        # Save enhanced checkpoint
        merged_history = {
            "train": prev_history.get("train", []) + evals_result["train"],
            "valid": prev_history.get("valid", []) + evals_result["valid"],
        }
        save_checkpoint(
            save_path=save_path,
            model_state_dict=best_param,
            optimizer_state_dict=self.train_optimizer.state_dict(),
            best_epoch=best_epoch,
            best_score=best_score,
            training_mode=training_mode,
            config=training_config or {},
            training_history=merged_history,
        )

        return best_epoch, best_score, evals_result

    def predict(self, dataset: DatasetH, segment: Union[Text, slice] = "test"):
        if not self.fitted:
            raise ValueError("model is not fitted yet!")

        stock2concept_matrix = np.load(self.stock2concept)
        stock_index_map = np.load(self.stock_index, allow_pickle=True).item()

        df_test = dataset.prepare(segment, col_set="feature", data_key=DataHandlerLP.DK_I)
        si_test = df_test.index.get_level_values("instrument").map(stock_index_map)
        si_test = si_test.to_series().fillna(self._default_stock_index).astype(int).values

        index = df_test.index
        x_values = df_test.values

        self.HIST_model.eval()
        preds = []
        daily_index, daily_count = self.get_daily_inter(df_test, shuffle=False)

        for idx, count in zip(daily_index, daily_count):
            batch = slice(idx, idx + count)
            x_batch = torch.from_numpy(x_values[batch]).float().to(self.device)
            concept_matrix = torch.from_numpy(stock2concept_matrix[si_test[batch]]).float().to(self.device)
            with torch.no_grad():
                pred = self.HIST_model(x_batch, concept_matrix).detach().cpu().numpy()
            preds.append(pred)

        return pd.Series(np.concatenate(preds), index=index)


# ============================================================
# Evaluation
# ============================================================
def evaluate_predictions(pred_series: pd.Series, dataset: DatasetH) -> dict:
    """Evaluate model predictions: IC, Rank IC, long-short return."""
    df_test = dataset.prepare("test", col_set=["feature", "label"], data_key=DataHandlerLP.DK_L)
    label = df_test["label"].iloc[:, 0]

    # Align predictions and labels
    common_idx = pred_series.index.intersection(label.index)
    pred = pred_series.loc[common_idx]
    label = label.loc[common_idx]

    results = {}

    # Daily IC
    dates = common_idx.get_level_values("datetime").unique()
    daily_ic = []
    daily_rank_ic = []
    for dt in dates:
        mask = common_idx.get_level_values("datetime") == dt
        p = pred[mask]
        l = label[mask]
        if len(p) < 10:
            continue
        ic = p.corr(l)
        rank_ic = p.rank().corr(l.rank())
        if np.isfinite(ic):
            daily_ic.append(ic)
        if np.isfinite(rank_ic):
            daily_rank_ic.append(rank_ic)

    daily_ic = np.array(daily_ic)
    daily_rank_ic = np.array(daily_rank_ic)

    results["IC_mean"] = daily_ic.mean() if len(daily_ic) > 0 else 0
    results["IC_std"] = daily_ic.std() if len(daily_ic) > 0 else 0
    results["ICIR"] = results["IC_mean"] / (results["IC_std"] + 1e-12)
    results["RankIC_mean"] = daily_rank_ic.mean() if len(daily_rank_ic) > 0 else 0
    results["RankIC_std"] = daily_rank_ic.std() if len(daily_rank_ic) > 0 else 0
    results["RankICIR"] = results["RankIC_mean"] / (results["RankIC_std"] + 1e-12)
    results["num_days"] = len(daily_ic)
    results["num_samples"] = len(common_idx)

    # Long-short analysis
    top_pct = 0.1
    bottom_pct = 0.1
    daily_returns = []
    for dt in dates:
        mask = common_idx.get_level_values("datetime") == dt
        p = pred[mask]
        l = label[mask]
        if len(p) < 20:
            continue
        n = len(p)
        top_n = max(int(n * top_pct), 1)
        bottom_n = max(int(n * bottom_pct), 1)
        top_idx = p.nlargest(top_n).index
        bottom_idx = p.nsmallest(bottom_n).index
        long_ret = l.loc[top_idx].mean()
        short_ret = l.loc[bottom_idx].mean()
        ls_ret = long_ret - short_ret
        daily_returns.append(ls_ret)

    daily_returns = np.array(daily_returns)
    if len(daily_returns) > 0:
        results["long_short_return_daily"] = daily_returns.mean()
        results["long_short_return_annual"] = daily_returns.mean() * 252
        results["long_short_sharpe"] = (daily_returns.mean() / (daily_returns.std() + 1e-12)) * np.sqrt(252)
    else:
        results["long_short_return_daily"] = 0
        results["long_short_return_annual"] = 0
        results["long_short_sharpe"] = 0

    return results


# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="HIST Model Training for US Stocks")

    # Existing arguments
    parser.add_argument("--market", type=str, default=MARKET)
    parser.add_argument("--epochs", type=int, default=None,
                        help="Max training epochs (default: 100 for cold-start, auto for incremental)")
    parser.add_argument("--lr", type=float, default=None,
                        help="Learning rate (default: 0.0001 for cold-start, auto for incremental)")
    parser.add_argument("--hidden", type=int, default=HIDDEN_SIZE)
    parser.add_argument("--early-stop", type=int, default=EARLY_STOP)
    parser.add_argument("--gpu", type=int, default=-1, help="GPU ID (-1=CPU, 0=first GPU)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=str, default=None)

    # New arguments
    parser.add_argument("--mode", type=str, default="cold-start",
                        choices=["cold-start", "incremental", "new-features"],
                        help="Training mode: cold-start(冷启), incremental(追N天), new-features(新特征冷启)")
    parser.add_argument("--days", type=int, default=1,
                        help="Number of trading days to expand for incremental mode (default: 1)")
    parser.add_argument("--checkpoint", type=str, default=None,
                        help="Path to existing checkpoint (auto-detected in incremental mode)")
    parser.add_argument("--train-end", type=str, default=None,
                        help="Override training end date")
    parser.add_argument("--valid-start", type=str, default=None,
                        help="Override validation start date")
    parser.add_argument("--valid-end", type=str, default=None,
                        help="Override validation end date")
    parser.add_argument("--test-start", type=str, default=None,
                        help="Override test start date")
    parser.add_argument("--test-end", type=str, default=None,
                        help="Override test end date")

    args = parser.parse_args()

    output_dir = Path(args.output) if args.output else RESULT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # Concept data paths
    s2c_path = str(DATA_DIR / f"stock2concept_{args.market}.npy")
    si_path = str(DATA_DIR / f"stock_index_{args.market}.npy")

    if not os.path.exists(s2c_path) or not os.path.exists(si_path):
        print(f"ERROR: Concept data not found. Run first:")
        print(f"  python scripts/build_us_concept_data.py --market {args.market}")
        sys.exit(1)

    # Determine time windows based on mode
    if args.mode == "incremental":
        # Find checkpoint
        checkpoint_path = args.checkpoint
        if checkpoint_path is None:
            # Auto-detect from output dir
            default_ckpt = output_dir / "hist_us_best.pt"
            if default_ckpt.exists():
                checkpoint_path = str(default_ckpt)
            else:
                print(f"ERROR: No checkpoint found for incremental mode.")
                print(f"  Expected: {default_ckpt}")
                print(f"  Please run cold-start first, or specify --checkpoint path.")
                sys.exit(1)

        if not os.path.exists(checkpoint_path):
            print(f"ERROR: Checkpoint file not found: {checkpoint_path}")
            sys.exit(1)

        ckpt = load_checkpoint(checkpoint_path)
        if ckpt["format_version"] < 2:
            print(f"ERROR: Old-format checkpoint does not support incremental training.")
            print(f"  Please run cold-start first: python scripts/train_hist_us.py --mode cold-start")
            sys.exit(1)

        old_config = ckpt.get("config", {})
        if not old_config:
            print(f"ERROR: Checkpoint has no config metadata. Cannot compute incremental windows.")
            print(f"  Please run cold-start first with the updated script.")
            sys.exit(1)

        # Init qlib to get calendar for window computation
        qlib.init(provider_uri=QLIB_US_DATA, region=REG_US)
        calendar_list = D.calendar(freq="day")

        # Compute new windows
        windows = compute_incremental_windows(old_config, args.days, calendar_list)

        # Apply CLI overrides
        if args.train_end:
            windows["train_end"] = args.train_end
        if args.valid_start:
            windows["valid_start"] = args.valid_start
        if args.valid_end:
            windows["valid_end"] = args.valid_end
        if args.test_start:
            windows["test_start"] = args.test_start
        if args.test_end:
            windows["test_end"] = args.test_end

        # Compute incremental hyperparams
        ckpt_lr = old_config.get("lr", LR)
        final_epochs, final_lr = compute_incremental_hyperparams(
            ckpt_lr, args.days,
            explicit_epochs=args.epochs,
            explicit_lr=args.lr,
        )

        # Build training config
        training_config = {
            "train_start": windows["train_start"],
            "train_end": windows["train_end"],
            "valid_start": windows["valid_start"],
            "valid_end": windows["valid_end"],
            "test_start": windows["test_start"],
            "test_end": windows["test_end"],
            "d_feat": old_config.get("d_feat", D_FEAT),
            "hidden_size": old_config.get("hidden_size", HIDDEN_SIZE),
            "num_layers": old_config.get("num_layers", NUM_LAYERS),
            "dropout": old_config.get("dropout", DROPOUT),
            "lr": final_lr,
            "base_model": old_config.get("base_model", BASE_MODEL),
        }

    else:
        # cold-start or new-features: use default windows
        checkpoint_path = None
        windows = {
            "train_start": TRAIN_START,
            "train_end": args.train_end or TRAIN_END,
            "valid_start": args.valid_start or VALID_START,
            "valid_end": args.valid_end or VALID_END,
            "test_start": args.test_start or TEST_START,
            "test_end": args.test_end or TEST_END,
        }
        final_epochs = args.epochs or N_EPOCHS
        final_lr = args.lr or LR

        training_config = {
            "train_start": windows["train_start"],
            "train_end": windows["train_end"],
            "valid_start": windows["valid_start"],
            "valid_end": windows["valid_end"],
            "test_start": windows["test_start"],
            "test_end": windows["test_end"],
            "d_feat": D_FEAT,
            "hidden_size": args.hidden,
            "num_layers": NUM_LAYERS,
            "dropout": DROPOUT,
            "lr": final_lr,
            "base_model": BASE_MODEL,
        }

    # Print training plan
    print(f"\n{'='*70}")
    print(f"  HIST Model Training - US Stocks")
    print(f"  Mode: {args.mode}")
    print(f"  Market: {args.market} | Epochs: {final_epochs} | LR: {final_lr}")
    print(f"  Hidden: {args.hidden} | GPU: {args.gpu} | Seed: {args.seed}")
    if args.mode == "incremental":
        print(f"  Incremental: +{args.days} trading days")
        print(f"  Checkpoint: {checkpoint_path}")
    print(f"  Train: {windows['train_start']} ~ {windows['train_end']}")
    print(f"  Valid: {windows['valid_start']} ~ {windows['valid_end']}")
    print(f"  Test:  {windows['test_start']} ~ {windows['test_end']}")
    print(f"{'='*70}\n")

    # Step 1: Init Qlib (may already be initialized for incremental mode)
    print("[1/5] Initializing Qlib (US)...")
    if args.mode != "incremental":
        qlib.init(provider_uri=QLIB_US_DATA, region=REG_US)
    print(f"  Provider: {QLIB_US_DATA}")

    # Step 2: Build dataset with USAlpha360
    print("\n[2/5] Building dataset (USAlpha360, d_feat=5)...")

    handler = USAlpha360(
        instruments=args.market,
        start_time=windows["train_start"],
        end_time=windows["test_end"],
        fit_start_time=windows["train_start"],
        fit_end_time=windows["train_end"],
    )
    dataset = DatasetH(
        handler=handler,
        segments={
            "train": (windows["train_start"], windows["train_end"]),
            "valid": (windows["valid_start"], windows["valid_end"]),
            "test": (windows["test_start"], windows["test_end"]),
        },
    )

    # Verify feature count
    df_check = dataset.prepare("train", col_set="feature", data_key=DataHandlerLP.DK_L)
    n_features = df_check.shape[1]
    expected = training_config.get("d_feat", D_FEAT) * 60
    print(f"  Feature count: {n_features} (expected: {expected})")
    if n_features != expected:
        print(f"  WARNING: Feature count mismatch! Adjusting d_feat to {n_features // 60}")
        d_feat = n_features // 60
        training_config["d_feat"] = d_feat
    else:
        d_feat = training_config.get("d_feat", D_FEAT)
    print(f"  Train samples: {len(df_check)}")
    del df_check

    # Step 3: Load concept data info
    print("\n[3/5] Loading concept data...")
    s2c = np.load(s2c_path)
    si = np.load(si_path, allow_pickle=True).item()
    print(f"  stock2concept: {s2c.shape}")
    print(f"  stock_index: {len(si)} stocks")
    default_si = len(si) - 1  # Use last index as default

    # Step 4: Create and train model
    print(f"\n[4/5] Training HIST model...")
    model = CustomHIST(
        d_feat=d_feat,
        hidden_size=args.hidden,
        num_layers=NUM_LAYERS,
        dropout=DROPOUT,
        n_epochs=final_epochs,
        lr=final_lr,
        metric="ic",
        early_stop=args.early_stop,
        loss="mse",
        base_model=BASE_MODEL,
        stock2concept=s2c_path,
        stock_index=si_path,
        optimizer="adam",
        GPU=args.gpu,
        seed=args.seed,
        default_stock_index=default_si,
    )

    save_path = str(output_dir / "hist_us_best.pt")
    evals_result = {}
    best_epoch, best_score, evals_result = model.fit(
        dataset, evals_result, save_path,
        training_mode=args.mode,
        checkpoint_path=checkpoint_path,
        training_config=training_config,
    )

    # Step 5: Evaluate on test set
    print(f"\n[5/5] Evaluating on test set...")
    pred_series = model.predict(dataset, segment="test")
    eval_results = evaluate_predictions(pred_series, dataset)

    # Print results
    print(f"\n{'='*70}")
    print(f"  HIST US Training Results")
    print(f"{'='*70}")
    print(f"  Mode:             {args.mode}")
    print(f"  Best Epoch:       {best_epoch}")
    print(f"  Best Valid IC:    {best_score:.6f}")
    print(f"  ---")
    print(f"  Test IC:           {eval_results['IC_mean']:.6f} (std={eval_results['IC_std']:.4f})")
    print(f"  Test ICIR:         {eval_results['ICIR']:.4f}")
    print(f"  Test Rank IC:      {eval_results['RankIC_mean']:.6f} (std={eval_results['RankIC_std']:.4f})")
    print(f"  Test Rank ICIR:    {eval_results['RankICIR']:.4f}")
    print(f"  ---")
    print(f"  Long-Short Annual: {eval_results['long_short_return_annual']*100:.2f}%")
    print(f"  Long-Short Sharpe: {eval_results['long_short_sharpe']:.4f}")
    print(f"  ---")
    print(f"  Test Days:         {eval_results['num_days']}")
    print(f"  Test Samples:      {eval_results['num_samples']}")
    print(f"  ---")
    print(f"  Train: {windows['train_start']} ~ {windows['train_end']}")
    print(f"  Valid: {windows['valid_start']} ~ {windows['valid_end']}")
    print(f"  Test:  {windows['test_start']} ~ {windows['test_end']}")
    print(f"{'='*70}\n")

    # Save everything
    pred_series.to_pickle(str(output_dir / "predictions.pkl"))
    pd.Series(evals_result["train"]).to_csv(str(output_dir / "train_ic_history.csv"))
    pd.Series(evals_result["valid"]).to_csv(str(output_dir / "valid_ic_history.csv"))

    import json
    eval_results_serializable = {k: float(v) for k, v in eval_results.items()}
    eval_results_serializable["best_epoch"] = int(best_epoch)
    eval_results_serializable["best_valid_ic"] = float(best_score)
    eval_results_serializable["training_mode"] = args.mode
    eval_results_serializable["time_windows"] = windows
    with open(str(output_dir / "eval_results.json"), "w") as f:
        json.dump(eval_results_serializable, f, indent=2)

    with open(str(output_dir / "training_history.pkl"), "wb") as f:
        pickle.dump(evals_result, f)

    print(f"  Model:       {save_path}")
    print(f"  Predictions: {output_dir / 'predictions.pkl'}")
    print(f"  Results:     {output_dir / 'eval_results.json'}")
    print(f"\nDone!")


if __name__ == "__main__":
    main()
