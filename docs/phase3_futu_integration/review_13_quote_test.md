# Review Report: ACT_13 - 测试行情数据获取

## 验收状态: PASS

## 1. 验收概要

| 项目 | 内容 |
|------|------|
| ACT编号 | ACT_13 |
| ACT名称 | 测试行情数据获取 |
| 验收日期 | 2026-05-03 |
| 验收结果 | PASS |

## 2. 测试环境

| 组件 | 版本/信息 |
|------|-----------|
| futu-api | 10.04.6408 |
| FutuOpenD | 10.4.6408 |
| protobuf | 4.25.9 |
| 加密模式 | 禁用 |

## 3. 测试结果

### 3.1 股票快照（get_market_snapshot）

**测试代码**：
```python
from futu import SysConfig, OpenQuoteContext
SysConfig.enable_proto_encrypt(False)
ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
ret, data = ctx.get_market_snapshot(['US.AAPL', 'US.MSFT', 'US.TSLA'])
```

**结果**：PASS
| 股票 | 最新价 |
|------|--------|
| US.AAPL | $280.14 |
| US.MSFT | $414.44 |
| US.TSLA | $390.82 |

### 3.2 K线数据（request_history_kline）

**测试代码**：
```python
ret, data, _ = ctx.request_history_kline('US.AAPL', ktype=KLType.K_DAY, max_count=5)
```

**结果**：PASS
- 成功获取5日K线数据
- 包含 time_key, open, close, high, low, volume 等字段

**注意**：`get_cur_kline()` 在10.x版本参数有变化，推荐统一使用 `request_history_kline()` 并通过 `max_count` 控制数量。该方法返回3个值 `(ret, data, page_req_key)`。

### 3.3 实时订阅（subscribe / unsubscribe）

**测试代码**：
```python
ret, data = ctx.subscribe(['US.AAPL'], [SubType.QUOTE])
# ... 使用数据 ...
ret, data = ctx.unsubscribe(['US.AAPL'], [SubType.QUOTE])
```

**结果**：PASS
- 订阅成功，返回 RET_OK
- 取消订阅成功，返回 RET_OK

### 3.4 可用SubType枚举

| SubType | 说明 |
|---------|------|
| SubType.QUOTE | 实时报价 |
| SubType.K_DAY | 日K线 |
| SubType.K_1M | 1分钟K线 |
| SubType.K_5M | 5分钟K线 |
| SubType.TICKER | 逐笔 |
| SubType.ORDER_BOOK | 盘口 |

**注意**：不存在 `SubType.K_LINE`，需使用具体的K线类型。

## 4. API兼容性备注

| 旧API | 新API（10.x） | 说明 |
|-------|---------------|------|
| `RetType.SUCCEED` | `futu.RET_OK` (= 0) | 返回值常量 |
| `SubType.K_LINE` | `SubType.K_DAY` 等 | 需指定具体类型 |
| `get_cur_kline(count=N)` | `request_history_kline(max_count=N)` | 返回值数量不同 |
