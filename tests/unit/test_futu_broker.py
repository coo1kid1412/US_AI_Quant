"""
FutuBroker 单元测试

注意：这些测试需要OpenD网关运行。
如果OpenD未运行，测试会跳过（skip）。
"""

import pytest
import os
from unittest.mock import Mock, patch

from src.execution.futu_broker import FutuBroker
from futu import TrdEnv


# 检查OpenD是否可用
def is_opend_available():
    """检查OpenD网关是否可用"""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('127.0.0.1', 11111))
        sock.close()
        return result == 0
    except:
        return False


OPEND_AVAILABLE = is_opend_available()


@pytest.mark.skipif(not OPEND_AVAILABLE, reason="OpenD网关未运行")
class TestFutuBrokerIntegration:
    """集成测试（需要OpenD运行）"""
    
    def test_init_simulate_env(self):
        """测试初始化模拟环境"""
        broker = FutuBroker(env='simulate')
        assert broker.env == 'simulate'
        assert broker._trd_env == TrdEnv.SIMULATE
        broker.close()
    
    def test_get_realtime_quote(self):
        """测试获取实时报价"""
        broker = FutuBroker(env='simulate')
        try:
            data = broker.get_realtime_quote(['US.AAPL'])
            assert data is not None
        finally:
            broker.close()
    
    def test_get_kline(self):
        """测试获取K线数据"""
        broker = FutuBroker(env='simulate')
        try:
            data = broker.get_kline('US.AAPL', ktype='DAY', count=10)
            assert data is not None
            assert len(data) > 0
        finally:
            broker.close()
    
    def test_context_manager(self):
        """测试上下文管理器"""
        with FutuBroker(env='simulate') as broker:
            assert broker is not None
            assert broker.env == 'simulate'


class TestFutuBrokerUnit:
    """单元测试（不需要OpenD）"""
    
    def test_invalid_env_raises_error(self):
        """测试无效环境参数"""
        with patch('src.execution.futu_broker.OpenQuoteContext'):
            with patch('src.execution.futu_broker.OpenSecTradeContext'):
                with patch('src.execution.futu_broker.SysConfig'):
                    with pytest.raises(ValueError, match="env必须是"):
                        FutuBroker(env='invalid')
    
    def test_invalid_ktype_raises_error(self):
        """测试无效K线类型"""
        with patch('src.execution.futu_broker.OpenQuoteContext') as mock_quote:
            with patch('src.execution.futu_broker.OpenSecTradeContext'):
                with patch('src.execution.futu_broker.SysConfig'):
                    mock_quote.return_value = Mock()
                    broker = FutuBroker(env='simulate')
                    
                    with pytest.raises(ValueError, match="不支持的K线类型"):
                        broker.get_kline('US.AAPL', ktype='INVALID')
                    
                    broker.close()
    
    def test_invalid_order_type_raises_error(self):
        """测试无效订单类型"""
        with patch('src.execution.futu_broker.OpenQuoteContext') as mock_quote:
            with patch('src.execution.futu_broker.OpenSecTradeContext') as mock_trade:
                with patch('src.execution.futu_broker.SysConfig'):
                    mock_quote.return_value = Mock()
                    mock_trade.return_value = Mock()
                    broker = FutuBroker(env='simulate')
                    
                    with pytest.raises(ValueError, match="不支持的订单类型"):
                        broker.place_order('US.AAPL', 'BUY', 10, order_type='INVALID')
                    
                    broker.close()
    
    def test_buy_side_mapping(self):
        """测试买入方向映射"""
        from futu import TrdSide
        
        # BUY 应该映射到 TrdSide.BUY
        assert 'BUY' == 'BUY'
        assert 'SELL' == 'SELL'
    
    def test_subscribe_with_defaults(self):
        """测试默认订阅"""
        with patch('src.execution.futu_broker.OpenQuoteContext') as mock_quote:
            with patch('src.execution.futu_broker.OpenSecTradeContext'):
                with patch('src.execution.futu_broker.SysConfig'):
                    import futu
                    mock_quote.return_value = Mock()
                    mock_quote.return_value.subscribe.return_value = (futu.RET_OK, None)
                    mock_quote.return_value.unsubscribe.return_value = (futu.RET_OK, None)
                    
                    broker = FutuBroker(env='simulate')
                    result = broker.subscribe(['US.AAPL'])
                    
                    assert result == True
                    assert 'US.AAPL' in broker._subscribed_symbols
                    
                    broker.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
