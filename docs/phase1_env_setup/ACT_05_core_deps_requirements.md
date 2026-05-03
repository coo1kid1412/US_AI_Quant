# ACT_05: 安装核心Python依赖

## 1. ACT概述

### 1.1 目标
安装项目核心Python依赖包，包括Qlib、富途OpenAPI SDK、机器学习库等。

### 1.2 范围
- 安装Qlib（pyqlib）
- 安装富途OpenAPI SDK（futu-api）
- 安装机器学习库（torch、lightgbm、xgboost、scikit-learn）
- 安装数据处理库（pandas、numpy、scipy）
- 安装工具库（python-dotenv、requests、pyyaml、tqdm）

### 1.3 前置条件
- ACT_03已完成（系统依赖库已安装）
- ACT_04已完成（Python虚拟环境已创建并激活）
- 网络连接

## 2. 详细需求

### 2.1 功能需求
- 所有依赖包安装成功
- 无编译错误
- 库导入正常

### 2.2 技术需求
```bash
# 设置编译环境变量
export HDF5_DIR=$(brew --prefix hdf5)
export LDFLAGS="-L$(brew --prefix libomp)/lib"
export CPPFLAGS="-I$(brew --prefix libomp)/include"

# 安装预编译依赖
pip install numpy cython

# 安装Qlib
pip install pyqlib

# 安装其他依赖
pip install futu-api yfinance
pip install lightgbm xgboost scikit-learn
pip install torch pandas scipy
pip install python-dotenv requests pyyaml tqdm
```

### 2.3 依赖项
- ACT_03（HDF5、libomp）
- ACT_04（Python虚拟环境）

## 3. 验收标准

### 3.1 完成定义
- [ ] pyqlib安装成功
- [ ] futu-api安装成功
- [ ] lightgbm安装成功
- [ ] torch安装成功
- [ ] 所有库可正常导入
- [ ] Review报告已编写

### 3.2 测试标准
```python
# 验证导入
import qlib
import futu
import lightgbm
import torch
import pandas
import numpy

print(f"Qlib {qlib.__version__}")
print(f"LightGBM {lightgbm.__version__}")
print(f"PyTorch {torch.__version__}")
```

## 4. 注意事项

### 4.1 风险点
- **pyqlib编译时间长**（约5-15分钟）
- **torch包较大**（约500MB-1GB）
- **Cython编译错误**（需确保Xcode CLI已安装）
- **内存不足**（编译时可能需要4GB+内存）

### 4.2 常见问题
**Q: pyqlib安装失败，提示找不到HDF5**
A: 确保环境变量已设置：
```bash
export HDF5_DIR=$(brew --prefix hdf5)
pip install pyqlib
```

**Q: LightGBM安装失败，libomp not found**
A: 
```bash
brew install libomp
export LDFLAGS="-L$(brew --prefix libomp)/lib"
export CPPFLAGS="-I$(brew --prefix libomp)/include"
pip install lightgbm
```

**Q: torch安装很慢或失败**
A: 使用官方索引：
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### 4.3 最佳实践
- 先安装numpy和cython，再安装pyqlib
- 使用国内PyPI镜像加速（如清华源）：
  ```bash
  pip install -i https://pypi.tuna.tsinghua.edu.cn/simple <package>
  ```
- 记录安装时间和包版本，便于后续复现
- 如遇到编译错误，先检查Xcode CLI和系统依赖

## 5. 参考资料
- Qlib安装指南：https://qlib.readthedocs.io/en/latest/start/install.html
- PyTorch安装指南：https://pytorch.org/get-started/locally/
- LightGBM Mac OS安装：https://lightgbm.readthedocs.io/en/latest/Installation-Guide.html
