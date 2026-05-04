# US_AI_Quant 项目计划（修订版 v2.0）

> 项目名称：美股AI量化交易系统
> 启动日期：2026-05-02
> 最后更新：2026-05-04
> 修订说明：移除TradingAgents集成，重新聚焦于 **Qlib Alpha Pipeline + RD-Agent 自动化研究** 范式

---

## 安全警告（最高优先级）

**严禁实盘交易禁令**

> **在pipeline完全跑通、且经用户明确书面确认之前，严禁接入富途app进行「实盘」买入卖出等具体股票动作的操作。**
> 
> - 所有交易操作**必须**在模拟环境（`env='simulate'`）下进行
> - 严禁任何形式的自动实盘下单
> - 严禁修改交易环境为 `env='real'` 除非用户明确要求
> - 此禁令适用于所有代码、脚本、自动化流程
> - **违反此禁令将导致严重财务风险**

**当前阶段：虚拟盘测试**
- 允许：模拟环境行情获取
- 允许：模拟环境下单、撤单
- 禁止：实盘环境任何交易操作

---

## 项目愿景与目标

### 核心目标
通过 Qlib + RD-Agent 范式，构建系统化的美股量化交易Pipeline，实现：
1. **因子挖掘** — 自动化发现有效的Alpha因子
2. **因子组合** — 通过机器学习模型融合多因子信号
3. **模型迭代** — 滚动训练 + RD-Agent自动优化
4. **准实时交易** — 通过富途OpenAPI执行交易信号
5. **风险控制** — 最大回撤控制在10%以内

### 收益目标
- **年化收益**: 30%（Sharpe Ratio ≈ 2.0-2.5）
- **最大回撤**: ≤ 10%
- **Calmar Ratio**: ≥ 3.0

> **现实预期说明**：30%年化 + 10%最大回撤意味着 Calmar Ratio ≈ 3.0，这在量化领域属于
> 较高水准。作为参考，Renaissance Technologies的Medallion基金年化约66%，但大多数优秀
> 量化基金的年化在15%-25%之间。我们的目标具有挑战性但并非不可实现，关键在于：
> (1) 持续的因子创新避免Alpha衰减，(2) 严格的风控纪律，(3) 足够分散的持仓。

### 技术架构总览

```
┌─────────────────────────────────────────────────────────┐
│                    RD-Agent 自动化研究                     │
│  (因子假设生成 → 代码实现 → 回测验证 → 知识积累)            │
└────────────────────────┬────────────────────────────────┘
                         │ 新因子 / 新模型
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    Qlib Alpha Pipeline                   │
│                                                         │
│  数据层 ──→ 因子层 ──→ 模型层 ──→ 信号层 ──→ 组合层       │
│  (行情数据)  (Alpha158+)  (LightGBM   (排序/评分)  (TopK    │
│              (自定义因子)   DoubleEns.)              选股)   │
│                                                         │
│  ◄──── 滚动训练 (RollingGen: 每月重训) ────►             │
└────────────────────────┬────────────────────────────────┘
                         │ 交易信号 (买入/卖出/持仓)
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  信号执行与风控引擎                        │
│                                                         │
│  信号解析 → 仓位计算 → 风控检查 → FutuBroker下单          │
│              (等权/风险平价)  (回撤/集中度)  (模拟盘)        │
└─────────────────────────────────────────────────────────┘
```

---

## 量化交易核心概念（教育模块）

> 本节为量化交易的核心概念解释，帮助理解后续各Phase的设计逻辑。

### 1. 什么是Alpha因子？

**Alpha因子**是用来预测股票未来收益的特征信号。每个因子是一个从市场数据中提取的数值指标。

**常见因子类别**：
| 类别 | 示例 | 直觉解释 |
|------|------|----------|
| 动量因子 | 过去20天收益率 | "涨的还会涨" — 趋势延续 |
| 反转因子 | 过去5天收益率(取反) | "跌多了会反弹" — 均值回归 |
| 波动率因子 | 20日收益率标准差 | 低波动股票长期跑赢高波动 |
| 流动性因子 | 平均换手率 | 低流动性股票有溢价 |
| 价值因子 | 市盈率倒数 | 便宜的股票长期跑赢贵的 |
| 质量因子 | ROE、利润增长率 | 好公司股价终究会反映基本面 |

**Qlib的因子表达式引擎**（核心优势）：
```python
# Qlib允许用类似Excel公式的方式定义因子
# 示例：20日动量因子
"Ref($close, -20) / $close - 1"

# 示例：成交量加权价格偏离
"($close - Mean($close * $volume, 10) / Mean($volume, 10)) / Std($close, 10)"

# Alpha158包含158个预定义因子，Alpha360包含360个
# 涵盖了KBAR(K线)、PRICE(价格)、VOLUME(成交量)、VWAP(加权均价)等维度
```

### 2. 如何评估因子好坏？

| 指标 | 公式含义 | 判断标准 |
|------|----------|----------|
| **IC** (Information Coefficient) | 因子值与下期收益的相关系数 | \|IC\| > 0.03 即有意义 |
| **ICIR** (IC Information Ratio) | IC均值 / IC标准差 | ICIR > 0.5 算优秀 |
| **Rank IC** | 因子排名与收益排名的相关系数 | 比IC更稳健，推荐使用 |
| **因子换手率** | 因子值排名变化程度 | 太高意味着交易成本大 |
| **因子衰减** | IC随持有期的变化 | 好因子的IC应缓慢衰减 |

> **实操意义**：单个因子的IC通常在0.02-0.08之间。真正的Alpha来自**组合**多个弱相关的因子。
> 这就是为什么我们需要机器学习模型（LightGBM等）来学习因子之间的非线性组合关系。

### 3. 什么是回测？为什么重要？

**回测**（Backtesting）是用历史数据模拟策略执行，评估策略在过去会获得怎样的收益。

**回测的关键指标**：
| 指标 | 含义 | 目标值 |
|------|------|--------|
| **年化收益率** (Annualized Return) | 每年平均赚多少 | ≥ 30% |
| **最大回撤** (Max Drawdown) | 从最高点到最低点的最大跌幅 | ≤ 10% |
| **Sharpe Ratio** | (收益 - 无风险利率) / 波动率 | ≥ 2.0 |
| **Calmar Ratio** | 年化收益 / 最大回撤 | ≥ 3.0 |
| **胜率** (Win Rate) | 盈利交易占比 | ≥ 55% |
| **盈亏比** (Profit Factor) | 总盈利 / 总亏损 | ≥ 1.5 |
| **换手率** (Turnover) | 每期调仓比例 | 需要权衡收益vs交易成本 |

**回测的三大陷阱**（必须避免）：
1. **前视偏差** (Look-ahead Bias)：用了未来才能知道的信息。例如用当天收盘价做当天的交易决策。
   - 解决：Qlib的 `handler` 会自动对齐时间，但自定义因子需要注意。
2. **幸存者偏差** (Survivorship Bias)：只用现在还存在的股票做回测，忽略已退市的股票。
   - 解决：Qlib的美股数据包含已退市股票。
