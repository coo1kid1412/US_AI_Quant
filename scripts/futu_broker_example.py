#!/usr/bin/env python
"""
FutuBroker 使用示例

演示如何使用FutuBroker进行：
1. 行情获取
2. 模拟交易
3. 账户查询

注意：需要OpenD网关运行才能执行
"""

import logging
from futu import SysConfig
from src.execution.futu_broker import FutuBroker

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    print("=" * 60)
    print("FutuBroker 使用示例")
    print("=" * 60)
    
    # 使用上下文管理器（推荐方式）
    with FutuBroker(env='simulate') as broker:
        print(f"\n环境: {broker.env}")
        
        # 1. 获取实时报价
        print("\n1. 获取实时报价...")
        symbols = ['US.AAPL', 'US.MSFT', 'US.GOOGL']
        quotes = broker.get_realtime_quote(symbols)
        
        if not quotes.empty:
            print(f"成功获取 {len(quotes)} 只股票报价")
            for _, row in quotes.iterrows():
                print(f"  {row.get('code', 'N/A')}: 最新价={row.get('last_price', 'N/A')}")
        else:
            print("获取报价失败（请检查OpenD是否运行）")
        
        # 2. 获取K线数据
        print("\n2. 获取AAPL日K线数据（最近10条）...")
        kline = broker.get_kline('US.AAPL', ktype='DAY', count=10)
        
        if not kline.empty:
            print(f"成功获取 {len(kline)} 条K线数据")
            print(kline[['time_key', 'close', 'volume']].tail(5))
        else:
            print("获取K线失败")
        
        # 3. 查询账户
        print("\n3. 查询模拟账户...")
        account = broker.get_account()
        
        if account:
            print(f"总资产: {account.get('total_assets', 'N/A')}")
            print(f"市值: {account.get('market_val', 'N/A')}")
            print(f"购买力: {account.get('max_power_short', 'N/A')}")
        else:
            print("查询账户失败")
        
        # 4. 查询持仓
        print("\n4. 查询持仓...")
        positions = broker.get_positions()
        
        if not positions.empty:
            print(f"持仓数量: {len(positions)}")
            print(positions[['code', 'qty', 'cost_price', 'pl_val']].head())
        else:
            print("无持仓")
        
        # 5. 示例：模拟下单（取消注释以测试）
        # print("\n5. 模拟下单...")
        # order_id = broker.place_order('US.AAPL', 'BUY', 10, price=150.0)
        # if order_id:
        #     print(f"下单成功，订单ID: {order_id}")
        #     # 查询订单
        #     orders = broker.get_orders()
        #     print(orders)
        #     # 撤单
        #     broker.cancel_order(order_id)
        
    print("\n" + "=" * 60)
    print("示例执行完成")
    print("=" * 60)


if __name__ == '__main__':
    main()
