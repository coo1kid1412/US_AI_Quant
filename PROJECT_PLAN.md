# US_AI_Quant 项目计划

> 项目名称：美股AI量化交易系统
> 启动日期：2026-05-02
> 最后更新：2026-05-03

---

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

## 项目概述

构建基于AI的美股量化交易系统，集成Qlib量化研究框架、富途OpenAPI程序化交易、TradingAgents多智能体决策系统。

---

## Phase分解总览

### Phase 1: 环境准备 (ACT_01-ACT_05)
- **目标**：完成Mac OS开发环境搭建，安装所有必需工具
- **预计完成**：第1周

### Phase 2: Qlib部署与美股数据 (ACT_06-ACT_10)
- **目标**：部署Qlib框架，下载美股数据，验证回测功能
- **预计完成**：第2周

### Phase 3: 富途OpenAPI集成 (ACT_11-ACT_15)
- **目标**：集成富途OpenAPI，实现行情获取和模拟交易
- **预计完成**：第3周

### Phase 4: TradingAgents集成 (ACT_16-ACT_20)
- **目标**：扩展TradingAgents，集成Qlib信号和富途交易
- **预计完成**：第4-5周

### Phase 5: 策略优化与回测 (ACT_21-ACT_25)
- **目标**：自定义美股因子，优化策略，多股票回测
- **预计完成**：第6-7周

### Phase 6: 实盘仿真 (ACT_26-ACT_30)
- **目标**：富途模拟账户端到端测试，性能优化
- **预计完成**：第8-9周

### Phase 7: RD-Agent部署（可选）(ACT_31-ACT_35)
- **目标**：部署RD-Agent，自动化因子挖掘
- **预计完成**：第10周+

---

## Phase 1: 环境准备

### ACT_01: 安装Xcode Command Line Tools
- **需求文档**: `docs/phase1_env_setup/ACT_01_xcode_cli_requirements.md`
- **Review报告**: `docs/phase1_env_setup/review_01_xcode_cli.md`

### ACT_02: 安装Homebrew包管理器
- **需求文档**: `docs/phase1_env_setup/ACT_02_homebrew_requirements.md`
- **Review报告**: `docs/phase1_env_setup/review_02_homebrew.md`

### ACT_03: 安装系统依赖库
- **需求文档**: `docs/phase1_env_setup/ACT_03_system_libs_requirements.md`
- **Review报告**: `docs/phase1_env_setup/review_03_system_libs.md`

### ACT_04: 创建Python虚拟环境
- **需求文档**: `docs/phase1_env_setup/ACT_04_python_env_requirements.md`
- **Review报告**: `docs/phase1_env_setup/review_04_python_env.md`

### ACT_05: 安装核心Python依赖
- **需求文档**: `docs/phase1_env_setup/ACT_05_core_deps_requirements.md`
- **Review报告**: `docs/phase1_env_setup/review_05_core_deps.md`

---

## Phase 2: Qlib部署与美股数据

### ACT_06: 安装Qlib框架
- **需求文档**: `docs/phase2_qlib_setup/ACT_06_qlib_install_requirements.md`
- **Review报告**: `docs/phase2_qlib_setup/review_06_qlib_install.md`

### ACT_07: 下载美股数据
- **需求文档**: `docs/phase2_qlib_setup/ACT_07_us_data_download_requirements.md`
- **Review报告**: `docs/phase2_qlib_setup/review_07_us_data_download.md`

### ACT_08: 验证数据完整性
- **需求文档**: `docs/phase2_qlib_setup/ACT_08_data_validation_requirements.md`
- **Review报告**: `docs/phase2_qlib_setup/review_08_data_validation.md`

### ACT_09: 运行LightGBM示例Workflow
- **需求文档**: `docs/phase2_qlib_setup/ACT_09_lightgbm_workflow_requirements.md`
- **Review报告**: `docs/phase2_qlib_setup/review_09_lightgbm_workflow.md`

### ACT_10: Mac OS兼容性验证
- **需求文档**: `docs/phase2_qlib_setup/ACT_10_mac_compatibility_requirements.md`
- **Review报告**: `docs/phase2_qlib_setup/review_10_mac_compatibility.md`

---

## Phase 3: 富途OpenAPI集成

### ACT_11: 安装富途OpenAPI SDK
- **需求文档**: `docs/phase3_futu_integration/ACT_11_futu_sdk_install_requirements.md`
- **Review报告**: `docs/phase3_futu_integration/review_11_futu_sdk_install.md`

### ACT_12: 配置富途OpenD网关
- **需求文档**: `docs/phase3_futu_integration/ACT_12_opend_config_requirements.md`
- **Review报告**: `docs/phase3_futu_integration/review_12_opend_config.md`

### ACT_13: 测试行情数据获取
- **需求文档**: `docs/phase3_futu_integration/ACT_13_quote_test_requirements.md`
- **Review报告**: `docs/phase3_futu_integration/review_13_quote_test.md`

### ACT_14: 测试模拟交易下单
- **需求文档**: `docs/phase3_futu_integration/ACT_14_trade_test_requirements.md`
- **Review报告**: `docs/phase3_futu_integration/review_14_trade_test.md`

### ACT_15: 实现FutuBroker封装类
- **需求文档**: `docs/phase3_futu_integration/ACT_15_broker_wrapper_requirements.md`
- **Review报告**: `docs/phase3_futu_integration/review_15_broker_wrapper.md`

---

## Phase 4: TradingAgents集成

### ACT_16: 扩展市场分析师（美股支持）
- **需求文档**: `docs/phase4_agents_integration/ACT_16_market_analyst_requirements.md`
- **Review报告**: `docs/phase4_agents_integration/review_16_market_analyst.md`