3. **过拟合** (Overfitting)：策略在历史数据上表现好但实盘不行。
   - 解决：使用**滚动训练** (Walk-forward)，严格分离训练集/验证集/测试集。

### 4. 什么是滚动训练？

**滚动训练**（Rolling Training / Walk-Forward）是量化策略的标准做法：

```
时间线 ──────────────────────────────────────────────►

窗口1: [====训练集====][==验证集==][测试集]
窗口2:    [====训练集====][==验证集==][测试集]
窗口3:       [====训练集====][==验证集==][测试集]
                                            ...

每个窗口：
- 训练集：用来训练模型（比如过去3年的数据）
- 验证集：用来调参和早停（比如接下来6个月）
- 测试集：用来评估真实表现（比如接下来1个月）
- 然后窗口向前滚动，用新数据重新训练
```

**为什么必须滚动训练？**
- 市场在变化，去年有效的因子今年可能失效（Alpha衰减）
- 模型需要不断用最新数据更新
- Qlib通过 `RollingGen` + `task_generator` 自动化这个过程

### 5. 投资组合构建

从模型预测到实际持仓的过程：

```
模型输出 → 股票评分排序 → 选股 → 权重分配 → 约束检查 → 最终持仓

选股策略：
- TopK: 选评分最高的K只股票（简单有效）
- TopK + Dropout: 在TopK基础上加入随机性，减少换手
  （Qlib的TopkDropoutStrategy: 只卖出排名跌出TopK+d的，只买入新进TopK-d的）

权重分配：
- 等权: 每只股票分配相同资金（最简单）
- 风险平价: 波动大的股票少配，波动小的多配
- 均值-方差优化: 最大化Sharpe Ratio（需要cvxpy）
```

### 6. 风险管理

**核心原则：先求不亏，再求盈利**

| 风控维度 | 规则 | 说明 |
|----------|------|------|
| 最大回撤 | 回撤达8%时减仓50%，达10%时清仓 | 硬性止损线 |
| 单只持仓 | 单股不超过总资金5% | 避免集中风险 |
| 行业集中度 | 单行业不超过20% | 分散行业风险 |
| 换手率控制 | 日换手率≤20% | 控制交易成本 |
| Beta暴露 | 组合Beta接近1.0 | 避免过度暴露市场风险 |

---

## Phase分解总览

### Phase 1: 环境准备 (ACT_01-ACT_05) **[已完成]**
- **目标**：完成Mac OS开发环境搭建，安装所有必需工具

### Phase 2: Qlib部署与美股数据 (ACT_06-ACT_10) **[已完成]**
- **目标**：部署Qlib框架，下载美股数据，验证回测功能

### Phase 3: 富途OpenAPI集成 (ACT_11-ACT_15) **[已完成]**
- **目标**：集成富途OpenAPI，实现行情获取和模拟交易

### Phase 4: Qlib Alpha Pipeline (ACT_16-ACT_22) **[新]**
- **目标**：建设因子体系，训练预测模型，建立滚动回测框架，生成交易信号
- **核心产出**：可回测的完整Alpha策略Pipeline

### Phase 5: 信号执行与风控引擎 (ACT_23-ACT_27) **[新]**
- **目标**：将Qlib信号转化为FutuBroker交易指令，实现仓位管理与风控
- **核心产出**：自动化的信号→交易执行链路

### Phase 6: RD-Agent 自动化研究 (ACT_28-ACT_32) **[新]**
- **目标**：部署RD-Agent，实现因子自动挖掘、模型自动迭代的研究闭环
- **核心产出**：LLM驱动的因子/模型自动优化系统

### Phase 7: 全链路仿真与持续优化 (ACT_33-ACT_37) **[新]**
- **目标**：全Pipeline模拟盘运行，监控优化，准备实盘切换
- **核心产出**：经过验证的完整量化交易系统

---

## Phase 1: 环境准备 **[已完成]**

### ACT_01: 安装Xcode Command Line Tools
- **Review报告**: `docs/phase1_env_setup/review_01_xcode_cli.md`

### ACT_02: 安装Homebrew包管理器
- **Review报告**: `docs/phase1_env_setup/review_02_homebrew.md`

### ACT_03: 安装系统依赖库
- **Review报告**: `docs/phase1_env_setup/review_03_system_libs.md`

### ACT_04: 创建Python虚拟环境
- **Review报告**: `docs/phase1_env_setup/review_04_python_env.md`

### ACT_05: 安装核心Python依赖
- **Review报告**: `docs/phase1_env_setup/review_05_core_deps.md`

---

## Phase 2: Qlib部署与美股数据 **[已完成]**

### ACT_06: 安装Qlib框架
- **Review报告**: `docs/phase2_qlib_setup/review_06_qlib_install.md`

### ACT_07: 下载美股数据
- **Review报告**: `docs/phase2_qlib_setup/review_07_us_data_download.md`

### ACT_08: 验证数据完整性
- **Review报告**: `docs/phase2_qlib_setup/review_08_data_validation.md`

### ACT_09: 运行LightGBM示例Workflow
- **Review报告**: `docs/phase2_qlib_setup/review_09_lightgbm_workflow.md`

### ACT_10: Mac OS兼容性验证
- **Review报告**: `docs/phase2_qlib_setup/review_10_mac_compatibility.md`

---

## Phase 3: 富途OpenAPI集成 **[已完成]**

### ACT_11: 安装富途OpenAPI SDK
- **Review报告**: `docs/phase3_futu_integration/review_11_futu_sdk_install.md`

### ACT_12: 配置富途OpenD网关
- **Review报告**: `docs/phase3_futu_integration/review_12_opend_config.md`

### ACT_13: 测试行情数据获取
- **Review报告**: `docs/phase3_futu_integration/review_13_quote_test.md`

### ACT_14: 测试模拟交易下单
- **Review报告**: `docs/phase3_futu_integration/review_14_trade_test.md`

### ACT_15: 实现FutuBroker封装类
- **Review报告**: `docs/phase3_futu_integration/review_15_broker_wrapper.md`

---

## Phase 4: Qlib Alpha Pipeline

> **学习目标**：理解因子工程、模型训练、滚动回测的完整流程
> 
> **背景知识**：这个Phase是整个系统的核心。我们要建立一个完整的Alpha策略Pipeline：
> 从原始行情数据出发，经过因子计算、模型预测、信号生成、组合构建，最终产出
> "明天该买哪些股票、卖哪些股票"的决策。

### ACT_16: Alpha因子库建设

**做什么**：构建项目的因子库，包含Qlib内置因子和自定义美股因子。

**关键概念**：
- Alpha158是Qlib内置的158个因子集，覆盖K线形态、价格动量、成交量等维度
- 我们需要在此基础上添加适合美股的因子（如VIX相关、ETF动量等）

**具体任务**：
1. 配置Alpha158数据处理器（DataHandler），适配美股数据格式
2. 验证Alpha158在美股数据上的因子分布和IC值
3. 开发5-10个自定义美股因子：
   - 美股特有因子：SPY相对强弱、VIX恐慌因子、行业轮动因子
   - 增强因子：多尺度动量（5/10/20/60日）、波动率调整收益
