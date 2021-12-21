from datetime import datetime
import backtrader as bt
import locale

from backtrader.indicators import crossover

locale.setlocale(locale.LC_ALL, 'ko_KR')
 
class BollingerStrategy(bt.Strategy):

    params = (
        ("period", 20),
        ("devfactor", 2),
        ("size", 20),
        ("debug", False)
        )
 
    def __init__(self):
        self.boll = bt.indicators.BollingerBands(period=self.p.period, devfactor=self.p.devfactor)

    def next(self):
        orders = self.broker.get_orders_open()
        # Cancel open orders so we can track the median line
        if orders:
            for order in orders:
                self.broker.cancel(order)
        if not self.position:
            if self.data.close > self.boll.lines.top:
                self.sell(exectype=bt.Order.Stop, price=self.boll.lines.top[0], size=self.p.size)
            if self.data.close < self.boll.lines.bot:
                self.buy(exectype=bt.Order.Stop, price=self.boll.lines.bot[0], size=self.p.size)
        else:
            if self.position.size > 0:
                self.sell(exectype=bt.Order.Limit, price=self.boll.lines.mid[0], size=self.p.size)
            else:
                self.buy(exectype=bt.Order.Limit, price=self.boll.lines.mid[0], size=self.p.size)
 
    def notify_order(self, order):
        if order.status not in [order.Completed]:
            return

        if order.isbuy():
            action = 'Buy'
        elif order.issell():
            action = 'Sell'

        stock_price = self.data.close[0]
        cash = self.broker.getcash()
        value = self.broker.getvalue()
        # self.holding += order.size
        
        # print('%s[%d] holding[%d] price[%d] cash[%.2f] value[%.2f]'
        #       % (action, abs(order.size), self.holding, stock_price, cash, value))

if __name__ == '__main__':

    cerebro = bt.Cerebro()  # create a "Cerebro" engine instance
    cerebro.broker.setcash(10000000)
    cerebro.broker.setcommission(0.002)

    #   KODEX 미국달러선물 : 261240
    #   KODEX 200 : 069500
    #   삼성전자 : 005930
    #   코나아이 : 052400
    #   이마트 : 139480
    #   Create a data feed
    data = bt.feeds.YahooFinanceData(dataname='139480.KS',
                                    fromdate=datetime(2021, 1, 1),
                                    todate=datetime.now())

    cerebro.addsizer(bt.sizers.FixedReverser, stake=10)

    cerebro.adddata(data)  # Add the data feed

    cerebro.addstrategy(BollingerStrategy)  # Add the trading strategy

    start_value = cerebro.broker.getvalue()
    cerebro.run()  # run it all
    final_value = cerebro.broker.getvalue()

    print('* start value : %s won' % locale.format_string('%d', start_value, grouping=True))
    print('* final value : %s won' % locale.format_string('%d', final_value, grouping=True))
    print('* earning rate : %.2f %%' % ((final_value - start_value) / start_value * 100.0))

    cerebro.plot()  # and plot it with a single command
