# ACT_01: 安装Xcode Command Line Tools

## 1. ACT概述

### 1.1 目标
在Mac OS上安装Xcode Command Line Tools，提供C/C++编译器、make等基础开发工具，为后续编译Python C扩展（如Qlib的Cython代码）提供必需工具链。

### 1.2 范围
- 安装Xcode Command Line Tools
- 验证安装成功
- 记录安装过程和潜在问题

### 1.3 前置条件
- Mac OS系统（当前版本：macOS 26.4.1）
- 管理员权限（sudo）
- 网络连接（下载安装包）

## 2. 详细需求

### 2.1 功能需求
- 成功安装Xcode Command Line Tools
- 提供`gcc`、`clang`、`make`、`git`等命令行工具
- 支持Python 3.11的C扩展编译

### 2.2 技术需求
- 使用系统命令安装：`xcode-select --install`
- 验证安装：`xcode-select -p` 应返回有效路径
- 验证编译器：`clang --version` 应显示版本信息

### 2.3 依赖项
- 无外部依赖

## 3. 验收标准

### 3.1 完成定义
- [ ] Xcode Command Line Tools安装成功
- [ ] `xcode-select -p` 返回 `/Library/Developer/CommandLineTools`
- [ ] `clang --version` 显示版本信息
- [ ] `make --version` 显示版本信息
- [ ] Review报告已编写

### 3.2 测试标准
```bash
# 验证安装
xcode-select -p
clang --version
make --version
git --version
```

## 4. 注意事项

### 4.1 风险点
- 安装包较大（约1-2GB），下载时间取决于网络速度
- 可能需要Apple ID登录（某些版本）
- 安装过程需要用户交互（点击确认）

### 4.2 常见问题
**Q: 提示"无法安装软件，因为当前不可用"**
A: 检查网络连接，或从Apple Developer官网手动下载：https://developer.apple.com/download/

**Q: 安装后仍找不到编译器**
A: 运行 `sudo xcode-select --reset` 重置路径

### 4.3 最佳实践
- 确保有足够磁盘空间（至少5GB可用）
- 安装完成后重启终端
- 记录版本号便于后续排查

## 5. 参考资料
- Apple Developer文档：https://developer.apple.com/xcode/
- Xcode Command Line Tools官方指南