4. 实现因子评估工具：自动计算IC、ICIR、Rank IC、因子换手率
5. 因子去重和共线性检测（相关系数 > 0.7的因子保留IC更高的一个）

**验收标准**：
- Alpha158在美股数据上成功计算，无NaN异常
- 至少5个因子的|Rank IC| > 0.03
- 因子评估报告自动生成

**代码结构**：
```
src/research/
├── factors/
│   ├── __init__.py
│   ├── alpha158_config.py      # Alpha158的YAML配置
│   ├── custom_factors.py       # 自定义因子表达式
│   └── factor_evaluator.py     # 因子IC/ICIR评估工具
configs/qlib/
├── alpha158_handler.yaml       # DataHandler配置
└── factor_evaluation.yaml      # 因子评估配置
```

- **需求文档**: `docs/phase4_alpha_pipeline/ACT_16_factor_library_requirements.md`
- **Review报告**: `docs/phase4_alpha_pipeline/review_16_factor_library.md`

---

### ACT_17: 预测模型训练

**做什么**：使用Qlib的模型框架训练收益预测模型，实现从因子到收益预测的映射。

**关键概念**：
- Qlib的Model层接收因子矩阵（N只股票 x M个因子），输出每只股票的预测收益
- 推荐从LightGBM开始（训练快、效果稳定），后续可尝试更复杂的模型

**Qlib模型层级**：
```
入门模型（先用这些建立baseline）：
├── LightGBM          — 梯度提升树，训练快，可解释性好
├── XGBoost           — 类似LightGBM，可做交叉验证
└── Linear            — 线性模型，最简单的baseline

进阶模型（Alpha Pipeline稳定后尝试）：
├── DoubleEnsemble    — 样本+特征双重集成，抗过拟合
├── TabNet            — 注意力机制的表格模型
└── CatBoost          — 自动处理类别特征

深度模型（RD-Agent阶段尝试）：
├── TRA (Transformer) — 时序Transformer
├── HIST              — 概念感知的图网络
└── ADARNN            — 自适应分布漂移的RNN
```

**具体任务**：
1. 配置LightGBM训练YAML（参数：num_leaves=128, learning_rate=0.05, num_boost_round=1000）
2. 配置训练/验证/测试集时间分割：
   - 训练集：2015-01-01 ~ 2022-12-31
   - 验证集：2023-01-01 ~ 2023-12-31
   - 测试集：2024-01-01 ~ 2024-12-31
3. 运行单次训练，获取baseline指标（IC, ICIR, 年化收益）
4. 尝试DoubleEnsemble和XGBoost作为对比
5. 分析特征重要性（哪些因子贡献最大）

**验收标准**：
- LightGBM训练成功完成，输出预测结果
- 测试集IC > 0.03，ICIR > 0.3
- 生成特征重要性分析报告
- 至少3个模型的对比结果

**代码结构**：
```
src/research/
├── models/
│   ├── __init__.py
│   ├── model_trainer.py        # 模型训练封装
│   └── model_evaluator.py      # 模型评估工具
configs/qlib/
├── lgbm_alpha158.yaml          # LightGBM训练配置
├── double_ensemble.yaml        # DoubleEnsemble配置
└── model_comparison.yaml       # 多模型对比配置
```

- **需求文档**: `docs/phase4_alpha_pipeline/ACT_17_model_training_requirements.md`
- **Review报告**: `docs/phase4_alpha_pipeline/review_17_model_training.md`

---

### ACT_18: 滚动训练框架

**做什么**：实现Qlib的滚动训练机制，让模型自动随时间滚动更新。

**关键概念**：
> 单次训练的模型用3年数据训练一次就不再更新，但市场在变化。
> 滚动训练的意思是：每隔一段时间（比如每月），用最新的数据重新训练模型，
> 这样模型始终能"看到"最新的市场规律。这是量化策略的标准做法。

**Qlib滚动训练机制**：
```python
# Qlib使用 RollingGen 自动生成滚动训练任务
from qlib.workflow.task.gen import RollingGen

# 配置：每月滚动一次，训练窗口3年，验证6个月
rolling_gen = RollingGen(
    step=20,          # 每20个交易日滚动一次（约1个月）
    rtype="expanding"  # expanding=训练窗口不断扩大, rolling=固定窗口
)

# RollingGen会自动生成多个训练任务：
# Task 1: train 2015-2021, valid 2022H1, test 2022H2
# Task 2: train 2015-2022H1, valid 2022H2, test 2023H1
# Task 3: train 2015-2022, valid 2023H1, test 2023H2
# ...
```

**具体任务**：
1. 配置 `RollingGen`，参数：step=20（月度滚动），expanding模式
2. 配置 `task_generator` 自动生成滚动训练任务序列
3. 运行完整的滚动训练（2015-2025），生成每月的预测结果
4. 实现 `SignalRecord` 收集所有滚动窗口的预测信号
5. 分析IC随时间的变化趋势（检测Alpha衰减）
6. 与单次训练的结果对比

**验收标准**：
- 滚动训练成功完成所有窗口（约36-48个月度窗口）
- 每个窗口的预测信号自动合并为时间序列
- 滚动IC时序图生成
- 滚动训练vs单次训练的对比报告

**代码结构**：
```
src/research/
├── rolling/
│   ├── __init__.py
│   ├── rolling_trainer.py      # 滚动训练封装
│   └── rolling_analyzer.py     # 滚动训练分析
configs/qlib/
├── rolling_lgbm.yaml           # 滚动LightGBM配置
└── rolling_schedule.yaml       # 滚动时间表配置
```

- **需求文档**: `docs/phase4_alpha_pipeline/ACT_18_rolling_training_requirements.md`
- **Review报告**: `docs/phase4_alpha_pipeline/review_18_rolling_training.md`

---

### ACT_19: 回测引擎搭建

**做什么**：基于Qlib的回测框架，将模型预测信号转化为模拟交易，评估策略真实表现。

**关键概念**：
> 模型预测了"每只股票明天的预期收益"，但我们还需要决定：
> - 买哪些？→ 选股策略（TopkDropoutStrategy）
> - 买多少？→ 权重分配（等权 / 风险平价）
> - 什么时候调仓？→ 交易频率（日频 / 周频）
> - 考虑交易成本（手续费 + 滑点）
>
> 回测就是在历史数据上模拟这整个过程，看策略到底能赚多少钱。

**Qlib回测架构**：
```
                  ┌─────────────┐
                  │  Backtest   │
                  │   Engine    │
                  └──────┬──────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
        ┌──────────┐ ┌──────┐ ┌──────────┐
        │ Strategy │ │ Risk │ │ Executor │
        │ (选股)   │ │(风控) │ │ (执行)    │
        └──────────┘ └──────┘ └──────────┘

Strategy = TopkDropoutStrategy:
  - topk=50: 持有评分最高的50只股票
  - n_drop=5: 每次只替换5只（降低换手率）
  
Executor = SimulatorExecutor:
  - 模拟真实交易执行
  - 考虑成交量限制（不超过日均成交量的10%）
  - 考虑滑点（买入按ask, 卖出按bid）
```

