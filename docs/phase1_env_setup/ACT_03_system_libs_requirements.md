# ACT_03: 安装系统依赖库

## 1. ACT概述

### 1.1 目标
安装Qlib和机器学习库编译所需的系统级依赖：
- **HDF5**：Qlib数据存储依赖
- **libomp**：LightGBM编译所需的OpenMP支持

### 1.2 范围
- 使用Homebrew安装HDF5
- 使用Homebrew安装libomp
- 验证库文件安装正确

### 1.3 前置条件
- ACT_02已完成（Homebrew已安装）
- 网络连接

## 2. 详细需求

### 2.1 功能需求
- HDF5库和头文件可用
- libomp库和头文件可用
- 环境变量正确配置

### 2.2 技术需求
```bash
brew install hdf5 libomp
```
- 设置编译环境变量：
  - `HDF5_DIR=$(brew --prefix hdf5)`
  - `LDFLAGS="-L$(brew --prefix libomp)/lib"`
  - `CPPFLAGS="-I$(brew --prefix libomp)/include"`

### 2.3 依赖项
- Homebrew（ACT_02）

## 3. 验收标准

### 3.1 完成定义
- [ ] HDF5安装成功
- [ ] libomp安装成功
- [ ] `brew list hdf5` 显示文件列表
- [ ] `brew list libomp` 显示文件列表
- [ ] 环境变量配置正确
- [ ] Review报告已编写

### 3.2 测试标准
```bash
# 验证HDF5
brew list hdf5
ls $(brew --prefix hdf5)/lib/

# 验证libomp
brew list libomp
ls $(brew --prefix libomp)/lib/

# 测试编译（后续Python安装时使用）
export HDF5_DIR=$(brew --prefix hdf5)
export LDFLAGS="-L$(brew --prefix libomp)/lib"
export CPPFLAGS="-I$(brew --prefix libomp)/include"
```

## 4. 注意事项

### 4.1 风险点
- HDF5编译时间较长（约5-10分钟）
- Intel Mac和Apple Silicon路径不同
- 某些Python包可能找不到HDF5（需手动设置环境变量）

### 4.2 常见问题
**Q: pip install h5py 失败，找不到HDF5**
A: 设置环境变量：
```bash
export HDF5_DIR=$(brew --prefix hdf5)
pip install h5py
```

**Q: LightGBM编译失败，libomp not found**
A: 确保libomp已安装，并设置LDFLAGS和CPPFLAGS

### 4.3 最佳实践
- 记录brew安装路径，后续编译Python包时使用
- 将环境变量添加到 `.zshrc` 或虚拟环境激活脚本
- 使用 `brew info <package>` 查看详细信息

## 5. 参考资料
- HDF5官方文档：https://www.hdfgroup.org/solutions/hdf5/
- LightGBM Mac OS安装指南：https://lightgbm.readthedocs.io/en/latest/Installation-Guide.html
