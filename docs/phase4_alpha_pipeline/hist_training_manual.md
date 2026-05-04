# HIST 模型训练使用手册

> US 美股 HIST 模型的数据更新、冷启动、增量训练 (追N天)、新特征冷启 完整操作指南。

## 0. 前置条件

- Python venv 环境: `US_AI_Quant/venv/bin/python` (本地数据更新)
- Qlib 数据目录: `~/.qlib/qlib_data/us_data/`
- Qlib 源码目录: `~/WorkSpace/QoderWorkspace/qlib/scripts/` (用于数据更新)
- Concept 数据: `data/hist/stock2concept_sp500.npy`, `data/hist/stock_index_sp500.npy`
- 所有命令均在项目根目录 `US_AI_Quant/` 下执行

**训练环境**: 推荐使用 AutoDL GPU (RTX 4090)，训练速度约为 CPU 的 9 倍。
连接 AutoDL 前请先确认实例已开机，未使用时应关机以节省费用。

**本地数据更新**: 数据更新脚本在本地 Mac 运行，必须使用 venv Python:
```bash
cd ~/WorkSpace/QoderWorkspace/US_AI_Quant
PYTHON=venv/bin/python
```

---

## 1. 口令速查表

| 口令 | 含义 | 命令 |
|------|------|------|
| **更新数据** | 拉取最新美股行情到 Qlib 数据库 | `$PYTHON scripts/update_us_data.py` |
| **冷启** | 从零训练模型 (全量数据) | `$PYTHON scripts/train_hist_us.py --mode cold-start --gpu 0` |
| **追1天** | 增量训练扩展1个交易日 | `$PYTHON scripts/train_hist_us.py --mode incremental --days 1 --gpu 0` |
| **追N天** | 增量训练扩展N个交易日 | `$PYTHON scripts/train_hist_us.py --mode incremental --days N --gpu 0` |
| **新特征冷启** | 新增 alpha 因子后全量重训 | `$PYTHON scripts/train_hist_us.py --mode new-features --gpu 0` |

> GPU 参数: `--gpu 0` 使用 GPU (推荐, AutoDL), `--gpu -1` 使用 CPU (本地 Mac, 较慢)

---

## 2. 数据更新 (更新数据)

### 2.1 更新到最新日期
```bash
$PYTHON scripts/update_us_data.py
```
默认更新到明天的日期 (开区间)，即包含今天的数据。

### 2.2 更新到指定日期
```bash
$PYTHON scripts/update_us_data.py --end-date 2026-05-02
```

### 2.3 更新并重建 concept 矩阵
```bash
$PYTHON scripts/update_us_data.py --end-date 2026-05-02 --rebuild-concept
```
如果 SP500 成分股变动较大 (季度调整后)，建议加 `--rebuild-concept`。

### 2.4 试运行 (不执行)
```bash
$PYTHON scripts/update_us_data.py --dry-run
```

### 2.5 参数说明
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--end-date` | 明天 | 数据更新的截止日期 (开区间) |
| `--qlib-dir` | `~/.qlib/qlib_data/us_data` | Qlib 数据目录 |
| `--delay` | 1.0 | Yahoo API 调用间隔 (秒) |
| `--rebuild-concept` | false | 更新后重建 stock2concept 矩阵 |
| `--market` | sp500 | concept 重建的市场 |
| `--dry-run` | false | 只显示计划，不执行 |

### 2.6 耗时参考
- 追1天: ~2-5 分钟
- 追1周: ~5-10 分钟
- 跨年 (5+ 年缺口): ~30-60 分钟 (含 863 只股票下载)

---

## 3. 冷启动 (冷启)

从零开始训练 HIST 模型，使用全量历史数据。

### 3.1 默认配置 (推荐首次使用)
```bash
$PYTHON scripts/train_hist_us.py --mode cold-start --gpu 0
```
默认时间窗口:
- 训练集: 2008-01-01 ~ 2023-12-31
- 验证集: 2024-01-01 ~ 2025-12-31
- 测试集: 2026-01-01 ~ 2026-05-01

默认超参: epochs=100, lr=0.0001, hidden=64, early_stop=15

### 3.2 自定义时间窗口
```bash
$PYTHON scripts/train_hist_us.py --mode cold-start --gpu 0 \
    --train-end 2024-06-30 \
    --valid-start 2024-07-01 --valid-end 2025-06-30 \
    --test-start 2025-07-01 --test-end 2026-05-01