**具体任务**：
1. 配置 `TopkDropoutStrategy`（topk=30, n_drop=3）
2. 配置 `SimulatorExecutor`，设置交易成本：
   - 手续费：买卖各0.05%（美股较低）
   - 滑点：0.05%
   - 最小交易金额：$100
3. 运行回测，生成完整收益曲线
4. 实现回测指标计算器：年化收益、最大回撤、Sharpe、Calmar、换手率
5. 对比不同参数组合（topk=20/30/50, n_drop=2/3/5）
6. 生成回测报告（含收益曲线图、月度收益热力图、回撤图）

**验收标准**：
- 回测成功运行，生成收益曲线
- 年化收益率 > 15%（初始目标，后续通过因子优化提升）
- 最大回撤 < 15%（初始目标）
- 回测报告包含完整的指标和可视化

**代码结构**：
```
src/research/
├── backtest/
│   ├── __init__.py
│   ├── backtest_runner.py      # 回测运行器
│   ├── metrics.py              # 指标计算
│   └── report_generator.py     # 报告生成
configs/qlib/
├── backtest_topk.yaml          # TopK回测配置
└── backtest_comparison.yaml    # 参数对比配置
results/backtest/               # 回测结果输出目录
```

- **需求文档**: `docs/phase4_alpha_pipeline/ACT_19_backtest_engine_requirements.md`
- **Review报告**: `docs/phase4_alpha_pipeline/review_19_backtest_engine.md`

---

### ACT_20: 信号生成Pipeline

**做什么**：构建从"模型训练完成"到"每日交易信号输出"的自动化Pipeline。

**关键概念**：
> 前面ACT_16-19建立了各个组件，这里是把它们串成一条自动化的流水线：
> 每天美股收盘后，自动拉取最新数据 → 计算因子 → 用最新模型预测 → 
> 输出"明天要买什么、卖什么"的信号文件。

**Pipeline流程**：
```
[每日 16:30 EST 触发]
    │
    ├─ 1. 数据更新: 从Qlib数据源获取最新行情
    ├─ 2. 因子计算: DataHandler自动计算Alpha158+自定义因子
    ├─ 3. 模型预测: 用最新的滚动模型对全市场股票评分
    ├─ 4. 信号生成: TopK选股，计算目标仓位
    ├─ 5. 信号对比: 与当前持仓对比，生成调仓指令
    └─ 6. 输出: 交易信号文件 (JSON/CSV)
         → {"AAPL": {"action": "hold", "target_weight": 0.033},
            "MSFT": {"action": "buy",  "target_weight": 0.033},
            "TSLA": {"action": "sell", "target_weight": 0.0}}
```

**具体任务**：
1. 实现 `SignalPipeline` 类，封装完整的日度信号生成流程
2. 实现数据增量更新机制（只获取新增数据，不重复下载）
3. 信号文件格式定义（JSON），包含：股票代码、操作、目标权重、预测分数
4. 实现信号缓存和版本管理（每日信号保存在 `results/signals/` 目录）
5. 添加信号质量检查：覆盖率、异常值检测、信号翻转率
6. 编写集成测试验证完整Pipeline

**验收标准**：
- 一条命令即可运行完整Pipeline生成当日信号
- 信号文件格式规范，包含完整字段
- 信号质量检查通过
- Pipeline运行时间 < 10分钟

**代码结构**：
```
src/research/
├── pipeline/
│   ├── __init__.py
│   ├── signal_pipeline.py      # 信号Pipeline主类
│   ├── data_updater.py         # 数据增量更新
│   └── signal_checker.py       # 信号质量检查
results/signals/
├── signal_20260504.json        # 日度信号文件
└── signal_history.csv          # 历史信号汇总
```

- **需求文档**: `docs/phase4_alpha_pipeline/ACT_20_signal_pipeline_requirements.md`
- **Review报告**: `docs/phase4_alpha_pipeline/review_20_signal_pipeline.md`

---

### ACT_21: Workflow自动化与MLflow集成

**做什么**：用Qlib Workflow统一管理实验，MLflow记录参数和指标，实现实验可追溯。

**关键概念**：
> 量化研究过程中会跑大量实验：不同因子组合、不同模型参数、不同选股数量...
> 如果不系统性地记录每次实验的参数和结果，很快就会迷失在实验海洋中。
> Qlib集成了MLflow，可以自动记录每次实验的一切。

**具体任务**：
1. 配置MLflow tracking server（本地SQLite后端）
2. 编写统一的实验Workflow YAML，支持参数化运行
3. 实现实验对比脚本：自动从MLflow拉取结果，生成对比表格
4. 建立标准的实验命名规范（如 `alpha158_lgbm_topk30_rolling20`）
5. 编写最佳实验筛选工具（按Sharpe/IC排序）

**验收标准**：
- MLflow UI可访问，展示所有实验
- 每次实验自动记录：因子集、模型类型、训练参数、回测指标
- 实验对比报告自动生成

**代码结构**：
```
src/research/
├── workflow/
│   ├── __init__.py
│   ├── experiment_manager.py   # 实验管理
│   └── comparison.py           # 实验对比
configs/qlib/
├── workflow_base.yaml          # 基础Workflow模板
└── workflow_experiments.yaml   # 实验矩阵配置
```

- **需求文档**: `docs/phase4_alpha_pipeline/ACT_21_workflow_mlflow_requirements.md`
- **Review报告**: `docs/phase4_alpha_pipeline/review_21_workflow_mlflow.md`

---

### ACT_22: Phase 4 端到端验证

**做什么**：对整个Alpha Pipeline进行端到端验证，确保所有组件正确串联。

**具体任务**：
1. 端到端测试：从原始数据到最终信号，全链路自动运行
2. 基线性能确认：记录当前Pipeline的Sharpe/IC/回撤等核心指标作为基线
3. 消融实验：对比Alpha158 vs Alpha158+自定义因子的提升
4. 稳健性测试：不同时间段（牛市/熊市/震荡）的表现分解
5. 编写Phase 4总结报告

**验收标准**：
- 全Pipeline端到端运行成功
- 基线指标已记录：年化收益≥15%, IC≥0.03, 最大回撤≤15%
- 消融实验证明自定义因子有正向贡献
- 总结报告完成

- **需求文档**: `docs/phase4_alpha_pipeline/ACT_22_e2e_validation_requirements.md`
- **Review报告**: `docs/phase4_alpha_pipeline/review_22_e2e_validation.md`

---

## Phase 5: 信号执行与风控引擎

> **学习目标**：理解从量化信号到实际交易执行的完整链路
>
> **背景知识**：Phase 4产出的是"理论上该怎么交易"的信号。但真正执行时还需要：
> - 将信号翻译成具体的买入/卖出/持有指令
> - 计算每笔交易的金额和数量
> - 在下单前检查风控规则
> - 处理执行中的各种异常（部分成交、网络中断等）
> - 记录完整的交易日志用于后续分析

### ACT_23: 信号解析与执行器

**做什么**：将Pipeline生成的JSON信号文件解析为具体的交易指令，通过FutuBroker执行。

