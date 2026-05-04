#!/usr/bin/env python3
"""
AutoDL GPU训练入口 - US HIST模型
================================
在AutoDL实例上运行, 自动检测GPU并启动训练。

用法:
  python autodl_train_us.py --epochs 100 --gpu 0
  python autodl_train_us.py --epochs 200 --lr 0.0001 --hidden 128
"""
import os
import sys
import argparse
import subprocess
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent


def check_environment():
    """验证运行环境"""
    import torch
    import numpy as np

    print("\n[环境检查]")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  torch:  {torch.__version__}")
    print(f"  numpy:  {np.__version__}")

    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"  GPU:    {gpu_name} ({gpu_mem:.1f} GB)")
        return 0  # GPU ID
    else:
        print("  GPU:    不可用, 使用CPU")
        return -1


def check_data():
    """验证数据文件"""
    us_data = Path.home() / ".qlib" / "qlib_data" / "us_data"
    concept_dir = PROJECT_DIR / "data" / "hist"

    print("\n[数据检查]")
    if not us_data.exists():
        print(f"  ERROR: US数据不存在: {us_data}")
        sys.exit(1)
    print(f"  US数据: {us_data}")

    s2c = concept_dir / "stock2concept_sp500.npy"
    si = concept_dir / "stock_index_sp500.npy"
    if not s2c.exists() or not si.exists():
        print(f"  ERROR: 概念数据不存在: {concept_dir}")
        sys.exit(1)
    print(f"  概念数据: OK")


def run_training(args, gpu_id):
    """运行训练脚本"""
    gpu = args.gpu if args.gpu is not None else gpu_id

    cmd = [
        sys.executable,
        str(PROJECT_DIR / "scripts" / "train_hist_us.py"),
        "--market", args.market,
        "--epochs", str(args.epochs),
        "--lr", str(args.lr),
        "--hidden", str(args.hidden),
        "--early-stop", str(args.early_stop),
        "--gpu", str(gpu),
        "--seed", str(args.seed),
        "--output", str(PROJECT_DIR / "results" / "hist_us"),
    ]

    print(f"\n{'='*60}")
    print(f"  US HIST Model Training (AutoDL)")
    print(f"{'='*60}")
    print(f"  Market:     {args.market}")
    print(f"  Epochs:     {args.epochs}")
    print(f"  LR:         {args.lr}")
    print(f"  Hidden:     {args.hidden}")
    print(f"  Early Stop: {args.early_stop}")
    print(f"  GPU:        {gpu}")
    print(f"  Seed:       {args.seed}")
    print(f"{'='*60}\n")

    result = subprocess.run(cmd, cwd=str(PROJECT_DIR))

    if result.returncode == 0:
        print(f"\n{'='*60}")
        print(f"  训练完成!")
        print(f"{'='*60}")
        print(f"  模型: results/hist_us/hist_us_best.pt")
        print(f"  结果: results/hist_us/eval_results.json")
        print(f"\n  下载到本地Mac:")
        print(f'  scp -P <端口> root@<IP>:/root/hist_us_train/results/hist_us/* \\')
        print(f'      ~/WorkSpace/QoderWorkspace/US_AI_Quant/results/hist_us/')
        print(f"\n  ⚠️  记得关机!")
    else:
        print(f"\n  训练失败 (exit code: {result.returncode})")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="AutoDL US HIST Training")
    parser.add_argument("--market", default="sp500")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--lr", type=float, default=0.0001)
    parser.add_argument("--hidden", type=int, default=64)
    parser.add_argument("--early-stop", type=int, default=15)
    parser.add_argument("--gpu", type=int, default=None, help="GPU ID (auto-detect if not set)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    gpu_id = check_environment()
    check_data()
    run_training(args, gpu_id)


if __name__ == "__main__":
    main()