```
注意: train_start 固定为 2008-01-01，不可修改。

### 3.3 本地 CPU 训练 (Mac)
```bash
$PYTHON scripts/train_hist_us.py --mode cold-start --gpu -1 --epochs 20
```
CPU 训练较慢 (每 epoch ~400s vs GPU ~46s)，建议减少 epochs 或使用 AutoDL。

### 3.4 AutoDL GPU 训练
```bash
# 在 AutoDL 上
python scripts/train_hist_us.py --mode cold-start --gpu 0
```
在 AutoDL 上直接用系统 Python 即可 (已安装所有依赖)。

### 3.5 输出文件
| 文件 | 说明 |
|------|------|
| `results/hist_us/hist_us_best.pt` | 模型 checkpoint (v2 格式，含 optimizer state + config) |
| `results/hist_us/eval_results.json` | 测试集评估指标 (IC, ICIR, 多空收益等) |
| `results/hist_us/predictions.pkl` | 测试集预测分数 |
| `results/hist_us/train_ic_history.csv` | 训练 IC 曲线 |
| `results/hist_us/valid_ic_history.csv` | 验证 IC 曲线 |

---

## 4. 增量训练 (追1天 / 追N天)

在已有 checkpoint 基础上，扩展训练窗口继续微调模型。

### 4.1 前提条件
- 必须先执行过一次**冷启**，生成 v2 格式的 checkpoint
- 旧的 AutoDL checkpoint (v1 格式) 不支持增量训练，需重新冷启

### 4.2 追1天
```bash
# 先更新数据
$PYTHON scripts/update_us_data.py

# 再增量训练
$PYTHON scripts/train_hist_us.py --mode incremental --days 1 --gpu 0
```
自动计算: epochs=5, lr=原始lr*0.1

### 4.3 追N天
```bash
$PYTHON scripts/train_hist_us.py --mode incremental --days 5 --gpu 0
```
自动计算: epochs=min(20, N), lr=原始lr*0.5

### 4.4 手动指定超参 (覆盖自动值)
```bash
$PYTHON scripts/train_hist_us.py --mode incremental --days 5 \
    --epochs 30 --lr 0.00005 --gpu 0
```
`--epochs` 和 `--lr` 可单独或同时指定，未指定的用自动值。

### 4.5 窗口扩展策略 (扩展窗口)
增量训练使用**扩展窗口**策略:
- `train_start` 固定不动 (2008-01-01)
- `train_end` 向后推 N 个交易日
- `valid_start`/`valid_end` 同步向后推 N 个交易日
- `test_start` 紧跟 valid_end 之后，`test_end` 取日历末尾

示例: 追5天后，原窗口 → 新窗口:
```
Train: 2008-01-01 ~ 2023-12-31  →  2008-01-01 ~ 2024-01-08
Valid: 2024-01-01 ~ 2025-12-31  →  2024-01-08 ~ 2026-01-07
Test:  2026-01-01 ~ 2026-05-01  →  2026-01-08 ~ (日历末尾)
```

### 4.6 自动超参策略
| 条件 | epochs | lr |
|------|--------|----|
| days == 1 | 5 | checkpoint_lr * 0.1 |
| days > 1 | min(20, N) | checkpoint_lr * 0.5 |
| 手动指定 --epochs | 使用指定值 | 不影响 lr |
| 手动指定 --lr | 不影响 epochs | 使用指定值 |

---

## 5. 新特征冷启 (新特征冷启)

当新增了 alpha 因子/特征后，需要全量重训模型。

### 5.1 标准流程
1. 修改 `src/research/model/us_alpha_handler.py` 添加新特征
2. 执行新特征冷启:
```bash
$PYTHON scripts/train_hist_us.py --mode new-features --gpu 0
```

### 5.2 注意事项
- 新特征冷启等同于冷启，但语义上标记为 "new-features" 便于追踪
- 如果 d_feat 发生变化 (如从 5 变为 6)，脚本会自动检测并调整
- checkpoint 中会记录 training_mode="new-features"

---

## 6. Checkpoint 格式说明

### v2 格式 (新版，支持增量训练)
```python
{
    "format_version": 2,
    "model_state_dict": OrderedDict,   # 模型权重
    "optimizer_state_dict": dict,       # Adam 优化器状态 (含动量)
    "epoch": int,                       # 最佳 epoch
    "best_score": float,                # 最佳验证 IC
    "training_mode": str,               # "cold-start" / "incremental" / "new-features"
    "config": {                         # 训练配置 (时间窗口, 超参)
        "train_start", "train_end",
        "valid_start", "valid_end",
        "test_start", "test_end",
        "d_feat", "hidden_size", "lr", ...
    },
    "training_history": {               # 完整训练历史 (含历史增量)
        "train": [ic1, ic2, ...],
        "valid": [ic1, ic2, ...]
    },
    "timestamp": str
}
```

### v1 格式 (旧版 AutoDL，仅含模型权重)
```python
OrderedDict({
    "rnn.weight_ih_l0": Tensor,
    "rnn.weight_hh_l0": Tensor,
    ...
})
```
v1 格式不支持增量训练，需先冷启生成 v2 checkpoint。

---

## 7. 常见操作流程

### 7.1 日更流程 (每个交易日收盘后)
```bash
# 1. 本地更新数据
$PYTHON scripts/update_us_data.py