**关键概念**：
```
信号文件 (target portfolio)              当前持仓 (current portfolio)
┌─────────────────────────┐          ┌──────────────────────────┐
│ AAPL: 3.3%              │          │ AAPL: 3.5% (已持有)      │
│ MSFT: 3.3%              │          │ GOOG: 3.2% (需卖出)      │
│ NVDA: 3.3%              │          │ NVDA: 3.0% (需加仓)      │
│ ...30只                 │          │ ...28只                   │
└────────────┬────────────┘          └──────────┬───────────────┘
             │                                  │
             └──────────┬───────────────────────┘
                        ▼
              ┌──────────────────┐
              │ 差异计算 (Rebalance) │
              │ AAPL: 持有 (3.3%≈3.5%)│
              │ GOOG: 卖出 (3.2%→0%) │
              │ MSFT: 买入 (0%→3.3%) │
              │ NVDA: 加仓 (3.0→3.3%)│
              └──────────────────┘
```

**具体任务**：
1. 实现 `SignalExecutor` 类：
   - 读取信号文件，解析目标持仓
   - 查询当前FutuBroker持仓
   - 计算差异，生成调仓指令列表
   - 按顺序执行：先卖出释放资金，再买入
2. 实现交易数量计算器（考虑美股最小交易单位、价格、可用资金）
3. 实现交易日志记录（每笔交易的时间、价格、数量、状态）
4. 错误处理：部分成交、报价超时、网络中断的重试机制
5. Dry-run模式：只输出交易计划不实际下单，用于审核

**验收标准**：
- 信号文件→交易指令的转换正确
- Dry-run模式输出清晰的交易计划
- 在富途模拟盘成功执行一轮完整调仓
- 交易日志完整记录

**代码结构**：
```
src/execution/
├── futu_broker.py              # [已有] FutuBroker封装
├── signal_executor.py          # 信号执行器（新）
├── order_calculator.py         # 交易数量计算（新）
└── trade_logger.py             # 交易日志（新）
```

- **需求文档**: `docs/phase5_execution/ACT_23_signal_executor_requirements.md`
- **Review报告**: `docs/phase5_execution/review_23_signal_executor.md`

---

### ACT_24: 仓位管理器

**做什么**：实现持仓管理系统，追踪实际持仓、记录盈亏、提供仓位查询。

**关键概念**：
> 仓位管理器是连接"策略想要什么"和"实际持有什么"的桥梁。
> 它需要实时知道：每只股票的持仓数量、成本价、当前市值、浮盈/浮亏。

**具体任务**：
1. 实现 `PortfolioManager` 类：
   - 从FutuBroker同步实际持仓
   - 维护持仓状态：股票代码、数量、成本价、当前市值
   - 计算组合级指标：总市值、现金比例、各股票权重
2. 持仓快照功能：每日定时保存持仓快照到本地
3. P&L（盈亏）追踪：
   - 每笔交易的实现盈亏
   - 持仓的浮动盈亏
   - 日/周/月度P&L汇总
4. 持仓漂移检测：实际持仓vs目标持仓的偏差监控

**验收标准**：
- 与FutuBroker持仓数据一致
- 日度持仓快照自动保存
- P&L计算正确

**代码结构**：
```
src/execution/
├── portfolio_manager.py        # 仓位管理器（新）
├── pnl_tracker.py             # 盈亏追踪（新）
results/portfolio/
├── snapshot_20260504.json      # 持仓快照
└── pnl_daily.csv              # 日度盈亏
```

- **需求文档**: `docs/phase5_execution/ACT_24_portfolio_manager_requirements.md`
- **Review报告**: `docs/phase5_execution/review_24_portfolio_manager.md`

---

### ACT_25: 风控引擎

**做什么**：实现交易前和交易后的风险控制检查。

**关键概念**：
> 风控是量化系统的生命线。没有风控的量化系统就像没有刹车的汽车。
> 
> **交易前风控**（Pre-trade）：在下单之前检查，不合规则的交易直接拒绝
> **交易后风控**（Post-trade）：在持仓变化后检查，触发预警或自动减仓

**风控规则体系**：
```
Pre-trade Checks (每笔交易前):
├── 单股集中度: 单股不超过总资金5%
├── 行业集中度: 单行业不超过20%
├── 最大持仓数: 不超过50只
├── 最小交易金额: 不低于$100
└── 流动性检查: 单笔不超过个股日均成交量5%

Post-trade Checks (持仓变化后):
├── 组合回撤: 达8%减半仓，达10%清仓
├── 单股止损: 单股亏损超15%强制卖出
├── 日内波动: 组合日内跌幅超3%暂停交易
└── 换手率: 日换手率超20%暂停新增买入
```

**具体任务**：
1. 实现 `RiskEngine` 类，包含所有风控规则
2. Pre-trade检查：返回 allow/reject + 原因
3. Post-trade检查：返回 ok/warning/critical + 建议操作
4. 回撤监控器：实时计算从最高点的回撤比例
5. 风控参数可配置化（YAML配置文件）
6. 风控日志和告警（console输出 + 日志文件）

**验收标准**：
- 所有风控规则正确实现，有单元测试覆盖
- 超出阈值时正确拒绝交易或发出告警
- 回撤达到10%时正确触发清仓

**代码结构**：
```
src/risk/
├── __init__.py
├── risk_engine.py              # 风控引擎主类
├── pre_trade_checks.py         # 交易前检查
├── post_trade_checks.py        # 交易后检查
├── drawdown_monitor.py         # 回撤监控
└── risk_logger.py              # 风控日志
configs/
├── risk_rules.yaml             # 风控规则配置
```

- **需求文档**: `docs/phase5_execution/ACT_25_risk_engine_requirements.md`
- **Review报告**: `docs/phase5_execution/review_25_risk_engine.md`

---

### ACT_26: 调度器与定时任务

**做什么**：实现系统的自动化调度，让Pipeline按计划自动运行。

**每日自动化流程**：
```
美东时间 (EST)
─────────────────────────────────────────
04:00  预开盘数据准备（拉取隔夜数据）
09:30  美股开盘 — 监控持仓状态
10:00  执行昨日收盘后生成的交易信号（开盘后30分钟等价格稳定）
16:00  收盘 — 保存持仓快照
16:30  运行信号Pipeline — 生成明日交易信号
17:00  风控日报 — 发送当日P&L和风控状态
─────────────────────────────────────────

每月1日:
- 触发滚动训练（用最新月度数据重训模型）
- 生成月度绩效报告
```

**具体任务**：
1. 实现 `Scheduler` 类，管理定时任务
2. 日度任务：信号生成、交易执行、持仓快照、日报
3. 月度任务：滚动训练、月度报告
4. 任务依赖管理：信号生成必须在交易执行之前完成
5. 失败重试和告警机制

**验收标准**：
- 定时任务正确触发
- 任务日志完整
- 失败时正确告警

**代码结构**：
```
src/
├── scheduler/
│   ├── __init__.py
│   ├── scheduler.py            # 调度主类
│   ├── daily_tasks.py          # 日度任务定义
│   └── monthly_tasks.py        # 月度任务定义
```

