# ACT_15: 实现FutuBroker封装类

## 1. ACT概述

### 1.1 目标
封装富途OpenAPI为统一的Broker接口类，提供简洁的交易抽象层，便于TradingAgents和Qlib调用，屏蔽底层API复杂性。

### 1.2 范围
- 设计Broker接口抽象
- 实现行情获取方法
- 实现交易下单方法
- 实现账户管理方法
- 实现订阅管理方法
- 编写单元测试

### 1.3 前置条件
- ACT_11至ACT_14已完成
- futu-api SDK工作正常
- 模拟交易测试通过

## 2. 详细需求

### 2.1 功能需求

#### 2.1.1 行情接口
```python
class FutuBroker:
    def get_realtime_quote(self, symbols: List[str]) -> pd.DataFrame
    def get_kline(self, symbol: str, ktype: str, count: int) -> pd.DataFrame
    def get_market_snapshot(self, symbols: List[str]) -> pd.DataFrame
    def subscribe(self, symbols: List[str], sub_types: List[str]) -> bool
    def unsubscribe(self, symbols: List[str]) -> bool
```

#### 2.1.2 交易接口
```python
    def place_order(self, symbol: str, side: str, qty: int, 
                    price: float = None, order_type: str = 'LIMIT') -> str
    def cancel_order(self, order_id: str) -> bool
    def modify_order(self, order_id: str, qty: int, price: float) -> bool
    def get_orders(self, status: str = 'ALL') -> pd.DataFrame
    def get_trades(self, start_date: str = None, end_date: str = None) -> pd.DataFrame
```

#### 2.1.3 账户接口
```python
    def get_account(self) -> dict
    def get_positions(self) -> pd.DataFrame
    def get_buying_power(self) -> float
    def get_market_value(self) -> float
```

### 2.2 技术需求
- 使用Python类封装
- 支持模拟和真实环境切换
- 自动重连机制（断线重连）
- 日志记录所有操作
- 错误处理统一异常
- 线程安全（支持多线程调用）

### 2.3 依赖项
- futu-api SDK
- OpenD网关运行
- 模拟账户配置

## 3. 验收标准

### 3.1 完成定义
- [ ] FutuBroker类实现完成
- [ ] 行情接口测试通过
- [ ] 交易接口测试通过
- [ ] 账户接口测试通过
- [ ] 自动重连机制工作正常
- [ ] 日志记录完整
- [ ] 单元测试覆盖率>80%
- [ ] Review报告已编写

### 3.2 测试标准
```python
# 测试脚本：tests/unit/test_futu_broker.py
from src.execution.futu_broker import FutuBroker

# 1. 初始化
broker = FutuBroker(env='simulate', host='127.0.0.1', port=11111)

# 2. 行情测试
quotes = broker.get_realtime_quote(['US.AAPL', 'US.MSFT'])
assert len(quotes) == 2

kline = broker.get_kline('US.AAPL', 'DAY', 100)
assert len(kline) == 100

# 3. 账户测试
account = broker.get_account()
assert 'total_assets' in account

positions = broker.get_positions()
assert isinstance(positions, pd.DataFrame)

# 4. 交易测试
order_id = broker.place_order('US.AAPL', 'BUY', 10, price=150.0)
assert order_id is not None

success = broker.cancel_order(order_id)
assert success == True
```

## 4. 注意事项

### 4.1 风险点
- 环境切换错误可能导致真实交易（必须有保护机制）
- 并发调用可能导致订阅超限
- 重连机制可能陷入死循环
- 日志可能包含敏感信息（需脱敏）

### 4.2 常见问题
**Q: 如何防止误操作真实账户？**
A: 
1. 构造函数显式指定env参数
2. 所有交易方法打印环境信息
3. 真实环境需要二次确认
4. 使用环境变量控制

**Q: 如何处理断线重连？**
A: 
1. 捕获连接异常
2. 等待后重试（指数退避）
3. 超过最大重试次数后抛出异常
4. 记录重连日志

**Q: 如何管理订阅额度？**
A: 
1. 内部维护订阅状态
2. 自动取消过期订阅
3. 提供查询剩余额度方法
4. 批量操作减少订阅次数

### 4.3 最佳实践
- 使用上下文管理器管理连接生命周期
- 所有公开方法都有docstring
- 错误信息包含足够上下文
- 使用类型提示（Type Hints）
- 关键操作有日志记录

## 5. 参考资料
- 富途OpenAPI完整文档：https://openapi.futunn.com/futu-api-doc/
- Broker设计模式：https://openapi.futunn.com/futu-api-doc/intro/design.html
- Python最佳实践：https://docs.python.org/3/howto/index.html
