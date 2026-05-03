# ACT_11: 安装富途OpenAPI SDK

## 1. ACT概述

### 1.1 目标
安装并配置富途OpenAPI Python SDK（futu-api），实现与富途OpenD网关的通信能力，为后续行情获取和交易执行提供基础。

### 1.2 范围
- 验证futu-api是否已安装
- 升级到最新稳定版本
- 测试SDK导入和基本功能
- 编写SDK使用示例代码

### 1.3 前置条件
- Python 3.11虚拟环境已激活
- futu-api已通过requirements.txt安装（版本：10.04.6408）
- 富途OpenD网关已安装（需用户手动安装富途牛牛客户端）

## 2. 详细需求

### 2.1 功能需求
- futu-api SDK安装成功，可正常导入
- 验证SDK版本信息
- 测试基础类导入（OpenQuoteContext、OpenSecTradeContext等）
- 编写连接测试脚本

### 2.2 技术需求
- SDK版本：>=10.04.6408
- Python版本兼容性：支持Python 3.8-3.11
- 依赖protobuf库正确安装
- 网络连接测试（本地OpenD默认端口11111）

### 2.3 依赖项
- 富途牛牛客户端（Mac版）已安装
- OpenD网关已启动并监听端口
- RSA密钥对配置（用于加密通信）

## 3. 验收标准

### 3.1 完成定义
- [ ] futu-api安装成功，版本号>=10.04.6408
- [ ] `import futu` 无错误
- [ ] 基础类可正常实例化
- [ ] 连接测试脚本编写完成
- [ ] Review报告已编写

### 3.2 测试标准
```python
# 测试1: SDK导入
import futu
print(f"futu-api version: {futu.__version__}")

# 测试2: 基础类导入
from futu import OpenQuoteContext, OpenSecTradeContext
from futu import SubType, RetType

# 测试3: 连接测试（需OpenD运行）
quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
ret, data = quote_ctx.get_market_snapshot(['US.AAPL'])
print(f"Ret: {ret}, Data shape: {data.shape if ret == 0 else 'N/A'}")
```

## 4. 注意事项

### 4.1 风险点
- OpenD网关未启动会导致连接失败
- 富途牛牛客户端需要保持登录状态
- 未订阅的行情类型会返回空数据
- 免费版OpenD有订阅额度限制（最多同时订阅100只股票）

### 4.2 常见问题
**Q: ImportError: No module named 'futu'**
A: 检查虚拟环境是否激活，运行 `pip install futu-api`

**Q: 连接超时或拒绝**
A: 
1. 确认OpenD网关已启动
2. 检查端口是否正确（默认11111）
3. 确认防火墙未阻止连接

**Q: 行情订阅失败**
A: 
1. 确认富途牛牛已登录
2. 检查订阅额度是否用完
3. 确认股票代码格式正确（US.AAPL格式）

### 4.3 最佳实践
- 使用上下文管理器管理连接生命周期
- 及时取消不需要的订阅（释放额度）
- 错误处理要检查RetType返回值
- 日志记录所有API调用便于调试

## 5. 参考资料
- 富途OpenAPI文档：https://openapi.futunn.com/futu-api-doc/
- futu-api GitHub：https://github.com/FutunnOpen/py-futu-api
- OpenD下载：https://www.futunn.com/download/openAPI
