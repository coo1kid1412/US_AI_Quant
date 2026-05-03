# ACT_14: 测试模拟交易下单

## 1. ACT概述

### 1.1 目标
通过富途OpenAPI在模拟环境下完成交易下单测试，验证交易接口的完整性和安全性。

### 1.2 范围
- 配置模拟交易环境
- 查询模拟账户资产
- 测试市价单下单
- 测试限价单下单
- 测试撤单功能
- 查询订单状态

### 1.3 前置条件
- 富途OpenD网关已启动
- 模拟交易账户已开通
- futu-api SDK已安装

## 2. 详细需求

### 2.1 功能需求
- 查询模拟账户资产和持仓
- 市价单下单（OrderType.MARKET）
- 限价单下单（OrderType.NORMAL）
- 修改订单价格
- 撤销未成交订单
- 查询当日订单列表
- 查询历史成交记录

### 2.2 技术需求
- 交易环境：SIMULATE（模拟环境）
- 市场：美股市场（TrdMarket.US）
- 订单类型：市价单、限价单
- 支持做空测试
- 错误处理：余额不足、价格异常等

### 2.3 依赖项
- OpenD网关运行中
- 模拟账户有足够资金
- 交易时段内测试（美股交易时间）

## 3. 验收标准

### 3.1 完成定义
- [ ] 模拟账户资产查询成功
- [ ] 市价单下单成功并成交
- [ ] 限价单下单成功
- [ ] 撤单功能测试通过
- [ ] 订单状态查询正确
- [ ] 成交记录查询正确
- [ ] Review报告已编写

### 3.2 测试标准
```python
# 测试脚本：tests/integration/test_futu_trade.py
from futu import OpenSecTradeContext, TrdEnv, OrderType, TrdMarket

# 1. 初始化交易上下文
trade_ctx = OpenSecTradeContext(filter_trdmarket=TrdMarket.US)
trade_ctx.set_global_state(1)  # 解锁交易

# 2. 查询资产
ret, data = trade_ctx.accinfo_query(trd_env=TrdEnv.SIMULATE)
assert ret == 0 and not data.empty

# 3. 市价单下单
ret, data = trade_ctx.place_order(price=0, qty=10, code='US.AAPL', 
                                   trd_side='BUY', order_type=OrderType.MARKET,
                                   trd_env=TrdEnv.SIMULATE)
assert ret == 0

# 4. 查询订单
ret, data = trade_ctx.order_list_query(trd_env=TrdEnv.SIMULATE)
assert ret == 0

# 5. 撤单
ret, data = trade_ctx.modify_order(modify_order_op='CANCEL', order_id='xxx', 
                                    qty=0, price=0, trd_env=TrdEnv.SIMULATE)
assert ret == 0
```

## 4. 注意事项

### 4.1 风险点
- **严重警告**：测试时务必确认trd_env=TrdEnv.SIMULATE，避免真实交易
- 模拟账户资金有限，合理测试
- 市价单会立即成交，测试前确认价格可接受
- 非交易时段下单会进入待处理状态

### 4.2 常见问题
**Q: 交易接口返回权限不足**
A: 
1. 确认使用的是SIMULATE环境
2. 检查是否已解锁交易（set_global_state）
3. 确认OpenD已登录

**Q: 订单未成交**
A: 
1. 限价单价格偏离市场价太远
2. 非交易时段
3. 股票流动性差

**Q: 撤单失败**
A: 
1. 订单已成交或部分成交
2. 订单ID不正确
3. 订单已撤销

### 4.3 最佳实践
- **永远先测试模拟环境**
- 下单前双重确认环境和股票代码
- 使用限价单而非市价单进行测试（更可控）
- 记录所有订单ID便于追踪
- 测试完成后撤销所有未成交订单

## 5. 参考资料
- 交易接口：https://openapi.futunn.com/futu-api-doc/trade/PlaceOrder.html
- 订单类型说明：https://openapi.futunn.com/futu-api-doc/trade/OrderType.html
- 模拟交易指南：https://openapi.futunn.com/futu-api-doc/introduction/SimulateTrading.html
