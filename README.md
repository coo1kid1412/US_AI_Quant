# US_AI_Quant - 美股AI量化交易系统

> 基于Qlib + 富途OpenAPI + TradingAgents的智能量化交易平台

## 项目简介

本项目旨在构建一个基于AI的美股量化交易系统，集成：
- **Qlib**: 微软AI量化研究框架
- **富途OpenAPI**: 美股程序化交易
- **TradingAgents**: 多智能体决策系统
- **RD-Agent** (可选): 自动化因子挖掘

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

## 下一步 (Phase 2)

- [ ] 下载美股数据 (Qlib --region us)
- [ ] 验证数据完整性
- [ ] 运行LightGBM示例Workflow
- [ ] Mac OS兼容性验证

## 重要提示

- **Python虚拟环境**: 每次开发前激活 `venv`
- **环境变量**: 复制 `.env.example` 为 `.env` 并填写真实值
- **富途OpenD**: 确保富途客户端已启动并OpenD运行

## 技术栈

- **语言**: Python 3.11
- **量化框架**: Qlib 0.9.7
- **券商API**: 富途OpenAPI
- **机器学习**: PyTorch, LightGBM, XGBoost
- **数据源**: Yahoo Finance (yfinance)
- **系统**: macOS Intel x86_64

---

**创建日期**: 2026-05-02
**最后更新**: 2026-05-02
**状态**: Phase 1 完成 ✅
