# ACT_07: 下载美股数据

## 1. ACT概述

### 1.1 目标
使用Qlib下载美股数据，包括OHLCV（开盘价、最高价、最低价、收盘价、成交量）等。

### 1.2 范围
- 下载美股数据到~/.qlib/qlib_data/us_data
- 使用Yahoo Finance数据源
- 验证下载完整性

### 1.3 前置条件
- ACT_06已完成（Qlib已安装）
- 网络连接（下载数据约1-2GB）

## 2. 详细需求

### 2.1 功能需求
- 美股数据下载成功
- 数据目录结构正确
- 包含标普500成分股数据

### 2.2 技术需求
```bash
python -m qlib.run.get_data qlib_data \
    --target_dir ~/.qlib/qlib_data/us_data \
    --region us
```

### 2.3 依赖项
- Qlib 0.9.7
- Yahoo Finance API

## 3. 验收标准

### 3.1 完成定义
- [ ] 数据下载完成
- [ ] 数据目录存在
- [ ] 包含至少100只股票数据
- [ ] Review报告已编写

### 3.2 测试标准
```bash
# 验证数据目录
ls ~/.qlib/qlib_data/us_data/

# 验证Qlib初始化
python -c "
import qlib
qlib.init(provider_uri='~/.qlib/qlib_data/us_data', region='us')
print('Qlib US data initialized!')
"
```

## 4. 注意事项

### 4.1 风险点
- 下载时间较长（取决于网络速度）
- Yahoo Finance可能限流
- 数据可能不完整（某些股票）

### 4.2 常见问题
**Q: 下载失败或中断**
A: 重新运行命令，Qlib支持断点续传

**Q: 数据不全**
A: 检查Yahoo Finance API限制，可手动补充

### 4.3 最佳实践
- 使用稳定的网络连接
- 预留至少5GB磁盘空间
- 记录下载时间便于后续参考

## 5. 参考资料
- Qlib数据下载文档：https://qlib.readthedocs.io/en/latest/component/data.html
