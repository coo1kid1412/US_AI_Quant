# ACT_13: 测试行情数据获取

## 1. ACT概述

### 1.1 目标
通过富途OpenAPI获取美股实时行情数据，验证行情订阅和数据获取功能的完整性和准确性。

### 1.2 范围
- 订阅美股实时报价
- 获取K线数据（日K、分钟K）
- 获取逐笔成交数据
- 获取买卖盘口数据
- 测试多股票并发订阅

### 1.3 前置条件
- 富途OpenD网关已启动并连接
- futu-api SDK已安装
- 富途牛牛已登录

## 2. 详细需求

### 2.1 功能需求
- 实时报价订阅（SubType.QUOTE）
- K线数据获取（SubType.K_1M, SubType.K_DAY）
- 逐笔成交订阅（SubType.TICKER）
- 买卖盘口订阅（SubType.ORDER_BOOK）
- 股票快照获取

### 2.2 技术需求
- 支持股票代码格式：US.AAPL, US.MSFT, US.TSLA等
- K线时间范围：最近30个交易日
- 订阅后及时取消（释放额度）
- 错误处理：重试机制和超时控制

### 2.3 依赖项
- OpenD网关运行中
- 订阅额度充足
- 网络稳定

## 3. 验收标准

### 3.1 完成定义
- [ ] 实时报价获取成功
- [ ] 日K线数据获取成功（至少100条）
- [ ] 分钟K线数据获取成功（至少50条）
- [ ] 逐笔成交数据获取成功
- [ ] 买卖盘口数据获取成功
- [ ] 多股票订阅测试通过
- [ ] Review报告已编写

### 3.2 测试标准
```python
# 测试脚本：tests/integration/test_futu_quote.py
# 1. 获取股票快照
ret, data = quote_ctx.get_market_snapshot(['US.AAPL'])
assert ret == 0 and not data.empty

# 2. 获取日K线
ret, data = quote_ctx.request_history_kline('US.AAPL', ktype=KLType.K_DAY, max_count=100)
assert ret == 0 and len(data) == 100

# 3. 订阅实时报价
ret, data = quote_ctx.subscribe(['US.AAPL'], [SubType.QUOTE])
assert ret == 0

# 4. 获取订阅信息
ret, data = quote_ctx.query_subscription()
assert ret == 0
```

## 4. 注意事项

### 4.1 风险点
- 订阅额度有限（免费版100只）
- 高频订阅可能被限流
- 盘前盘后行情与常规时段不同
- 美股交易时段：美东时间9:30-16:00（北京时间21:30-次日4:00）

### 4.2 常见问题
**Q: 订阅失败，返回额度不足**
A: 取消不需要的订阅，或减少同时订阅的股票数量

**Q: K线数据不完整**
A: 
1. 确认时间范围设置正确
2. 检查股票是否停牌
3. 确认交易时段

**Q: 实时数据不更新**
A: 
1. 确认订阅成功
2. 检查网络连接
3. 确认OpenD正常运行

### 4.3 最佳实践
- 订阅前检查是否已订阅（避免重复）
- 使用完毕后立即取消订阅
- 批量获取使用get_market_snapshot而非逐个订阅
- 记录订阅状态便于调试

## 5. 参考资料
- 订阅指南：https://openapi.futunn.com/futu-api-doc/quote/Subscribe.html
- 行情类型说明：https://openapi.futunn.com/futu-api-doc/quote/Subscription.html
- K线接口：https://openapi.futunn.com/futu-api-doc/quote/RequestHistoryKline.html
