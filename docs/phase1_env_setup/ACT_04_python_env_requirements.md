# ACT_04: 创建Python虚拟环境

## 1. ACT概述

### 1.1 目标
创建Python 3.11虚拟环境，隔离项目依赖，避免与系统Python冲突。

### 1.2 范围
- 确认Python 3.11可用
- 创建虚拟环境
- 激活并验证环境

### 1.3 前置条件
- ACT_01已完成（Xcode CLI已安装）
- Python 3.11已安装（系统自带或通过brew安装）

## 2. 详细需求

### 2.1 功能需求
- 虚拟环境创建成功
- Python版本为3.11.x
- pip、setuptools、wheel已更新到最新

### 2.2 技术需求
```bash
# 创建虚拟环境
python3.11 -m venv ~/us_quant_env

# 激活环境
source ~/us_quant_env/bin/activate

# 升级基础工具
pip install --upgrade pip setuptools wheel
```

### 2.3 依赖项
- Python 3.11
- ACT_01（Xcode CLI，用于编译C扩展）

## 3. 验收标准

### 3.1 完成定义
- [ ] 虚拟环境创建成功
- [ ] Python版本为3.11.x
- [ ] pip版本已更新
- [ ] 环境激活正常
- [ ] Review报告已编写

### 3.2 测试标准
```bash
# 验证Python版本
python --version  # 应显示 Python 3.11.x

# 验证pip版本
pip --version

# 验证环境路径
which python  # 应指向虚拟环境目录
```

## 4. 注意事项

### 4.1 风险点
- 系统可能没有Python 3.11（需通过brew安装）
- 虚拟环境路径包含空格会导致问题
- 某些包可能需要Python 3.10（Qlib兼容性）

### 4.2 常见问题
**Q: python3.11命令不存在**
A: 通过Homebrew安装：
```bash
brew install python@3.11
```

**Q: 虚拟环境激活失败**
A: 检查shell类型：
```bash
# zsh（Mac默认）
source ~/us_quant_env/bin/activate

# 如果仍然失败，重新创建
rm -rf ~/us_quant_env
python3.11 -m venv ~/us_quant_env
```

### 4.3 最佳实践
- 虚拟环境放在用户目录（~/us_quant_env），避免路径问题
- 每次打开新终端都需要激活环境
- 考虑使用 `autoenv` 或 `direnv` 自动激活
- 定期升级pip和基础工具

## 5. 参考资料
- Python venv官方文档：https://docs.python.org/3/library/venv.html
- 虚拟环境最佳实践
