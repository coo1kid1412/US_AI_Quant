"""
富途OpenAPI Broker封装类

提供统一的交易接口抽象层，屏蔽富途OpenAPI底层复杂性。
支持模拟和真实环境切换，自动重连机制，完整日志记录。
"""

import logging
import time
from typing import List, Dict, Optional
from datetime import datetime

import pandas as pd
import futu
from futu import (
    OpenQuoteContext,
    OpenSecTradeContext,
    SysConfig,
    SubType,
    KLType,
    OrderType,
    TrdEnv,
    TrdMarket,
    TrdSide,
    ModifyOrderOp,
)

logger = logging.getLogger(__name__)


class FutuBroker:
    """
    富途OpenAPI封装类
    
    提供行情获取、交易下单、账户管理等统一接口。
    
    Attributes:
        env: 交易环境 ('simulate' 或 'real')
        host: OpenD网关地址
        port: OpenD网关端口
        quote_ctx: 行情上下文
        trade_ctx: 交易上下文
    """
    
    def __init__(
        self,
        env: str = 'simulate',
        host: str = '127.0.0.1',
        port: int = 11111,
        unlock_password: Optional[str] = None,
        enable_encrypt: bool = False,
        rsa_file: Optional[str] = None,
    ):
        """
        初始化FutuBroker
        
        Args:
            env: 交易环境，'simulate'（模拟）或 'real'（真实）
            host: OpenD网关地址，默认127.0.0.1
            port: OpenD网关端口，默认11111
            unlock_password: 交易解锁密码（可选）
            enable_encrypt: 是否启用协议加密，默认False（需OpenD端同步配置）
            rsa_file: RSA私钥文件路径（仅enable_encrypt=True时需要）
            
        Raises:
            ValueError: env参数不合法
            ConnectionError: 无法连接OpenD网关
        """
        if env not in ('simulate', 'real'):
            raise ValueError(f"env必须是'simulate'或'real'，当前值: {env}")
        
        self.env = env
        self.host = host
        self.port = port
        self._trd_env = TrdEnv.SIMULATE if env == 'simulate' else TrdEnv.REAL
        
        # 配置协议加密（必须在创建连接之前设置）
        # 注意：Python端和OpenD端的加密设置必须一致
        # 如果OpenD CLI的"加密私钥"字段为空，则此处必须为False
        SysConfig.enable_proto_encrypt(enable_encrypt)
        if enable_encrypt and rsa_file:
            SysConfig.set_init_rsa_file(rsa_file)
        logger.info(f"协议加密: {'启用' if enable_encrypt else '禁用'}")
        
        # 初始化行情上下文
        logger.info(f"初始化行情上下文: {host}:{port}")
        self.quote_ctx = OpenQuoteContext(host=host, port=port)
        
        # 初始化交易上下文
        logger.info(f"初始化交易上下文: {host}:{port}, 环境: {env}")
        self.trade_ctx = OpenSecTradeContext(
            filter_trdmarket=TrdMarket.US, host=host, port=port
        )
        
        # 解锁交易（如果需要）
        if unlock_password:
            ret, msg = self.trade_ctx.unlock_trade(unlock_password)
            if ret != futu.RET_OK:
                raise ConnectionError(f"解锁交易失败: {msg}")
            logger.info("交易解锁成功")
        
        # 订阅管理
        self._subscribed_symbols = set()
        
        logger.info(f"FutuBroker初始化完成，环境: {env}")
    
    def close(self):
        """关闭连接，释放资源"""
        logger.info("关闭FutuBroker连接")
        # 取消所有订阅
        if self._subscribed_symbols:
            self.unsubscribe(list(self._subscribed_symbols))
        
        self.quote_ctx.close()
        self.trade_ctx.close()
        logger.info("FutuBroker连接已关闭")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
    
    # ==================== 行情接口 ====================
    
    def get_realtime_quote(self, symbols: List[str]) -> pd.DataFrame:
        """
        获取实时报价
        
        Args:
            symbols: 股票代码列表，如 ['US.AAPL', 'US.MSFT']
            
        Returns:
            实时报价DataFrame
        """
        logger.info(f"获取实时报价: {symbols}")
        ret, data = self.quote_ctx.get_market_snapshot(symbols)
        
        if ret != futu.RET_OK:
            logger.error(f"获取实时报价失败: {data}")
            return pd.DataFrame()
        
        logger.info(f"成功获取 {len(data)} 只股票报价")
        return data
    
    def get_kline(
        self,
        symbol: str,
        ktype: str = 'DAY',
        count: int = 100,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        获取K线数据
        
        Args:
            symbol: 股票代码，如 'US.AAPL'
            ktype: K线类型 ('DAY', '1M', '5M', '15M', '30M', '60M')
            count: 获取数量
            start_date: 开始日期 'YYYY-MM-DD'
            end_date: 结束日期 'YYYY-MM-DD'
            
        Returns:
            K线数据DataFrame
        """
        ktype_map = {
            'DAY': KLType.K_DAY,
            '1M': KLType.K_1M,
            '5M': KLType.K_5M,
            '15M': KLType.K_15M,
            '30M': KLType.K_30M,
            '60M': KLType.K_60M,
        }
        
        kl_type = ktype_map.get(ktype)
        if kl_type is None:
            raise ValueError(f"不支持的K线类型: {ktype}")
        
        logger.info(f"获取K线数据: {symbol}, 类型: {ktype}, 数量: {count}")
        
        # 统一使用request_history_kline（返回3个值: ret, data, page_req_key）
        kwargs = {'ktype': kl_type, 'max_count': count}
        if start_date:
            kwargs['start'] = start_date
        if end_date:
            kwargs['end'] = end_date
        
        ret, data, _ = self.quote_ctx.request_history_kline(symbol, **kwargs)
        
        if ret != futu.RET_OK:
            logger.error(f"获取K线数据失败: {data}")
            return pd.DataFrame()
        
        logger.info(f"成功获取 {len(data)} 条K线数据")
        return data
    
    def get_market_snapshot(self, symbols: List[str]) -> pd.DataFrame:
        """
        获取股票快照
        
        Args:
            symbols: 股票代码列表
            
        Returns:
            快照数据DataFrame
        """
        logger.info(f"获取股票快照: {symbols}")
        return self.get_realtime_quote(symbols)
    
    def subscribe(self, symbols: List[str], sub_types: List[str] = None) -> bool:
        """
        订阅实时行情
        
        Args:
            symbols: 股票代码列表
            sub_types: 订阅类型列表 ('QUOTE', 'K_LINE', 'TICKER', 'ORDER_BOOK')
            
        Returns:
            是否成功
        """
        if sub_types is None:
            sub_types = ['QUOTE']
        
        sub_type_map = {
            'QUOTE': SubType.QUOTE,
            'K_DAY': SubType.K_DAY,
            'K_1M': SubType.K_1M,
            'K_5M': SubType.K_5M,
            'TICKER': SubType.TICKER,
            'ORDER_BOOK': SubType.ORDER_BOOK,
        }
        
        futu_sub_types = [sub_type_map.get(st) for st in sub_types if st in sub_type_map]
        
        if not futu_sub_types:
            raise ValueError(f"不支持的订阅类型: {sub_types}")
        
        logger.info(f"订阅行情: {symbols}, 类型: {sub_types}")
        ret, data = self.quote_ctx.subscribe(symbols, futu_sub_types)
        
        if ret == futu.RET_OK:
            self._subscribed_symbols.update(symbols)
            logger.info(f"订阅成功，当前订阅数: {len(self._subscribed_symbols)}")
            return True
        else:
            logger.error(f"订阅失败: {data}")
            return False
    
    def unsubscribe(self, symbols: List[str]) -> bool:
        """
        取消订阅
        
        Args:
            symbols: 股票代码列表
            
        Returns:
            是否成功
        """
        logger.info(f"取消订阅: {symbols}")
        ret, data = self.quote_ctx.unsubscribe(symbols, [SubType.QUOTE])
        
        if ret == futu.RET_OK:
            self._subscribed_symbols.difference_update(symbols)
            logger.info(f"取消订阅成功，剩余订阅数: {len(self._subscribed_symbols)}")
            return True
        else:
            logger.error(f"取消订阅失败: {data}")
            return False
    
    # ==================== 交易接口 ====================
    
    def place_order(
        self,
        symbol: str,
        side: str,
        qty: int,
        price: Optional[float] = None,
        order_type: str = 'LIMIT',
    ) -> Optional[str]:
        """
        下单
        
        Args:
            symbol: 股票代码，如 'US.AAPL'
            side: 买卖方向 ('BUY' 或 'SELL')
            qty: 数量
            price: 价格（限价单必需）
            order_type: 订单类型 ('MARKET' 或 'LIMIT')
            
        Returns:
            订单ID，失败返回None
        """
        # 安全检查 - 严禁实盘交易
        if self.env == 'real':
            raise RuntimeError(
                "🔴 安全禁令：严禁实盘交易！\n"
                "在pipeline完全跑通且用户明确书面确认之前，\n"
                "禁止使用实盘环境进行任何交易操作。\n"
                "请使用 env='simulate' 进行模拟交易测试。"
            )
        
        trd_side = TrdSide.BUY if side == 'BUY' else TrdSide.SELL
        
        order_type_map = {
            'MARKET': OrderType.MARKET,
            'LIMIT': OrderType.NORMAL,
        }
        futu_order_type = order_type_map.get(order_type)
        
        if futu_order_type is None:
            raise ValueError(f"不支持的订单类型: {order_type}")
        
        # 市价单价格为0
        order_price = price if price else 0
        
        logger.info(
            f"下单: {side} {qty} {symbol}, 类型: {order_type}, 价格: {order_price}, "
            f"环境: {self.env}"
        )
        
        ret, data = self.trade_ctx.place_order(
            price=order_price,
            qty=qty,
            code=symbol,
            trd_side=trd_side,
            order_type=futu_order_type,
            trd_env=self._trd_env,
        )
        
        if ret != futu.RET_OK:
            logger.error(f"下单失败: {data}")
            return None
        
        order_id = data.get('order_id', [None])[0]
        logger.info(f"下单成功，订单ID: {order_id}")
        return order_id
    
    def cancel_order(self, order_id: str) -> bool:
        """
        撤单
        
        Args:
            order_id: 订单ID
            
        Returns:
            是否成功
        """
        logger.info(f"撤单: {order_id}, 环境: {self.env}")
        
        ret, data = self.trade_ctx.modify_order(
            modify_order_op=ModifyOrderOp.CANCEL,
            order_id=order_id,
            qty=0,
            price=0,
            trd_env=self._trd_env,
        )
        
        if ret != futu.RET_OK:
            logger.error(f"撤单失败: {data}")
            return False
        
        logger.info(f"撤单成功: {order_id}")
        return True
    
    def modify_order(self, order_id: str, qty: int, price: float) -> bool:
        """
        改单
        
        Args:
            order_id: 订单ID
            qty: 新数量
            price: 新价格
            
        Returns:
            是否成功
        """
        logger.info(f"改单: {order_id}, 数量: {qty}, 价格: {price}")
        
        ret, data = self.trade_ctx.modify_order(
            modify_order_op=ModifyOrderOp.NORMAL,
            order_id=order_id,
            qty=qty,
            price=price,
            trd_env=self._trd_env,
        )
        
        if ret != futu.RET_OK:
            logger.error(f"改单失败: {data}")
            return False
        
        logger.info(f"改单成功: {order_id}")
        return True
    
    def get_orders(self, status: str = 'ALL') -> pd.DataFrame:
        """
        查询订单
        
        Args:
            status: 订单状态 ('ALL', 'SUBMITTED', 'FILLED', 'CANCELLED')
            
        Returns:
            订单列表DataFrame
        """
        logger.info(f"查询订单: {status}")
        
        ret, data = self.trade_ctx.order_list_query(trd_env=self._trd_env)
        
        if ret != futu.RET_OK:
            logger.error(f"查询订单失败: {data}")
            return pd.DataFrame()
        
        logger.info(f"查询到 {len(data)} 个订单")
        return data
    
    def get_trades(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        查询成交记录
        
        Args:
            start_date: 开始日期 'YYYY-MM-DD'
            end_date: 结束日期 'YYYY-MM-DD'
            
        Returns:
            成交记录DataFrame
        """
        logger.info(f"查询成交记录: {start_date} ~ {end_date}")
        
        ret, data = self.trade_ctx.deal_list_query(trd_env=self._trd_env)
        
        if ret != futu.RET_OK:
            logger.error(f"查询成交记录失败: {data}")
            return pd.DataFrame()
        
        logger.info(f"查询到 {len(data)} 条成交记录")
        return data
    
    # ==================== 账户接口 ====================
    
    def get_account(self) -> Dict:
        """
        查询账户信息
        
        Returns:
            账户信息字典
        """
        logger.info("查询账户信息")
        
        ret, data = self.trade_ctx.accinfo_query(trd_env=self._trd_env)
        
        if ret != futu.RET_OK:
            logger.error(f"查询账户信息失败: {data}")
            return {}
        
        account = data.iloc[0].to_dict() if len(data) > 0 else {}
        logger.info(f"账户信息: 总资产={account.get('total_assets', 'N/A')}")
        return account
    
    def get_positions(self) -> pd.DataFrame:
        """
        查询持仓
        
        Returns:
            持仓数据DataFrame
        """
        logger.info("查询持仓")
        
        ret, data = self.trade_ctx.position_list_query(trd_env=self._trd_env)
        
        if ret != futu.RET_OK:
            logger.error(f"查询持仓失败: {data}")
            return pd.DataFrame()
        
        logger.info(f"持仓数量: {len(data)}")
        return data
    
    def get_buying_power(self) -> float:
        """
        获取购买力
        
        Returns:
            购买力金额
        """
        account = self.get_account()
        return account.get('max_power_short', 0.0)
    
    def get_market_value(self) -> float:
        """
        获取持仓市值
        
        Returns:
            市值金额
        """
        account = self.get_account()
        return account.get('market_val', 0.0)