- **需求文档**: `docs/phase5_execution/ACT_26_scheduler_requirements.md`
- **Review报告**: `docs/phase5_execution/review_26_scheduler.md`

---

### ACT_27: Phase 5 端到端验证

**做什么**：在富途模拟盘上验证完整的 信号→风控→执行→记录 链路。

**具体任务**：
1. 用历史信号在模拟盘执行一周的模拟交易
2. 验证持仓与目标一致
3. 验证风控规则正常工作（人为触发各种风控阈值）
4. 验证交易日志和P&L计算正确
5. 编写Phase 5总结报告

**验收标准**：
- 模拟盘上成功执行至少5次调仓
- 风控规则全部验证通过
- 交易日志和P&L报告完整
- Phase 5总结报告完成

- **需求文档**: `docs/phase5_execution/ACT_27_e2e_validation_requirements.md`
- **Review报告**: `docs/phase5_execution/review_27_e2e_validation.md`

---

## Phase 6: RD-Agent 自动化研究

> **学习目标**：理解如何用LLM驱动的自动化系统来持续挖掘新因子和优化模型
>
> **背景知识**：
> RD-Agent是微软开发的LLM驱动研究自动化框架。它的核心理念是：
> - 人类研究员的工作可以被分解为：**提出假设 → 写代码实现 → 运行实验 → 分析结果 → 提出新假设**
> - RD-Agent用LLM来自动化这个循环
> - 在量化场景中：自动提出新因子假设、自动生成因子计算代码、自动回测验证、自动分析结果
>
> **为什么需要RD-Agent？**
> Alpha因子会衰减（市场学习效应），人工挖掘新因子速度有限。
> RD-Agent可以7x24小时不间断地探索新因子空间，大幅提升研究效率。

### RD-Agent 架构概览

```
┌──────────────────────────────────────────────────┐
│                  RD-Agent Loop                    │
│                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ Research  │───▶│  Develop │───▶│  Test    │  │
│  │ (假设)    │    │ (实现)    │    │ (验证)   │  │
│  └──────────┘    └──────────┘    └──────────┘  │
│       ▲                               │         │
│       │         ┌──────────┐          │         │
│       └─────────│ Feedback │◀─────────┘         │
│                 │ (反馈)    │                     │
│                 └──────────┘                     │
│                                                  │
│  Knowledge Forest: 记录所有尝试过的假设和结果       │
│  Thompson Sampling: 智能决定下一步探索因子还是模型   │
└──────────────────────────────────────────────────┘
```

### ACT_28: Docker环境与RD-Agent安装

**做什么**：安装Docker Desktop并部署RD-Agent。

**关键依赖**：
- Docker Desktop（RD-Agent在Docker容器中执行代码，确保安全隔离）
- LLM API密钥（支持OpenAI GPT-4、DeepSeek、Claude等）
- 至少16GB内存（RD-Agent + Qlib同时运行）

**具体任务**：
1. 安装Docker Desktop for Mac
2. 克隆RD-Agent仓库，安装Python依赖
3. 配置LLM API（选择性价比最高的模型，如DeepSeek-V3）
4. 配置RD-Agent的Qlib集成模块
5. 运行RD-Agent的内置测试，确认安装成功
6. 测试单次因子生成循环（确认LLM→代码→回测→反馈链路通畅）

**验收标准**：
- Docker Desktop运行正常
- RD-Agent安装测试通过
- 单次因子生成循环成功完成
- LLM API调用正常，成本可控

**代码结构**：
```
configs/
├── rdagent/
│   ├── rdagent_config.yaml     # RD-Agent主配置
│   ├── llm_config.yaml         # LLM API配置
│   └── qlib_integration.yaml   # Qlib集成配置
```

- **需求文档**: `docs/phase6_rdagent/ACT_28_docker_rdagent_install_requirements.md`
- **Review报告**: `docs/phase6_rdagent/review_28_docker_rdagent_install.md`

---

### ACT_29: 因子自动挖掘配置

**做什么**：配置RD-Agent的因子挖掘模块，让它能自动生成、测试和筛选新因子。

**RD-Agent因子挖掘流程**：
```
1. LLM提出因子假设:
   "根据动量反转理论，短期（5日）动量与长期（60日）动量的差异可能
    捕捉到动量转换的信号"

2. LLM生成因子代码 (Co-STEER):
   class MomentumDivergenceFactor:
       def calculate(self, data):
           mom5 = data['close'].pct_change(5)
           mom60 = data['close'].pct_change(60)
           return mom5 - mom60

3. Docker沙箱中执行代码，计算因子值

4. 在Qlib中回测该因子的IC、ICIR

5. 分析结果:
   - IC = 0.042, ICIR = 0.68 → 有效因子，加入因子库
   - IC = 0.008, ICIR = 0.12 → 无效因子，记录到知识库避免重复
   
6. 基于结果，LLM提出下一个假设...
```

**具体任务**：
1. 配置因子搜索空间（限定因子类型、输入数据、复杂度约束）
2. 配置因子评估标准（IC > 0.03, ICIR > 0.3作为通过门槛）
3. 配置因子去重规则（与现有因子相关性 > 0.7的自动跳过）
4. 实现因子库管理器：自动将通过验证的因子加入Alpha Pipeline
5. 运行首轮自动因子挖掘（目标：50轮迭代，筛选出5-10个新因子）
6. 分析新因子与Alpha158的互补性

**验收标准**：
- RD-Agent完成至少50轮因子挖掘迭代
- 至少5个新因子通过IC/ICIR门槛
- 新因子加入Pipeline后回测指标有提升
- 因子挖掘日志完整

- **需求文档**: `docs/phase6_rdagent/ACT_29_factor_mining_requirements.md`
- **Review报告**: `docs/phase6_rdagent/review_29_factor_mining.md`

---

### ACT_30: 模型自动迭代配置

**做什么**：配置RD-Agent的模型优化模块，自动探索更好的模型架构和超参数。

**RD-Agent模型迭代流程**：
```
1. 分析当前模型的弱点:
   "LightGBM在高波动率时期预测偏差较大，可能需要引入
    注意力机制来动态调整对不同市场环境的响应"

2. 生成模型代码:
   - 修改现有模型架构
   - 或提出全新模型（如Transformer + LightGBM ensemble）

3. 在Qlib框架中训练和回测

4. 与当前最佳模型对比:
   - Sharpe提升 > 0.1 → 采用新模型
   - 否则 → 记录结果，继续探索
```

**具体任务**：
1. 配置模型搜索空间（允许探索的模型类型和超参数范围）
2. 配置模型评估标准（相比baseline的IC/Sharpe提升量）
3. 实现模型版本管理（MLflow tracking）
4. 运行首轮自动模型迭代（目标：20轮迭代）
5. 最佳模型与baseline LightGBM对比

**验收标准**：
- RD-Agent完成至少20轮模型迭代
- 至少1个模型在IC或Sharpe上超过baseline
- 模型迭代日志完整，可通过MLflow查看

