import datetime
import backtrader as bt
import locale
import sqlite3
import pandas as pd
import os

locale.setlocale(locale.LC_ALL, 'ko_KR')

# Create a subclass of Strategy to define the indicators and logic
class CustomStrategy(bt.Strategy):
    # list of parameters which are configurable for the strategy
    

    params = dict(
        period=15,
        upperband=70,
        lowerband=30,
        expected_yield = 0.3,
        margin = 0.3
    )

    def __init__(self):
        self.holding = 0
        self.rsi_sma = bt.ind.RSI_SMA(self.data.close ,period=self.params.period, upperband=self.params.upperband, lowerband=self.params.lowerband, safediv=True)
        
    def next(self):
        # position 이 없을때
        if not self.position:
            if self.rsi_sma < self.params.lowerband :
                if self.isRedCandle() :
                    close = self.data.close[0] # 종가 값
                    size = int(self.broker.getcash() / close) # 최대 구매 가능 개수
                    self.buy(size=size-10, price=self.data.open) # 매수 size = 구매 개수 설정
                    self.buy_price = self.data.close
                    self.from_buy_day = 3

        # 이미 position 이 있을때
        else : 
            if self.from_buy_day == 0 :
                self.close()
                self.from_buy_day = 0
            else : 
                self.from_buy_day = self.from_buy_day -1
                if self.data.close < self.buy_price * 0.97 :
                    self.close()
                    self.from_buy_day = 0
                 
    def isRedCandle(self):
        if self.data.close[0] > self.data.open[0] : 
            return True
        else :
            return False

    def notify_order(self, order):
        if order.status not in [order.Completed]:
            return

        if order.isbuy():
            action = 'Buy'
        elif order.issell():
            action = 'Sell' 

        date = self.data.datetime.date()
        stock_price = self.data.close[0]
        cash = self.broker.getcash()
        value = self.broker.getvalue()
        self.holding += order.size
        
        print('%s : %s[%d]  holding[%d] price[%d]   cash[%.2f]  value[%.2f]'
              % (date, action, abs(order.size), self.holding, stock_price, cash, value))


if __name__ == "__main__":
    cerebro = bt.Cerebro()  # create a "Cerebro" engine instance
    cerebro.broker.setcash(100000000)
    cerebro.broker.setcommission(0.003)

    # Create a data feed
    # data = bt.feeds.YahooFinanceData(dataname='005930.KS',
    #                                  fromdate=datetime(2019, 1, 1),
    #                                  todate=datetime.now())
    # data = bt.feeds.PandasData(dataname=yf.download('TSLA', '2018-01-01', '2019-01-01'))

    print(os.getcwd())

    datapath = ('../Creon-Datareader-master/db/일봉/일봉_전종목.db')
    if os.path.exists(datapath) : 
        print("DB file is OK! ("+datapath+")")
    else : 
        print(datapath + " in not exist!")

    con = sqlite3.connect(datapath)
    # code = "D0011025" # 코나아이
    code = "A052400" # 코나아이
    # code = "A005930" # 삼성전자
    # code = "A306200" # 세아제강
    start_date = 0
    # last_date = 20021010
    last_date = 20300101
    dataframe = pd.read_sql('SELECT * FROM ' + code + ' WHERE date BETWEEN '+ str(start_date) +' AND ' + str(last_date), con)
    dataframe['date'] = pd.to_datetime(dataframe['date'], format='%Y%m%d', errors='raise')
    dataframe.rename(columns={'date': 'datetime'}, inplace =True)
    # dataframe.columns.values[0] = 'datetime'

    dataframe.set_index('datetime', inplace=True)
    data = bt.feeds.PandasData(dataname=dataframe)

    cerebro.adddata(data)  # Add the data feed

    cerebro.addstrategy(CustomStrategy)  # Add the trading strategy

    start_value = cerebro.broker.getvalue()
    cerebro.run()  # run it all
    final_value = cerebro.broker.getvalue()

    print('* 시작 평가잔액 : %s won' % locale.format_string('%d', start_value, grouping=True))
    print('* 종가 평가잔액 : %s won' % locale.format_string('%d', final_value, grouping=True))
    print('*    수익율     : %.2f %%' % ((final_value - start_value) / start_value * 100.0))

    cerebro.plot(style = 'candle', barup = 'red', bardown = 'blue')  # and plot it with a single command