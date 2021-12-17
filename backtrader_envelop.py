from datetime import datetime
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

        stock_price = self.data.close[0]
        cash = self.broker.getcash()
        value = self.broker.getvalue()
        self.holding += order.size
        
        print('%s[%d] holding[%d] price[%d] cash[%.2f] value[%.2f]'
              % (action, abs(order.size), self.holding, stock_price, cash, value))

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
    data = bt.feeds.YahooFinanceData(dataname='069500.KS',
                                    fromdate=datetime(2021, 1, 1),
                                    todate=datetime.now())

    cerebro.adddata(data)  # Add the data feed

    cerebro.addstrategy(EnvelopeCross)  # Add the trading strategy

    start_value = cerebro.broker.getvalue()
    cerebro.run()  # run it all
    final_value = cerebro.broker.getvalue()

    print('* start value : %s won' % locale.format_string('%d', start_value, grouping=True))
    print('* final value : %s won' % locale.format_string('%d', final_value, grouping=True))
    print('* earning rate : %.2f %%' % ((final_value - start_value) / start_value * 100.0))

    cerebro.plot()  # and plot it with a single command
