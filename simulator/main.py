import datetime
import backtrader as bt
import locale
import sqlite3
import pandas as pd
import os
import yfinance as yf
import my_data_reader

locale.setlocale(locale.LC_ALL, 'ko_KR')

# Create a subclass of Strategy to define the indicators and logic


class CustomStrategy(bt.Strategy):
    # list of parameters which are configurable for the strategy

    params = dict(
        # rsi 셋팅
        rsi_period=10,
        upperband=70,
        lowerband=30,
        # envelope 셋팅
        envelope_period=30,
        perc=2.5,
        # 최대 보유 시간 
        target_day=5,
        extend_due_date=True,
        # 3단 비중 조절
        rsi_first_band=30,
        rsi_second_band=20,
        rsi_third_band=10,
        first_buy=0.3,
        second_buy=0.6,
        third_buy=0.95,
    )

    def __init__(self):
        self.holding = 0
        self.sum_price=0
        print(self.params.upperband)
        ## RSI_SMA 와 RSI_EMA 차이?
        self.rsi_sma = bt.ind.RSI_EMA(self.data.close, period=self.params.rsi_period,
                                      upperband=self.params.upperband, lowerband=self.params.lowerband, safediv=True)
        self.envelope = bt.ind.MovingAverageSimpleEnvelope(
            self.data.close, perc=self.params.perc, period=self.params.envelope_period)
            
        self.first_signal = False
        self.second_signal = False
        self.third_signal = False

        self.signal_due_date = self.min_date()

    def min_date(self) :
        return datetime.date(1, 1, 1)
        
    def no_signal_started(self) :
        signal_started = self.first_signal and self.second_signal and self.third_signal
        return signal_started

    def next(self):
        # position 이 없을때
        if self.signal_due_date < self.data.datetime.date() and self.rsi_sma < self.params.lowerband and self.envelope.bot > self.data.close :
            # 10일 카운트 시작
            if self.signal_due_date == self.min_date() :
                self.signal_due_date = self.data.datetime.date() + datetime.timedelta(days=self.params.target_day)
            if self.rsi_sma < self.params.rsi_first_band  and self.first_signal == False:
                self.order_target_percent(target=self.params.first_buy)
                self.first_signal = True
            elif self.rsi_sma < self.params.rsi_second_band  and self.second_signal == False:
                self.order_target_percent(target=self.params.second_buy)
                if self.params.extend_due_date : self.signal_due_date = self.data.datetime.date() + datetime.timedelta(days=self.params.target_day)
                self.second_signal = True
            elif self.rsi_sma < self.params.rsi_third_band  and self.third_signal == False:
                self.order_target_percent(target=self.params.third_buy)
                if self.params.extend_due_date : self.signal_due_date = self.data.datetime.date() + datetime.timedelta(days=self.params.target_day)
                self.third_signal = True

        # 이미 position 이 있을때
        elif self.position :
            if self.signal_due_date == self.min_date() :
                self.signal_due_date = datetime.min_date()
                self.third_signal = False
                self.second_signal = False
                self.first_signal = False
                self.order_target_percent(target=0.0)
            elif self.rsi_sma > 50 : 
                self.signal_due_date = self.min_date()
                self.third_signal = False
                self.second_signal = False
                self.first_signal = False
                self.order_target_percent(target=0.0)

    def isRedCandle(self):
        if self.data.close[0] > self.data.open[0]:
            return True
        else:
            return False

    def notify_order(self, order):
        if order.status not in [order.Completed]:
            return

        if order.isbuy():
            action = 'Buy :'
            sum_factor = 1
        elif order.issell():
            action = 'Sell:'
            sum_factor = -1

        date = self.data.datetime.date()
        stock_price = self.data.close[0]
        cash = self.broker.getcash()
        value = self.broker.getvalue()
        self.holding += order.size
        self.sum_price += order.size * stock_price * sum_factor
        avg_price = 0
        if self.holding != 0 : 
            avg_price = self.sum_price / self.holding
        else : 
            self.sum_price = 0
            
        print('%s : %s  가격[%d]    주문수량[%d]  평단가[%d]  보유주식[%d]  현금보유[%.0f]  평가잔액[%.0f]'
              % (date, action, stock_price, abs(order.size), avg_price, self.holding, cash, value))

if __name__ == "__main__":
    cerebro = bt.Cerebro()  # create a "Cerebro" engine instance
    cerebro.broker.setcash(100000000)
    cerebro.broker.setcommission(0.003)

    # data = bt.feeds.PandasData(dataname=my_data_reader.MyDataReader().get_data_with_time("A052400",20210101,20220101))
    # 000660.KS 하이닉스 
    # ^KS11 코스피
    kospi = bt.feeds.PandasData(dataname=yf.download('^KS11', '2021-01-01', '2022-12-31', auto_adjust=True))
    data = bt.feeds.PandasData(dataname=yf.download('000660.KS', '2021-01-01', '2022-12-31', auto_adjust=True))

    cerebro.adddata(kospi)  # Add the data feed
    cerebro.adddata(data)

    cerebro.addstrategy(CustomStrategy)  # Add the trading strategy

    start_value = cerebro.broker.getvalue()
    cerebro.run()  # run it all
    final_value = cerebro.broker.getvalue()

    print('* 시작 평가잔액 : %s won' %
          locale.format_string('%d', start_value, grouping=True))
    print('* 종료 평가잔액 : %s won' %
          locale.format_string('%d', final_value, grouping=True))
    print('*    수익율     : %.2f %%' %
          ((final_value - start_value) / start_value * 100.0))

    # and plot it with a single command
    cerebro.plot(style='candle', barup='red', bardown='blue')