- **需求文档**: `docs/phase6_rdagent/ACT_30_model_iteration_requirements.md`
- **Review报告**: `docs/phase6_rdagent/review_30_model_iteration.md`

---

### ACT_31: 因子-模型协同优化

**做什么**：配置RD-Agent的Thompson Sampling调度器，让因子挖掘和模型迭代协同优化。

**关键概念**：
> Thompson Sampling是一种智能决策算法。RD-Agent用它来决定：
> "接下来是应该探索新因子，还是优化模型？"
>
> 如果最近几轮因子挖掘成功率高 → 继续挖因子
> 如果最近几轮模型迭代收益大 → 转向优化模型
> 这样可以自动把有限的计算资源分配到最有价值的方向。

**具体任务**：
1. 配置Thompson Sampling调度器（因子vs模型的初始概率各50%）
2. 配置迭代总预算（LLM调用次数、运行时间限制）
3. 运行协同优化循环（目标：100轮迭代）
4. 分析优化轨迹：因子/模型各贡献了多少提升
5. 将最优配置固化到Alpha Pipeline

**验收标准**：
- 协同优化完成100轮迭代
- Pipeline的Sharpe Ratio相比Phase 4 baseline提升 ≥ 0.3
- 优化轨迹报告完成

- **需求文档**: `docs/phase6_rdagent/ACT_31_co_optimization_requirements.md`
- **Review报告**: `docs/phase6_rdagent/review_31_co_optimization.md`

---

### ACT_32: Phase 6 验证与因子库固化

**做什么**：验证RD-Agent产出的因子和模型，将经过验证的成果固化到生产Pipeline。

**具体任务**：
1. 对RD-Agent发现的所有因子进行独立验证（使用不同时间窗口交叉验证）
2. 检查因子的样本外表现（避免过拟合）
3. 将通过验证的因子和模型写入生产配置
4. 更新滚动训练框架以包含新因子
5. 完整回测对比：原始Alpha158 vs Alpha158+RD-Agent发现因子
6. 编写Phase 6总结报告

**验收标准**：
- 至少10个RD-Agent因子通过独立验证
- 增强版Pipeline的年化收益 ≥ 20%（向30%目标推进）
- 最大回撤 ≤ 12%
- 完整的Phase 6总结报告

- **需求文档**: `docs/phase6_rdagent/ACT_32_validation_requirements.md`
- **Review报告**: `docs/phase6_rdagent/review_32_validation.md`

---

## Phase 7: 全链路仿真与持续优化

> **学习目标**：将所有组件串联成生产级系统，在模拟盘上长期运行验证
>
> **背景知识**：
> 回测结果再好也不能完全代表实盘表现。这个Phase的目标是在富途模拟盘上
> 进行至少1个月的"纸面交易"（Paper Trading），在真实市场环境下验证系统：
> - 实际的成交价格（而非理想化的收盘价）
> - 真实的延迟和滑点
> - 系统的稳定性和容错能力

### ACT_33: 全链路集成

**做什么**：将Phase 4（Alpha Pipeline）+ Phase 5（执行引擎）+ Phase 6（RD-Agent因子）完整串联。

**完整系统流程**：
```
┌───────────────────────────────────────────────────────┐
│                     日度运行流程                        │
│                                                       │
│  16:00 收盘                                           │
│    ↓                                                  │
│  16:30 数据更新 + 因子计算                              │
│    ↓                                                  │
│  17:00 模型预测 + 信号生成                              │
│    ↓                                                  │
│  17:30 风控预检 + 交易计划                              │
│    ↓ (信号过夜，次日执行)                               │
│  10:00 开盘30分钟后 → 执行交易                          │
│    ↓                                                  │
│  10:30 执行确认 + 持仓更新                              │
│    ↓                                                  │
│  16:00 收盘 → 日度P&L + 风控日报                        │
└───────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────┐
│                     月度运行流程                        │
│                                                       │
│  每月1日: 触发滚动训练（用最新数据重训模型）              │
│  每月5日: 新模型上线（替换旧模型）                       │
│  每月末: 月度绩效报告 + RD-Agent新因子评审               │
└───────────────────────────────────────────────────────┘
```

**具体任务**：
1. 实现系统主入口（`main.py`），串联所有模块
2. 配置文件统一管理（一个YAML管全局配置）
3. 端到端冒烟测试（模拟一天的完整流程）
4. 异常恢复机制：系统崩溃后从最近快照恢复

**验收标准**：
- 全链路端到端运行成功
- 异常恢复测试通过
- 一天完整流程的运行时间 < 30分钟

**代码结构**：
```
src/
├── main.py                     # 系统主入口
├── config_loader.py            # 统一配置加载
configs/
├── system_config.yaml          # 全局系统配置
```

- **需求文档**: `docs/phase7_live_simulation/ACT_33_full_integration_requirements.md`
- **Review报告**: `docs/phase7_live_simulation/review_33_full_integration.md`

---

### ACT_34: 模拟盘运行（第1-2周）

**做什么**：系统上线富途模拟盘，开始为期2周的初始验证。

**具体任务**：
1. 在模拟盘上启动系统，每日自动运行
2. 每日检查：信号生成是否正常、交易执行是否成功、风控是否触发
3. 记录实际执行与回测之间的偏差（执行滑点、成交率）
4. 修复发现的任何问题
5. 周报：前2周的收益/回撤/Sharpe vs 回测预期

**验收标准**：
- 系统连续运行2周无重大故障
- 实际执行与回测偏差 < 5%
- 初步P&L报告生成

- **需求文档**: `docs/phase7_live_simulation/ACT_34_paper_trading_week1_requirements.md`
- **Review报告**: `docs/phase7_live_simulation/review_34_paper_trading_week1.md`

---

### ACT_35: 模拟盘运行（第3-4周）与调优

**做什么**：继续模拟盘运行，根据前2周数据进行调优。

**具体任务**：
1. 分析前2周的执行数据，识别改进点
2. 调优交易执行参数（执行时间、订单类型、滑点缓冲）
3. 调优风控参数（根据实际波动调整阈值）
4. 继续运行2周
5. 完成4周完整的模拟盘绩效报告

**验收标准**：
- 系统连续运行4周
- 年化收益预估 ≥ 25%（基于4周数据推算）
- 最大回撤 ≤ 10%
- 执行偏差 < 3%

- **需求文档**: `docs/phase7_live_simulation/ACT_35_paper_trading_month1_requirements.md`
- **Review报告**: `docs/phase7_live_simulation/review_35_paper_trading_month1.md`

---

### ACT_36: 性能监控与告警系统

**做什么**：建立系统级监控，确保系统运行健康。

**监控维度**：
| 维度 | 指标 | 告警阈值 |
|------|------|----------|
| 策略 | 滚动Sharpe(30日) | < 0.5 |
| 策略 | 单日亏损 | > 2% |
| 策略 | 连续亏损天数 | > 5天 |
| 系统 | Pipeline运行时间 | > 30分钟 |
| 系统 | 交易执行失败率 | > 10% |
| 数据 | 数据缺失率 | > 5% |