# 2. 上传数据到 AutoDL (确认 AutoDL 已开机)
# 3. 在 AutoDL 上追1天
python scripts/train_hist_us.py --mode incremental --days 1 --gpu 0
# 4. 训练完成后，下载 checkpoint 到本地，关闭 AutoDL
```

### 7.2 周更流程 (每周末)
```bash
# 1. 本地更新数据
$PYTHON scripts/update_us_data.py

# 2. 在 AutoDL 上追5天
python scripts/train_hist_us.py --mode incremental --days 5 --gpu 0
```

### 7.3 首次部署 / 完整重训
```bash
# 1. 本地确保数据已更新到最新
$PYTHON scripts/update_us_data.py

# 2. 在 AutoDL 上冷启动
python scripts/train_hist_us.py --mode cold-start --gpu 0
```

### 7.4 新增因子后
```bash
# 1. 修改 us_alpha_handler.py 添加新因子
# 2. 新特征冷启
$PYTHON scripts/train_hist_us.py --mode new-features --gpu 0
```

---

## 8. 关键指标解读

| 指标 | 含义 | 参考水位 |
|------|------|----------|
| IC (mean) | 预测分与实际收益的截面 Pearson 相关 | >0.03 良好, >0.05 优秀 (A股); 美股偏低 |
| ICIR | IC 均值 / IC 标准差 | >0.5 较好 |
| Rank IC | 预测排名与实际排名的 Spearman 相关 | 比 IC 更稳定 |
| Long-Short Sharpe | 多空对冲年化夏普比 | >0.5 可用, >1.0 优秀 |

历史参考值 (AutoDL 训练, 2018-2020 测试集):
- Valid IC: 0.0116
- Test IC: 0.0053
- Long-Short Sharpe: 0.6074

---

## 9. 错误排查

### "旧版checkpoint不支持增量训练"
```
ERROR: Old-format checkpoint does not support incremental training.
```
**解决**: 先执行一次冷启生成 v2 checkpoint:
```bash
$PYTHON scripts/train_hist_us.py --mode cold-start --gpu 0
```

### "Checkpoint file not found"
```
ERROR: Checkpoint file not found: results/hist_us/hist_us_best.pt
```
**解决**: 同上，先冷启。增量模式需要先有 checkpoint。

### "Concept data not found"
```
ERROR: Concept data not found. Run first:
  python scripts/build_us_concept_data.py --market sp500
```
**解决**: 执行 concept 构建脚本或使用 `--rebuild-concept` 参数更新数据。

### "Empty data from dataset"
数据不够或时间窗口超出 Qlib 数据范围。先更新数据:
```bash
$PYTHON scripts/update_us_data.py
```

### CatBoostModel 警告
```
ModuleNotFoundError. CatBoostModel are skipped.
```
这是无害警告，可以忽略。Qlib 在导入时尝试加载 CatBoost，未安装不影响功能。

---

## 10. 文件结构

```
US_AI_Quant/
├── scripts/
│   ├── train_hist_us.py          # 训练脚本 (冷启/增量/新特征)
│   ├── update_us_data.py         # 数据更新脚本
│   └── build_us_concept_data.py  # Concept 矩阵构建
├── src/research/model/
│   └── us_alpha_handler.py       # USAlpha360 特征工程 (5字段 x 60天 = 300维)
├── data/hist/
│   ├── stock2concept_sp500.npy   # 股票→行业 one-hot 矩阵 (745x11)
│   └── stock_index_sp500.npy     # 股票名→索引映射
├── results/hist_us/
│   ├── hist_us_best.pt           # 模型 checkpoint
│   ├── eval_results.json         # 评估结果
│   └── ...
└── ~/.qlib/qlib_data/us_data/    # Qlib 数据 (行情/日历/成分股)
```

---

## 11. 完整参数参考

### train_hist_us.py
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `--mode` | str | cold-start | 训练模式: cold-start, incremental, new-features |
| `--days` | int | 1 | 增量模式扩展天数 |
| `--checkpoint` | str | auto | checkpoint 路径 (增量模式自动检测) |
| `--epochs` | int | auto | 最大训练轮数 (冷启=100, 增量=自动) |
| `--lr` | float | auto | 学习率 (冷启=0.0001, 增量=自动) |
| `--hidden` | int | 64 | 隐藏层大小 |
| `--early-stop` | int | 15 | 早停耐心值 |
| `--gpu` | int | -1 | GPU ID (-1=CPU, 0=first GPU, 推荐 AutoDL 用 0) |
| `--seed` | int | 42 | 随机种子 |
| `--market` | str | sp500 | 市场 |
| `--output` | str | results/hist_us | 输出目录 |
| `--train-end` | str | 2023-12-31 | 训练集结束日期 (覆盖) |
| `--valid-start` | str | 2024-01-01 | 验证集开始日期 (覆盖) |
| `--valid-end` | str | 2025-12-31 | 验证集结束日期 (覆盖) |
| `--test-start` | str | 2026-01-01 | 测试集开始日期 (覆盖) |
| `--test-end` | str | 2026-05-01 | 测试集结束日期 (覆盖) |
