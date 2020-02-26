# -*- coding: utf-8 -*-
import asyncio
import math

from pymongo import UpdateOne, InsertOne

from models import Trade, Symbol, Exchange, Kline


one_day = 60 * 60 * 24 * 1000
LIMIT = 500


async def main():
    begin_timestamp = 1575129600000  # 开始时间, 12-1 00:00:00.000
    # end_timestamp = 1578585600000  # 结束时间 01-10  00:00:00.000
    end_timestamp = begin_timestamp + one_day * 2
    for begin_dt in range(begin_timestamp, end_timestamp, one_day):
        await day_loop(begin_dt)
    # 计算
    # 存储


async def day_loop(begin_dt):
    # 关注标的
    focus_symbols = Symbol.FOCUS_SYMBOLS
    # 交易所
    exchange = Exchange()
    exchange_cursor = exchange.collection.find()
    for e_document in await exchange_cursor.to_list(length=100):
        exchange_name = e_document["name"]

        for focus_symbol in focus_symbols:
            # 查询trade数据
            trade = Trade(exchange_name, focus_symbol)
            kline = Kline(exchange_name, focus_symbol)
            await insert(trade, kline, begin_dt)
            break


async def insert(trade, kline, begin_timestamp):
    # 查询上一天最后一笔trade数据的trade price
    prev_close_price = await query_prev_close_price(begin_timestamp, trade)
    prev_kline = await query_prev_kline(kline, begin_timestamp)
    print(prev_kline, "prev_kline")

    klines = []
    kline_document = {}
    update_flag = True  # 是否使用update_one

    # 按照 kline 时间段划分
    # for begin_dt in range(begin_timestamp, begin_timestamp + kline.interval * 5, kline.interval):
    for begin_dt in range(begin_timestamp, begin_timestamp + one_day, kline.interval):
        end_dt = begin_dt + kline.interval
        kline_document = {
            "begin_dt": begin_dt,
            "end_dt": end_dt,
            "open": 0.0,
            "high": 0.0,
            "low": 0.0,
            "close": 0.0,
            "avg_price": 0.0,
            "buy_avg_price": 0.0,
            "sell_avg_price": 0.0,
            "open_avg": 0.0,
            "close_avg": 0.0,
            "volume": 0.0,
            "amount": 0.0,
            "buy_volume": 0.0,
            "buy_amount": 0.0,
            "sell_volume": 0.0,
            "sell_amount": 0.0,
            "sectional_high": 0.0,
            "sectional_low": 0.0,
            "sectional_volume": 0.0,
            "sectional_amount": 0.0,
            "sectional_avg_price": 0.0,
            "sectional_buy_avg_price": 0.0,
            "sectional_sell_avg_price": 0.0,
            "sectional_book_count": 0,
            "sectional_buy_book_count": 0,
            "sectional_sell_book_count": 0,
            "sectional_buy_volume": 0.0,
            "sectional_buy_amount": 0.0,
            "sectional_sell_volume": 0.0,
            "sectional_sell_amount": 0.0,
            "prev_close_price": prev_close_price,
            "next_price": 0.0,
            "prev_price": prev_kline.get("close_avg", 0.0),
            "lead_ret": None,
            "lag_ret": None,
            "usable": False
        }

        trade_cursor = trade.collection.find(
            {"tradedt": {"$gte": begin_dt, "$lt": end_dt}}).sort("tradedt")

        trades = [t_document for t_document in await trade_cursor.to_list(length=kline.interval)]
        if trades:
            kline_document["open"] = trades[0]["tradeprice"]
            kline_document["close"] = trades[-1]["tradeprice"]
            results = handle_documents(trades)

            kline_document["avg_price"] = results["avg_price"]
            kline_document["volume"] = results["sum_volume"]

            kline_document["amount"] = results["sum_amount"]
            kline_document["usable"] = True if results["sum_volume"] > 0 else False

        sell_trades = []
        buy_trades = []
        open_trades = []
        close_trades = []
        tradeprices = []
        sum_amount_check = 0  # TODO: 之后删除

        duration = kline.interval * 0.2

        for t_document in trades:
            tradeprices.append(t_document["tradeprice"])
            # TODO: amount_check = sum(trade price * volume)
            sum_amount_check += t_document["tradeprice"] * t_document["volume"]

            if t_document["direction"] == "buy":
                buy_trades.append(t_document)
            else:
                sell_trades.append(t_document)

            if t_document["tradedt"] - begin_dt < duration:
                open_trades.append(t_document)
            elif (begin_dt + kline.interval) - t_document["tradedt"] <= duration:
                close_trades.append(t_document)

        high = max(tradeprices) if tradeprices else 0.0
        low = min(tradeprices) if tradeprices else 0.0
        kline_document["high"] = high
        kline_document["low"] = low
        kline_document["amount_check"] = sum_amount_check

        kline_document["book_count"] = len(trades)
        kline_document["buy_book_count"] = len(buy_trades)
        kline_document["sell_book_count"] = len(sell_trades)

        # 主买
        if buy_trades:
            results = handle_documents(buy_trades)
            kline_document["buy_avg_price"] = results["avg_price"]
            kline_document["buy_volume"] = results["sum_volume"]
            kline_document["buy_amount"] = results["sum_amount"]

        # 主卖
        if sell_trades:
            results = handle_documents(sell_trades)
            kline_document["sell_avg_price"] = results["avg_price"]
            kline_document["sell_volume"] = results["sum_volume"]
            kline_document["sell_amount"] = results["sum_amount"]

        prev_kline_sectional_low = prev_kline.get("sectional_low", 0.0)
        kline_document["sectional_high"] = max([prev_kline.get("sectional_high", 0.0), high])
        kline_document["sectional_low"] = min([low, prev_kline_sectional_low]) if prev_kline_sectional_low else low
        sectional_volume = prev_kline.get("sectional_volume", 0.0) + kline_document["volume"]
        sectional_amount = prev_kline.get("sectional_amount", 0.0) + kline_document["amount"]
        kline_document["sectional_volume"] = sectional_volume
        kline_document["sectional_amount"] = sectional_amount
        kline_document["sectional_avg_price"] = sectional_amount / sectional_volume if sectional_amount else 0.0
        kline_document["sectional_book_count"] = prev_kline.get("sectional_book_count", 0.0) + \
            kline_document["book_count"]

        sectional_buy_volume = prev_kline.get("sectional_buy_volume", 0.0) + kline_document["buy_volume"]
        sectional_buy_amount = prev_kline.get("sectional_buy_amount", 0.0) + kline_document["buy_amount"]
        kline_document["sectional_buy_volume"] = sectional_buy_volume
        kline_document["sectional_buy_amount"] = sectional_buy_amount
        kline_document["sectional_buy_avg_price"] = sectional_buy_amount / sectional_buy_volume \
            if sectional_buy_amount else 0.0
        kline_document["sectional_buy_book_count"] = prev_kline.get("sectional_buy_book_count", 0.0) + \
            kline_document["buy_book_count"]

        sectional_sell_volume = prev_kline.get("sectional_sell_volume", 0.0) + kline_document["sell_volume"]
        sectional_sell_amount = prev_kline.get("sectional_sell_amount", 0.0) + kline_document["sell_amount"]
        kline_document["sectional_sell_volume"] = sectional_sell_volume
        kline_document["sectional_sell_amount"] = sectional_sell_amount
        kline_document["sectional_sell_avg_price"] = \
            sectional_sell_amount / sectional_sell_volume if sectional_sell_amount else 0.0
        kline_document["sectional_sell_book_count"] = prev_kline.get("sectional_sell_book_count", 0.0) + \
            kline_document["sell_book_count"]

        # TODO: check open_avg_check = sum(trade price * volume) / sum(volume)
        if open_trades:
            results = handle_documents(open_trades)
            kline_document["open_avg"] = results["avg_price"]
            # TODO: 删除check
            kline_document["open_avg_check"] = get_avg_check(open_trades)

        if close_trades:
            results = handle_documents(close_trades)
            kline_document["close_avg"] = results["avg_price"]
            # TODO: 删除check
            kline_document["close_avg_check"] = get_avg_check(close_trades)

        kline_document["lag_ret"] = math.log(kline_document["close_avg"] / prev_kline["close_avg"]) \
            if prev_kline["close_avg"] and kline_document["close_avg"] else None

        # "lead_ret": 0.0  # math.log(next_price / open_avg),
        open_avg = kline_document["open_avg"]
        lead_ret = math.log(open_avg / prev_kline["open_avg"]) if prev_kline.get("open_avg", 0.0) and open_avg else None
        prev_kline.update({
            "next_price": open_avg,
            "lead_ret": lead_ret,
        })

        # 避免插入两天数据， 所以第一个采用update_one
        if update_flag:
            klines.append(UpdateOne(
                {
                    "begin_dt": begin_dt - kline.interval,
                    "end_dt": end_dt - kline.interval,
                },
                {"$set": prev_kline}
            ))
            update_flag = False
        else:
            klines.append(InsertOne(prev_kline))

        # 替换 prev_kline
        prev_kline = kline_document

    # 加上最后一个没有prev_price 的kline
    klines.append(InsertOne(kline_document))
    for offset in range(0, len(klines), LIMIT):
        result = await kline.insert_many(klines[offset: offset + LIMIT])
        print(result.bulk_api_result, begin_timestamp, kline.collection_name)


