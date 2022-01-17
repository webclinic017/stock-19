import datetime
import backtrader as bt
import locale
import sqlite3
import pandas as pd
import os
import yfinance as yf

locale.setlocale(locale.LC_ALL, 'ko_KR')

# Create a subclass of Strategy to define the indicators and logic


class CustomStrategy(bt.Strategy):
    # list of parameters which are configurable for the strategy

    params = dict(
        # rsi 셋팅
        rsi_period=15,
        upperband=70,
        lowerband=30,
        # envelope 셋팅
        envelope_period=30,
        fast=2,
        slow=30,
        perc=2.5
    )


    def __init__(self):
        self.holding = 0
        print(self.params.upperband)
        ## RSI_SMA 와 RSI_EMA 차이?
        self.rsi_sma = bt.ind.RSI_EMA(self.data.close, period=self.params.rsi_period,
                                      upperband=self.params.upperband, lowerband=self.params.lowerband, safediv=True)
        self.envelope = bt.ind.AdaptiveMovingAverageEnvelope(
            self.data.close, perc=self.params.perc, period=self.params.envelope_period, fast=self.params.fast, slow=self.params.slow)

    def next(self):
        # position 이 없을때
        if not self.position:
            if self.rsi_sma < self.params.lowerband:
                if self.isRedCandle():
                    close = self.data.close[0]  # 종가 값
                    size = int(self.broker.getcash() / close)  # 최대 구매 가능 개수
                    # 매수 size = 구매 개수 설정
                    self.buy(size=size-10, price=self.data.open)
                    self.buy_price = self.data.close
                    self.from_buy_day = 3

        # 이미 position 이 있을때
        else:
            if self.from_buy_day == 0:
                self.close()
                self.from_buy_day = 0
            else:
                self.from_buy_day = self.from_buy_day - 1
                if self.data.close < self.buy_price * 0.97:
                    self.close()
                    self.from_buy_day = 0

    def isRedCandle(self):
        if self.data.close[0] > self.data.open[0]:
            return True
        else:
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


class MyDataReader:
    def __init__(self):
        print(os.getcwd())
        self.datapath = ('../Creon-Datareader-master/db/일봉/일봉_전종목.db')
        if os.path.exists(self.datapath):
            print("DB file is OK! ("+self.datapath+")")
        else:
            print(self.datapath + " in not exist!")

    # code = "D0011025" # 코나아이
    # code = "A052400 # 코나아이
    # code = "A005930" # 삼성전자
    # code = "A306200" # 세아제강
    def get_data_with_time(self, code="A052400", start_date=20191201, last_date=20220101):
        con = sqlite3.connect(self.datapath)
        dataframe = pd.read_sql('SELECT * FROM ' + code + ' WHERE date BETWEEN ' +
                                str(start_date) + ' AND ' + str(last_date), con)
        dataframe['date'] = pd.to_datetime(
            dataframe['date'], format='%Y%m%d', errors='raise')
        dataframe.rename(columns={'date': 'datetime'}, inplace=True)
        # dataframe.columns.values[0] = 'datetime'
        dataframe.set_index('datetime', inplace=True)
        return dataframe


if __name__ == "__main__":
    cerebro = bt.Cerebro()  # create a "Cerebro" engine instance
    cerebro.broker.setcash(100000000)
    cerebro.broker.setcommission(0.003)

    # data = bt.feeds.PandasData(dataname=MyDataReader().get_data_with_time("A052400",20210101,20220101))

    data = bt.feeds.PandasData(dataname=yf.download(
        '^KS11', '2021-01-01', '2021-12-31', auto_adjust=True))

    cerebro.adddata(data)  # Add the data feed

    cerebro.addstrategy(CustomStrategy)  # Add the trading strategy

    start_value = cerebro.broker.getvalue()
    cerebro.run()  # run it all
    final_value = cerebro.broker.getvalue()

    print('* 시작 평가잔액 : %s won' %
          locale.format_string('%d', start_value, grouping=True))
    print('* 종가 평가잔액 : %s won' %
          locale.format_string('%d', final_value, grouping=True))
    print('*    수익율     : %.2f %%' %
          ((final_value - start_value) / start_value * 100.0))

    # and plot it with a single command
    cerebro.plot(style='candle', barup='red', bardown='blue')
