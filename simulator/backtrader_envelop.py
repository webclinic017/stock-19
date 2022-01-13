import datetime
import backtrader as bt
import locale

from backtrader.indicators import crossover

locale.setlocale(locale.LC_ALL, 'ko_KR')

class EnvelopeCross(bt.Strategy):

    def __init__(self):
        MASE = bt.ind.MovingAverageSimpleEnvelope(perc=2,period=5)  # slow moving average
        self.topCrossover = bt.ind.CrossOver(self.data,MASE.top)
        self.botCrossover = bt.ind.CrossOver(self.data,MASE.bot)
        self.holding = 0
        self.started = 0
        self.target = 0.4
        self.order_target_percent(target = self.target)

    def next(self):
        if self.botCrossover > 0 and self.target <= 0.8:
            self.target = self.target + 0.2
            print("buy  :   " + str(self.target))
            self.order_target_percent(target = self.target)
        elif self.topCrossover < 0 and self.target >= 0:  # in the market & cross to the downside
            self.target = self.target - 0.2
            print("sell :   " + str(self.target))
            self.order_target_percent(target = self.target)

    def notify_order(self, order):
        if order.status not in [order.Completed]:
            return

        if order.isbuy():
            action = 'Buy'
        elif order.issell():
            action = 'Sell'

        date = self.data.datetime[0]
        stock_price = self.data.close[0]
        cash = self.broker.getcash()
        value = self.broker.getvalue()
        self.holding += order.size
        
        print('%d : %s[%d] holding[%d] price[%d] cash[%.2f] value[%.2f]'
              % (date, action, abs(order.size), self.holding, stock_price, cash, value))

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
    data = bt.feeds.GenericCSVData(
        dataname='./backtrader/stock_price20211226_005930.csv',

        compression=100,
        sessionend=datetime.datetime(2021, 12, 23, 9, 00, 0),
        sessionstart=datetime.datetime(2021, 11, 4, 15, 30, 0),
        timeframe=bt.TimeFrame.Minutes,

        dtformat=('%Y%m%d'),
        tmformat=('%H%M%S'),

        datetime=0,
        time=1,
        open=2,
        high=3,
        low=4,
        close=5,
        volume=6,
        # openinterest=-1
    )
    cerebro.adddata(data)  # Add the data feed

    cerebro.addstrategy(EnvelopeCross)  # Add the trading strategy

    start_value = cerebro.broker.getvalue()
    cerebro.run()  # run it all
    final_value = cerebro.broker.getvalue()

    print('* start value : %s won' % locale.format_string('%d', start_value, grouping=True))
    print('* final value : %s won' % locale.format_string('%d', final_value, grouping=True))
    print('* earning rate : %.2f %%' % ((final_value - start_value) / start_value * 100.0))

    cerebro.plot()  # and plot it with a single command