async def query_prev_close_price(begin_timestamp, trade):
    prev_trade_cursor = trade.collection.find(
        {"tradedt": {"$gte": begin_timestamp - one_day, "$lt": begin_timestamp}}).sort("tradedt", -1)
    prev_trades = [t_document for t_document in await prev_trade_cursor.to_list(length=1)]
    prev_close_price = prev_trades[0].get("tradeprice", 0.0) if prev_trades else 0.0

    return prev_close_price


async def query_prev_kline(kline, begin_timestamp):
    prev_kline = await kline.collection.find_one({
        "begin_dt": begin_timestamp - kline.interval,
    }) or {}
    return {
        "open_avg": prev_kline.get("open_avg", 0.0),
        "close_avg": prev_kline.get("close_avg", 0.0)
    }


async def calculate():
    pass


def get_avg_check(documents):
    divisor = 0
    denominator = 0
    for document in documents:
        divisor += document["tradeprice"] * document["volume"]
        denominator += document["volume"]
    return divisor / denominator


def handle_documents(documents):
    sum_amount = 0
    sum_volume = 0

    for document in documents:
        sum_amount += document["amount"]
        sum_volume += document["volume"]
    return {
        "avg_price": sum_amount / sum_volume,
        "sum_volume": sum_volume,
        "sum_amount": sum_amount,
    }


async def get_df():
    kline = Kline(exchange_name="binance", symbol_name="btcusdt")
    begin = 1575129600000 + 60 * 60 * 8 * 1000
    end = 1575129600000 + 60 * 60 * 10 * 1000
    df = await kline.get_df_from_table({"begin_dt": {"$gte": begin, "$lt": end}})
    print(df)


if __name__ == '__main__':
    # TODO： 根据传入参数决定生成的kline种类
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