**具体任务**：
1. 实现监控仪表板（终端/日志形式，不做Web UI）
2. 异常告警通知（日志 + 可选飞书/邮件通知）
3. 性能劣化检测：连续2周Sharpe下降则自动暂停交易
4. 系统健康检查脚本

**验收标准**：
- 监控覆盖所有关键指标
- 告警在阈值触发时正确发出
- 性能劣化检测正确工作

- **需求文档**: `docs/phase7_live_simulation/ACT_36_monitoring_requirements.md`
- **Review报告**: `docs/phase7_live_simulation/review_36_monitoring.md`

---

### ACT_37: 项目总结与实盘准备

**做什么**：总结整个项目，产出最终报告，为用户的实盘决策提供数据支持。

**具体任务**：
1. 编写项目总结报告，包含：
   - 策略描述（因子体系、模型架构、选股逻辑、风控规则）
   - 回测绩效（多年历史回测结果）
   - 模拟盘绩效（至少1个月实时交易数据）
   - 回测 vs 模拟盘对比分析
   - 已知风险和局限性
2. 实盘切换检查清单：
   - [ ] 模拟盘运行 ≥ 1个月且指标达标
   - [ ] 最大回撤从未超过10%
   - [ ] 用户已阅读并理解所有风险
   - [ ] 用户出具书面确认（保留记录）
   - [ ] 初始资金规模确认
   - [ ] 风控参数针对实盘调整（更保守）
3. 实盘过渡计划（先小资金试运行，逐步放量）

**验收标准**：
- 项目总结报告完成
- 实盘切换检查清单定义完成
- 用户确认是否以及何时启动实盘

- **需求文档**: `docs/phase7_live_simulation/ACT_37_final_report_requirements.md`
- **Review报告**: `docs/phase7_live_simulation/review_37_final_report.md`

---

## 目录结构说明（修订版）

```
US_AI_Quant/
├── docs/                              # 文档目录
│   ├── phase1_env_setup/             # Phase 1文档 [已完成]
│   ├── phase2_qlib_setup/            # Phase 2文档 [已完成]
│   ├── phase3_futu_integration/      # Phase 3文档 [已完成]
│   ├── phase4_alpha_pipeline/        # Phase 4文档 [新]
│   ├── phase5_execution/             # Phase 5文档 [新]
│   ├── phase6_rdagent/               # Phase 6文档 [新]
│   └── phase7_live_simulation/       # Phase 7文档 [新]
├── src/                              # 源代码
│   ├── research/                     # 研究层（Qlib Alpha Pipeline）
│   │   ├── factors/                  # 因子库
│   │   ├── models/                   # 预测模型
│   │   ├── rolling/                  # 滚动训练
│   │   ├── backtest/                 # 回测引擎
│   │   ├── pipeline/                 # 信号Pipeline
│   │   └── workflow/                 # 实验管理
│   ├── execution/                    # 执行层（信号→交易）
│   │   ├── futu_broker.py            # 富途Broker封装 [已有]
│   │   ├── signal_executor.py        # 信号执行器
│   │   ├── portfolio_manager.py      # 仓位管理
│   │   ├── order_calculator.py       # 交易计算
│   │   └── trade_logger.py           # 交易日志
│   ├── risk/                         # 风控层
│   │   ├── risk_engine.py            # 风控引擎
│   │   ├── pre_trade_checks.py       # 交易前检查
│   │   ├── post_trade_checks.py      # 交易后检查
│   │   └── drawdown_monitor.py       # 回撤监控
│   ├── scheduler/                    # 调度层
│   │   ├── scheduler.py              # 任务调度
│   │   ├── daily_tasks.py            # 日度任务
│   │   └── monthly_tasks.py          # 月度任务
│   ├── monitoring/                   # 监控层
│   │   ├── dashboard.py              # 监控仪表板
│   │   └── alerting.py               # 告警通知
│   ├── config/                       # 配置管理
│   ├── utils/                        # 工具函数
│   └── main.py                       # 系统主入口
├── tests/                            # 测试代码
│   ├── unit/                         # 单元测试
│   ├── integration/                  # 集成测试
│   └── e2e/                          # 端到端测试
├── configs/                          # 配置文件
│   ├── qlib/                         # Qlib相关配置
│   ├── risk_rules.yaml               # 风控规则
│   ├── rdagent/                      # RD-Agent配置
│   └── system_config.yaml            # 全局系统配置
├── results/                          # 结果输出
│   ├── backtest/                     # 回测结果
│   ├── signals/                      # 信号文件
│   ├── portfolio/                    # 持仓快照
│   ├── factors/                      # 因子评估
│   └── reports/                      # 绩效报告
├── scripts/                          # 运维脚本
├── notebooks/                        # Jupyter研究笔记
├── logs/                             # 日志目录
├── requirements.txt                  # Python依赖
├── .env.example                      # 环境变量模板
├── PROJECT_PLAN.md                   # 本文件
└── README.md                         # 项目说明
```

---

## 依赖版本（锁定）

| 库 | 版本 | 用途 |
|---|------|------|
| pyqlib | 0.9.7 | 量化研究框架 |
| futu-api | 10.4.6408 | 富途OpenAPI |
| torch | 2.2.2 | 深度学习框架 |
| lightgbm | 4.6.0 | 梯度提升树模型 |
| xgboost | 3.2.0 | 梯度提升树模型 |
| pandas | 2.3.3 | 数据处理 |
| numpy | 1.26.4 | 数值计算 |
| scipy | 1.17.1 | 科学计算 |
| cvxpy | 1.6.7 | 凸优化（组合优化） |
| protobuf | >=5.0,<6.0 | 协议缓冲 |
| yfinance | 1.3.0 | Yahoo数据源 |
| mlflow | latest | 实验跟踪 |

---

## 文档规范

### 需求文档模板
每个 `ACT_XX_*_requirements.md` 包含：
1. **ACT概述**：目标、范围、前置条件
2. **详细需求**：功能需求、技术需求、依赖项
3. **验收标准**：完成定义、测试标准
4. **注意事项**：风险点、常见问题、最佳实践
5. **参考资料**：相关文档、外部链接

### Review报告模板
每个 `review_XX_*.md` 包含：
1. **执行摘要**：完成情况、关键成果
2. **实施过程**：步骤记录、遇到的问题、解决方案
3. **测试结果**：测试用例、通过率、性能指标
4. **问题与风险**：已知问题、风险项、后续计划
5. **结论与建议**：总结、下一步行动

---

## 工作流

1. 启动Phase前，编写对应ACT的需求文档
2. 按需求文档实施开发
3. 完成后编写Review报告
4. Review通过后，进入下一个ACT
5. 每Phase完成后进行端到端验证

---

## 修订日志

| 日期 | 版本 | 变更说明 |
|------|------|----------|
| 2026-05-02 | v1.0 | 初始版本，包含TradingAgents集成方案 |
| 2026-05-04 | v2.0 | 重大修订：移除TradingAgents，重新聚焦Qlib Alpha Pipeline + RD-Agent范式；Phase 4-7完全重写；新增量化概念教育模块 |

---

> 本文档随项目进展持续更新。
