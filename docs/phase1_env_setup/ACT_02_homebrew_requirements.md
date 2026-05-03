# ACT_02: 安装Homebrew包管理器

## 1. ACT概述

### 1.1 目标
安装Homebrew包管理器，为后续安装系统级依赖库（HDF5、libomp等）提供便捷的包管理工具。

### 1.2 范围
- 安装Homebrew
- 配置Homebrew环境
- 验证安装成功

### 1.3 前置条件
- ACT_01已完成（Xcode Command Line Tools已安装）
- Mac OS系统
- 网络连接

## 2. 详细需求

### 2.1 功能需求
- 成功安装Homebrew
- `brew`命令可用
- 能够安装和更新软件包

### 2.2 技术需求
- 使用官方安装脚本
- 配置PATH环境变量（如需）
- 运行 `brew update` 更新包索引

### 2.3 依赖项
- Xcode Command Line Tools（ACT_01）

## 3. 验收标准

### 3.1 完成定义
- [ ] Homebrew安装成功
- [ ] `brew --version` 显示版本信息
- [ ] `brew update` 执行成功
- [ ] `brew doctor` 无严重警告
- [ ] Review报告已编写

### 3.2 测试标准
```bash
brew --version
brew update
brew doctor
```

## 4. 注意事项

### 4.1 风险点
- 安装过程需要输入密码（sudo权限）
- 网络问题可能导致下载失败（特别是国内网络）
- 可能与现有包管理器冲突（如MacPorts）

### 4.2 常见问题
**Q: 安装脚本下载失败**
A: 使用国内镜像源或代理：
```bash
# 使用镜像安装
/bin/zsh -c "$(curl -fsSL https://mirrors.tuna.tsinghua.edu.cn/git/homebrew/install/raw/master/install.sh)"
```

**Q: brew update很慢**
A: 更换为国内镜像源：
```bash
export HOMEBREW_BREW_GIT_REMOTE="https://mirrors.tuna.tsinghua.edu.cn/git/homebrew/brew.git"
```

### 4.3 最佳实践
- 安装后运行 `brew doctor` 检查环境
- 定期运行 `brew update && brew upgrade`
- 不要使用sudo运行brew命令

## 5. 参考资料
- Homebrew官网：https://brew.sh/
- Homebrew国内镜像配置指南