### ACT_17: 设计Qlib信号传递机制
- **需求文档**: `docs/phase4_agents_integration/ACT_17_signal_pipeline_requirements.md`
- **Review报告**: `docs/phase4_agents_integration/review_17_signal_pipeline.md`

### ACT_18: 集成富途Broker到交易员模块
- **需求文档**: `docs/phase4_agents_integration/ACT_18_broker_integration_requirements.md`
- **Review报告**: `docs/phase4_agents_integration/review_18_broker_integration.md`

### ACT_19: 端到端流程测试
- **需求文档**: `docs/phase4_agents_integration/ACT_19_e2e_test_requirements.md`
- **Review报告**: `docs/phase4_agents_integration/review_19_e2e_test.md`

### ACT_20: 性能优化与调优
- **需求文档**: `docs/phase4_agents_integration/ACT_20_performance_requirements.md`
- **Review报告**: `docs/phase4_agents_integration/review_20_performance.md`

---

## Phase 5: 策略优化与回测

### ACT_21: 自定义美股因子
- **需求文档**: `docs/phase5_backtest/ACT_21_custom_factors_requirements.md`
- **Review报告**: `docs/phase5_backtest/review_21_custom_factors.md`

### ACT_22: 优化模型参数
- **需求文档**: `docs/phase5_backtest/ACT_22_model_tuning_requirements.md`
- **Review报告**: `docs/phase5_backtest/review_22_model_tuning.md`

### ACT_23: 多股票回测验证
- **需求文档**: `docs/phase5_backtest/ACT_23_multi_stock_test_requirements.md`
- **Review报告**: `docs/phase5_backtest/review_23_multi_stock_test.md`

### ACT_24: 性能评估指标
- **需求文档**: `docs/phase5_backtest/ACT_24_metrics_requirements.md`
- **Review报告**: `docs/phase5_backtest/review_24_metrics.md`

### ACT_25: 策略对比与选择
- **需求文档**: `docs/phase5_backtest/ACT_25_strategy_selection_requirements.md`
- **Review报告**: `docs/phase5_backtest/review_25_strategy_selection.md`

---

## Phase 6: 实盘仿真

### ACT_26: 富途模拟账户配置
- **需求文档**: `docs/phase6_simulation/ACT_26_paper_account_requirements.md`
- **Review报告**: `docs/phase6_simulation/review_26_paper_account.md`

### ACT_27: 完整流程测试
- **需求文档**: `docs/phase6_simulation/ACT_27_full_test_requirements.md`
- **Review报告**: `docs/phase6_simulation/review_27_full_test.md`

### ACT_28: 延迟和稳定性优化
- **需求文档**: `docs/phase6_simulation/ACT_28_latency_requirements.md`
- **Review报告**: `docs/phase6_simulation/review_28_latency.md`

### ACT_29: 监控和告警机制
- **需求文档**: `docs/phase6_simulation/ACT_29_monitoring_requirements.md`
- **Review报告**: `docs/phase6_simulation/review_29_monitoring.md`

### ACT_30: 仿真总结报告
- **需求文档**: `docs/phase6_simulation/ACT_30_summary_requirements.md`
- **Review报告**: `docs/phase6_simulation/review_30_summary.md`

---

## Phase 7: RD-Agent部署（可选）

### ACT_31: 安装Docker Desktop
- **需求文档**: `docs/phase7_rdagent/ACT_31_docker_install_requirements.md`
- **Review报告**: `docs/phase7_rdagent/review_31_docker_install.md`

### ACT_32: 部署RD-Agent
- **需求文档**: `docs/phase7_rdagent/ACT_32_rdagent_install_requirements.md`
- **Review报告**: `docs/phase7_rdagent/review_32_rdagent_install.md`

### ACT_33: 配置LLM API
- **需求文档**: `docs/phase7_rdagent/ACT_33_llm_config_requirements.md`
- **Review报告**: `docs/phase7_rdagent/review_33_llm_config.md`

### ACT_34: 运行自动化因子挖掘
- **需求文档**: `docs/phase7_rdagent/ACT_34_factor_mining_requirements.md`
- **Review报告**: `docs/phase7_rdagent/review_34_factor_mining.md`

### ACT_35: 集成到TradingAgents
- **需求文档**: `docs/phase7_rdagent/ACT_35_integration_requirements.md`
- **Review报告**: `docs/phase7_rdagent/review_35_integration.md`

---

## 目录结构说明

```
US_AI_Quant/
├── docs/                           # 文档目录
│   ├── phase1_env_setup/          # Phase 1文档
│   ├── phase2_qlib_setup/         # Phase 2文档
│   └── ...
├── src/                           # 源代码
│   ├── data/                      # 数据层
│   ├── research/                  # 研究层（Qlib）
│   ├── agents/                    # 决策层（TradingAgents）
│   ├── execution/                 # 执行层（券商API）
│   ├── risk/                      # 风控层
│   ├── utils/                     # 工具
│   └── config/                    # 配置文件
├── tests/                         # 测试代码
│   ├── unit/                      # 单元测试
│   ├── integration/               # 集成测试
│   └── e2e/                       # 端到端测试
├── scripts/                       # 运维脚本
├── notebooks/                     # Jupyter笔记
├── configs/                       # 配置文件
│   ├── qlib/                      # Qlib配置
│   ├── futu/                      # 富途配置
│   └── agents/                    # Agents配置
├── logs/                          # 日志目录
├── results/                       # 结果输出
│   ├── backtest/                  # 回测结果
│   ├── signals/                   # 信号输出
│   └── factors/                   # 因子数据
├── requirements.txt               # Python依赖
├── .env.example                   # 环境变量模板
└── README.md                      # 项目说明
```

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

---

> 本文档随项目进展持续更新。
