import datetime
import backtrader as bt
import locale
import sqlite3
import pandas as pd
import os

locale.setlocale(locale.LC_ALL, 'ko_KR')

# Create a subclass of Strategy to define the indicators and logic
class SmaCross(bt.Strategy):
    # list of parameters which are configurable for the strategy
    params = dict(
        pfast=6,  # period for the fast moving average
        pslow=20  # period for the slow moving average
    )

    def __init__(self):
        self.holding = 0

    def next(self):
        if self.data.volume[0] > 8000 :
            self.order_target_percent(target = 0.8)
        if self.data.volume[0] < 800 :
            self.order_target_percent(target = 0.0)

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

cerebro = bt.Cerebro()  # create a "Cerebro" engine instance
cerebro.broker.setcash(100000)
cerebro.broker.setcommission(0.002)

# Create a data feed
# data = bt.feeds.YahooFinanceData(dataname='005930.KS',
#                                  fromdate=datetime(2019, 1, 1),
#                                  todate=datetime.now())
# data = bt.feeds.PandasData(dataname=yf.download('TSLA', '2018-01-01', '2019-01-01'))

print(os.getcwd())

datapath = ('../Creon-Datareader-master/db/일봉/일봉_전종목.db')
print("datapath exist = "+ str(os.path.exists(datapath)))

con = sqlite3.connect(datapath)
# cursor = con.cursor()
# for i in range(10) : 
code = "A306200"
# cmd = "SELECT date FROM {} ORDER BY date DESC LIMIT 1".format(code)
dataframe = pd.read_sql('SELECT * FROM ' + code, con)
dataframe['date'] = pd.to_datetime(dataframe['date'], format='%Y%m%d', errors='raise')
dataframe.rename(columns={'date': 'datetime'}, inplace =True)
# dataframe.columns.values[0] = 'datetime'

dataframe.set_index('datetime', inplace=True)
data = bt.feeds.PandasData(dataname=dataframe)

cerebro.adddata(data)  # Add the data feed

cerebro.addstrategy(SmaCross)  # Add the trading strategy

start_value = cerebro.broker.getvalue()
cerebro.run()  # run it all
final_value = cerebro.broker.getvalue()

print('* start value : %s won' % locale.format_string('%d', start_value, grouping=True))
print('* final value : %s won' % locale.format_string('%d', final_value, grouping=True))
print('* earning rate : %.2f %%' % ((final_value - start_value) / start_value * 100.0))

cerebro.plot()  # and plot it with a single command