# -*- coding:utf-8 -*-

"""
DataMatrix样例演示

Project: alphahunter
Author: HJQuant
Description: Asynchronous driven quantitative trading framework
"""

import sys
import asyncio

from quant import const
from quant.error import Error
from quant.utils import tools, logger
from quant.config import config
from quant.market import Market, Kline, Orderbook, Trade, Ticker
from quant.tasks import LoopRunTask
from quant.gateway import ExchangeGateway
from quant.trader import Trader
from quant.strategy import Strategy
from quant.utils.decorator import async_method_locker
from quant.order import Order, Fill, ORDER_ACTION_BUY, ORDER_ACTION_SELL, ORDER_STATUS_FILLED, ORDER_TYPE_MARKET
from quant.position import Position
from quant.asset import Asset


class DataMatrixDemo(Strategy):

    def __init__(self):
        """ 初始化
        """
        super(DataMatrixDemo, self).__init__()
        
        platform = config.platforms[0]["platform"] #交易所
        symbols = config.markets[platform]["symbols"]
        # 交易模块参数
        params = {
            "strategy": config.strategy,
            "platform": const.DATAMATRIX, #接入datamatrix平台
            "databind": platform, #代表datamatrix所用历史数据所属交易所
            "symbols": symbols,

            "enable_kline_update": True,
            "enable_orderbook_update": True,
            "enable_trade_update": True,
            "enable_ticker_update": True,
            "enable_order_update": False,
            "enable_fill_update": False,
            "enable_position_update": False,
            "enable_asset_update": False,

            "direct_kline_update": True, #接入datamatrix平台,必须为True
            "direct_orderbook_update": True, #接入datamatrix平台,必须为True
            "direct_trade_update": True, #接入datamatrix平台,必须为True
            "direct_ticker_update": True #接入datamatrix平台,必须为True
        }
        self.trader = self.create_gateway(**params)

    async def on_init_success_callback(self, success: bool, error: Error, **kwargs):
        """ 初始化状态通知
        """
        logger.info("on_init_success_callback:", success, caller=self)

    async def on_kline_update_callback(self, kline: Kline):
        """ 市场K线更新
        """
        logger.info("kline:", kline, caller=self)
        # add some logic and calculations here.
        # await add_row(Row)        

    async def on_orderbook_update_callback(self, orderbook: Orderbook):
        """ 订单薄更新
        """
        logger.info("orderbook:", orderbook, caller=self)
        # add some logic and calculations here.
        # await add_row(Row)        

    async def on_trade_update_callback(self, trade: Trade):
        """ 市场最新成交更新
        """
        logger.info("trade:", trade, caller=self)
        # add some logic and calculations here.
        # await add_row(Row)        

    async def on_ticker_update_callback(self, ticker: Ticker):
        """ 市场行情tick更新
        """
        logger.info("ticker:", ticker, caller=self)
        # add some logic and calculations here.
        # await add_row(Row)

    async def add_row(self, Row):
        # add this Row to an existing csv file
        pass

    async def on_order_update_callback(self, order: Order): ...
    async def on_fill_update_callback(self, fill: Fill): ...
    async def on_position_update_callback(self, position: Position): ...
    async def on_asset_update_callback(self, asset: Asset): ...

    
def main():
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        config_file = None

    from quant.quant import quant
    quant.initialize(config_file)
    DataMatrixDemo()
    quant.start()


if __name__ == '__main__':
    main()