# Phase 4 验证与后续工作清单

> 创建日期: 2026-05-04
> 前置条件: 数据更新 (PID 60894) 完成
> 数据更新内容: Yahoo Finance -> Qlib格式, 18531只美股, 2000-01-01 ~ 2026-05-02

---

## 一、数据更新完成确认

```bash
# 1. 确认进程已结束
ps aux | grep update_us_data | grep -v grep

# 2. 验证数据完整性
cd /Users/lailixiang/WorkSpace/QoderWorkspace/US_AI_Quant
source venv/bin/activate

python -c "
import qlib
from qlib.constant import REG_US
from qlib.data import D
qlib.init(provider_uri='~/.qlib/qlib_data/us_data', region=REG_US)
cal = D.calendar(freq='day')
print(f'Calendar: {cal[0]} ~ {cal[-1]} ({len(cal)} days)')
insts = D.instruments('all')
print(f'Instruments: {len(D.list_instruments(insts, as_list=True))} stocks')
# 验证SP500数据
sp500 = D.instruments('sp500')
sp500_list = D.list_instruments(sp500, as_list=True)
print(f'SP500: {len(sp500_list)} stocks')
"

# 3. 确认 concept data 已重建
ls -la data/hist/stock2concept_sp500.npy data/hist/stock_index_sp500.npy
```

---

## 二、Phase 4 Pipeline 验证 (ACT_18-22)

### 2.1 LightGBM Baseline 训练

```bash
# 预计耗时: 5-15 分钟
python scripts/train_lgbm_us.py --mode baseline --no-backtest

# 验收标准:
# - 训练成功完成, 生成 results/lgbm_us/pred.pkl
# - Test IC > 0.03, ICIR > 0.3
# - eval_results.json 生成
```

### 2.2 独立回测

```bash
# 预计耗时: 2-5 分钟
python scripts/backtest_us.py --pred-path results/lgbm_us/pred.pkl

# 验收标准:
# - 回测成功完成
# - 生成 backtest_report.json
# - Sharpe > 1.0
```

### 2.3 DoubleEnsemble 对比

```bash
# 预计耗时: 10-20 分钟
python scripts/train_lgbm_us.py --mode baseline --model densemble --no-backtest

# 对比 lgbm vs densemble 的 IC/ICIR
```

### 2.4 滚动训练

```bash
# 预计耗时: 30-60 分钟 (取决于窗口数量)
python scripts/rolling_train_us.py --step 20

# 验收标准:
# - 所有滚动窗口训练完成
# - rolling_ic_timeline.csv 生成
# - 月度IC趋势合理
```

### 2.5 端到端 Pipeline

```bash
# 预计耗时: 20-40 分钟
python scripts/run_pipeline_us.py --steps all

# 验收标准:
# - train + backtest + signal 全部成功
# - 生成 results/pipeline/signals/signal_YYYYMMDD.json
```

### 2.6 MLflow 实验查看

```bash
# 启动 MLflow UI
mlflow ui --port 5000 --backend-store-uri sqlite:///mlruns.db

# 浏览器访问 http://localhost:5000
# 确认实验可浏览, 指标记录正确
```

---

## 三、HIST 模型冷启训练 (新数据)

> 注意: 需要连接 AutoDL GPU 服务器. 操作前必须先确认用户已开启 AutoDL 实例.

### 3.1 本地 CPU 快速测试 (可选)

```bash
# 确认新数据下 HIST 可正常运行 (仅2个epoch, 验证数据兼容性)
python scripts/train_hist_us.py --mode cold-start --gpu -1 --epochs 2 \
    --output results/hist_us_test_newdata/
```

### 3.2 AutoDL GPU 训练

```bash
# 1. 确认 AutoDL 实例已开启 (需用户确认)
# 2. 上传新的 concept data 和脚本
# 3. 执行 cold-start 训练
python scripts/train_hist_us.py --mode cold-start --gpu 0

# 预期时间: 10-30 分钟 (AutoDL GPU)
# 验收标准: Test IC > 0.02, 与旧模型对比提升
```

---

## 四、后续工作总览

### 4.1 Phase 4 收尾
- [ ] 运行验证命令 (上述 2.1-2.6)
- [ ] HIST 新数据冷启训练
- [ ] 对比分析: LightGBM vs DEnsemble vs HIST
- [ ] 编写 Phase 4 验证总结 (review_18_to_22.md)
- [ ] Hyperparameter Grid Search (可选, `--tune` 参数)

### 4.2 Phase 5 规划 (信号执行与风控)
- [ ] ACT_23: 信号解析与执行器 (SignalExecutor)
- [ ] ACT_24: 仓位管理器 (PortfolioManager)
- [ ] ACT_25: 风控引擎 (RiskEngine)
- [ ] ACT_26: 调度器与定时任务
- [ ] ACT_27: Phase 5 端到端验证

### 4.3 已知技术债务
- [ ] Enhanced mode (Alpha158 + custom factors) 需要自定义 DataHandler 子类
- [ ] Survivorship Bias 处理方案 (已记录在 memory, 待 Phase 5/6 迭代)
- [ ] Grid Search 仅支持 LightGBM, DEnsemble 暂不支持调参

---

## 五、关键文件索引

| 文件 | 说明 |
|------|------|
| `scripts/train_lgbm_us.py` | LightGBM/DEnsemble 训练脚本 |
| `scripts/backtest_us.py` | 独立回测引擎 |
| `scripts/rolling_train_us.py` | 滚动训练 (RollingGen) |
| `scripts/run_pipeline_us.py` | 端到端 Pipeline |
| `scripts/train_hist_us.py` | HIST 模型训练 |
| `scripts/update_us_data.py` | 数据更新脚本 (Yahoo Finance) |
| `src/research/workflow/experiment_manager.py` | MLflow 实验管理封装 |
| `src/research/factors/alpha158_config.py` | Alpha158 配置 |
| `configs/qlib/workflow_config_lightgbm_us.yaml` | LightGBM workflow YAML |
| `docs/phase4_alpha_pipeline/hist_training_manual.md` | HIST 训练使用手册 |

---

## 六、运行环境备注

- Python: venv (`source venv/bin/activate`)
- Qlib数据: `~/.qlib/qlib_data/us_data`
- MLflow: `sqlite:///mlruns.db` (项目根目录)
- AutoDL: 需用户确认开机后才可连接 (SSH)
