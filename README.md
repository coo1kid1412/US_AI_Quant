# US_AI_Quant - 美股AI量化交易系统

> 基于 Qlib Alpha Pipeline + RD-Agent 自动化研究 + 富途OpenAPI 的系统化量化交易平台

## ⚠️ 安全警告（最高优先级）

**🔴 严禁实盘交易禁令**

> **在pipeline完全跑通、且经用户明确书面确认之前，严禁接入富途app进行「实盘」买入卖出等具体股票动作的操作。**
> 
> - 所有交易操作**必须**在模拟环境（`env='simulate'`）下进行
> - 严禁任何形式的自动实盘下单
> - 严禁修改交易环境为 `env='real'` 除非用户明确要求
> - 此禁令适用于所有代码、脚本、自动化流程
> - **违反此禁令将导致严重财务风险**

**当前阶段：虚拟盘测试**
- ✅ 允许：模拟环境行情获取
- ✅ 允许：模拟环境下单、撤单
- ❌ 禁止：实盘环境任何交易操作

---

## 项目简介

本项目旨在构建一个系统化的美股量化交易系统，核心架构：
- **Qlib Alpha Pipeline**: 因子工程 → 模型训练 → 滚动回测 → 信号生成
- **富途OpenAPI**: 准实时美股程序化交易（信号执行、仓位管理）
- **RD-Agent**: LLM驱动的自动化因子挖掘与模型迭代
- **风控引擎**: 回撤控制、集中度限制、止损机制

## 环境状态

### ✅ 已完成 (Phase 1)

- [x] Xcode Command Line Tools
- [x] Homebrew包管理器
- [x] 系统依赖库 (HDF5, libomp)
- [x] Python 3.11虚拟环境
- [x] 核心Python依赖安装

### 已安装库版本

| 库 | 版本 |
|---|------|
| Qlib | 0.9.7 |
| 富途API | 10.04.6408 |
| PyTorch | 2.2.2 |
| LightGBM | 4.6.0 |
| XGBoost | 3.2.0 |
| YFinance | 1.3.0 |
| Pandas | 2.3.3 |
| NumPy | 1.26.4 |
| protobuf | 5.29.6 |
| cvxpy | 1.6.7 |

## 快速开始

### 1. 激活虚拟环境

```bash
cd /Users/lailixiang/WorkSpace/QoderWorkspace/US_AI_Quant
source venv/bin/activate
```

### 2. 验证安装

```bash
python -c "import qlib; import futu; import torch; print('✅ All libraries OK')"
```

### 3. 下一步

查看 [PROJECT_PLAN.md](PROJECT_PLAN.md) 了解完整实施路线。

## 项目结构

```
US_AI_Quant/
├── docs/                    # 文档（需求+Review）
│   ├── phase1_env_setup/   # Phase 1文档
│   ├── phase2_qlib_setup/  # Phase 2文档
│   └── ...
├── src/                    # 源代码
├── tests/                  # 测试代码
├── configs/                # 配置文件
├── notebooks/              # Jupyter笔记
├── results/                # 结果输出
├── logs/                   # 日志
├── venv/                   # Python虚拟环境
├── PROJECT_PLAN.md         # 项目计划
├── requirements.txt        # 依赖清单
└── .env.example            # 环境变量模板
```

## 当前进度

### ✅ Phase 1: 环境准备（完成）
- [x] Xcode Command Line Tools
- [x] Homebrew包管理器
- [x] 系统依赖库 (HDF5, libomp)
- [x] Python 3.11虚拟环境
- [x] 核心Python依赖安装

### ✅ Phase 2: Qlib部署与美股数据（完成）
- [x] Qlib框架安装
- [x] 美股数据下载（1.2GB, ~9000只股票）
- [x] 数据完整性验证
- [x] LightGBM示例Workflow
- [x] Mac OS兼容性验证

### ✅ Phase 3: 富途OpenAPI集成（完成）
- [x] futu-api SDK安装验证
- [x] OpenD网关配置并成功连接（无加密模式）
- [x] FutuBroker封装类实现
- [x] 行情测试通过（快照/K线/订阅）
- [x] 模拟交易测试通过（账户查询/持仓查询）
- [x] 单元测试9/9通过
- [x] 集成测试通过（OpenD在线时）

### Phase 4: Qlib Alpha Pipeline（进行中）
- [x] ACT_16: Alpha因子库建设 (Alpha158 + 14 custom factors)
- [x] ACT_17: HIST模型训练 (IC=0.0209, Sharpe=1.2324)
- [x] ACT_18+19+20+21: Pipeline脚本开发（代码完成，待数据验证）
  - `scripts/train_lgbm_us.py` - LightGBM/DEnsemble训练
  - `scripts/backtest_us.py` - 独立回测引擎
  - `scripts/rolling_train_us.py` - RollingGen滚动训练
  - `scripts/run_pipeline_us.py` - 端到端Pipeline
  - `src/research/workflow/experiment_manager.py` - MLflow实验管理
- [ ] ACT_22: Phase 4 端到端验证（等待数据更新完成）

### Phase 5-7: 待启动
- [ ] Phase 5: 信号执行与风控引擎（FutuBroker执行、仓位管理、风控）
- [ ] Phase 6: RD-Agent自动化研究（因子挖掘、模型迭代、协同优化）
- [ ] Phase 7: 全链路仿真与持续优化（模拟盘运行、监控、实盘准备）

## 重要提示

- **Python虚拟环境**: 每次开发前激活 `venv`
- **环境变量**: 复制 `.env.example` 为 `.env` 并填写真实值
- **富途OpenD**: 确保富途客户端已启动并OpenD运行

## 技术栈

- **语言**: Python 3.11
- **量化框架**: Qlib 0.9.7
- **券商API**: 富途OpenAPI
- **机器学习**: PyTorch, LightGBM, XGBoost
- **实验管理**: MLflow 3.11
- **数据源**: Yahoo Finance (yfinance)
- **系统**: macOS Intel x86_64

---

**创建日期**: 2026-05-02
**最后更新**: 2026-05-04
**状态**: Phase 3 完成 | Phase 4 代码完成(待验证) | 数据更新中 | 交易环境: 仅限模拟盘(实盘禁令生效中)
