# coding=utf-8
import backtrader as bt
from backtrader import plot
import locale
import pandas as pd
from pymysql import NULL
import yfinance as yf
import my_data_reader
import threading
import math
# from pycrunch_trace.client.api import trace

import time

locale.setlocale(locale.LC_ALL, 'ko_KR')

DEBUG = True

class RSIStrategy(bt.Strategy):
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
        target_day=10,
        target_due_date=True,
        # 익절 조건
        target_rsi=70,
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
        self.sum_price = 0
        # print(self.params.upperband)
        ## RSI_SMA 와 RSI_EMA 차이?
        self.rsi_sma = bt.ind.RSI_EMA(self.data.close, period=self.params.rsi_period,
                                      upperband=self.params.upperband, lowerband=self.params.lowerband, safediv=True)
        self.envelope = bt.ind.MovingAverageSimpleEnvelope(
            self.data.close, perc=self.params.perc, period=self.params.envelope_period)

        self.first_signal = False
        self.second_signal = False
        self.third_signal = False

        self.signal_due_date = 0

    def signal_started(self):
        signal_started = self.first_signal or self.second_signal or self.third_signal
        return signal_started

    def next(self):
        # position 이 없을때
        if self.rsi_sma < self.params.lowerband and self.envelope.bot > self.data.close:
            # 10일 카운트 시작
            if self.signal_due_date == 0:
                self.signal_due_date = self.params.target_day
            # RSI 조건별로 주문
            if self.rsi_sma < self.params.rsi_first_band and self.first_signal == False:
                self.order_target_percent(
                    target=self.params.first_buy, data=self.datas[1])
                self.first_signal = True
            elif self.rsi_sma < self.params.rsi_second_band and self.second_signal == False:
                self.order_target_percent(
                    target=self.params.second_buy, data=self.datas[1])
                if self.params.target_due_date:
                    self.signal_due_date = self.params.target_day
                self.second_signal = True
            elif self.rsi_sma < self.params.rsi_third_band and self.third_signal == False:
                self.order_target_percent(
                    target=self.params.third_buy, data=self.datas[1])
                if self.params.target_due_date:
                    self.signal_due_date = self.params.target_day
                self.third_signal = True

        # 이미 position 이 있을때
        elif self.signal_started():
            self.signal_due_date -= 1
            if self.signal_due_date <= 0:
                self.signal_due_date = 0
                self.third_signal = False
                self.second_signal = False
                self.first_signal = False
                self.order_target_percent(target=0.0, data=self.datas[1])
            elif self.rsi_sma > self.params.target_rsi:
                self.signal_due_date = 0
                self.third_signal = False
                self.second_signal = False
                self.first_signal = False
                self.order_target_percent(target=0.0, data=self.datas[1])

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
        stock_price = self.datas[1].close[0]
        cash = self.broker.getcash()
        value = self.broker.getvalue()
        self.holding += order.size
        self.sum_price += order.size * stock_price * sum_factor
        avg_price = 0
        if self.holding != 0:
            avg_price = self.sum_price / self.holding
        else:
            self.sum_price = 0

        if DEBUG:
            print('%s : %s  가격[%d]    주문수량[%d]  평단가[%d]  보유주식[%d]  현금보유[%.0f]  평가잔액[%.0f]'
                  % (date, action, stock_price, abs(order.size), avg_price, self.holding, cash, value))


class VolumeStrategy(bt.Strategy):
    # list of parameters which are configurable for the strategy
    class VolumeInd(bt.Indicator):
        lines = ('volume_AVG',)

        # params = (('period', 10),)

        def __init__(self, period = 10):
            self.period = period

        def next(self):
            datasum = math.fsum(self.data.volume.get(size=self.period))
            self.lines.volume_AVG[0] = datasum / self.period

    params = dict(
        # rsi 셋팅
        volume_sum_day = 10,
        volume_multiple = 5,
        volume_due_day = 1
    )

    def __init__(self):
        self.holding = 0
        self.sum_price = 0
        self.started_date = 0
        self.signal_due_date = 0
        self.volume_due_day = self.params.volume_due_day
        bt.ind = self.VolumeInd(period = self.params.volume_sum_day)

    def next(self):
        # avg = self.sum_volume / self.params.volume_multiple
        if bt.ind.lines.volume_AVG == 0 :
            return
        avg = bt.ind.lines.volume_AVG * self.params.volume_multiple
        if self.position.size == 0 and avg < self.data.volume[0] : 
            self.order_target_percent(target=0.9, data=self.data)
        if self.position.size > 0 :
            self.volume_due_day = self.volume_due_day -1
            if self.volume_due_day == 0 : 
                self.order_target_percent(target=0.0, data=self.data)
                self.volume_due_day = self.params.volume_due_day 
        # self.sum_volume = avg * (self.params.volume_multiple-1) / self.params.volume_multiple
        # self.sum_volume += self.data.volume[0]

    def notify_order(self, order):
        if order.status not in [order.Completed]:
            return

        if order.isbuy():
            action = 'Buy :'
            sum_factor = 1
        elif order.issell():
            action = 'Sell:'
            sum_factor = -1

        # date = self.data.datetime.date()
        # stock_price = self.datas[1].close[0]
        # cash = self.broker.getcash()
        # value = self.broker.getvalue()
        # self.holding += order.size
        # self.sum_price += order.size * stock_price * sum_factor
        # avg_price = 0
        # if self.holding != 0:
        #     avg_price = self.sum_price / self.holding
        # else:
        #     self.sum_price = 0

        # if DEBUG:
        #     print('%s : %s  가격[%d]    주문수량[%d]  평단가[%d]  보유주식[%d]  현금보유[%.0f]  평가잔액[%.0f]'
        #           % (date, action, stock_price, abs(order.size), avg_price, self.holding, cash, value))


class Simulator:
    def __init__(self, cash=100000000, commission=0.3, dataReader = NULL):
        # self.cerebro = bt.Cerebro()  # create a "Cerebro" engine instance
        self.cerebro = bt.Cerebro(maxcpus =4)  # create a "Cerebro" engine instance
        self.cerebro.broker.setcash(cash)
        self.cerebro.broker.setcommission(commission/100)
        self.MyDataReader = dataReader

    # @trace(additional_excludes=['C:\\Users\\qmxmp\\.conda\\envs\\py38_64\\lib\\site-packages'])
    def simulate_each(self, code="A011200", index_data=NULL, index='^KQ11', start_date='2020-12-01', last_date='2022-12-31', plot=True, db="MyDataReader"):
        # code = "000660.KS"  # 하이닉스
        # code = "005930.KS" # 삼성전자
        # code = "306200.KS" # 세아제강
        # code = "207940.KS" # 삼성바이오로직스
        # code = "052400.KQ" # 코나아이

        # index = '^KS11' # 코스피
        # index = '^KQ11'  # 코스닥
        # start_date = '2018-01-01'
        # last_date = '2018-12-31'

        if index_data is NULL:
            index_data = bt.feeds.PandasData(dataname=yf.download(
                index, start_date, last_date, auto_adjust=True, progress = False))

        if db in "MyDataReader" : 
            int_start_date = int(start_date.replace("-",""))
            int_last_date = int(last_date.replace("-",""))
            data = bt.feeds.PandasData(dataname=self.MyDataReader.get_data_with_time(
                code=code, start_date=int_start_date, last_date=int_last_date))
        else : 
            data = bt.feeds.PandasData(dataname=yf.download(tickers = code, start = start_date, end = last_date, auto_adjust=True,progress = False, threads=False))

        # self.cerebro.adddata(index_data)  # Add the data feed
        self.cerebro.adddata(data)
        self.cerebro.addstrategy(VolumeStrategy)  # Add the trading strategy

        start_value = self.cerebro.broker.getvalue()
        
        start = time.time()
        self.cerebro.run()  # run it all
        end = time.time() 
        print("simulate_each time : %0.2f sec"%(end - start))

        final_value = self.cerebro.broker.getvalue()
        if DEBUG:
            print(code)
            print('* 시작 평가잔액 : %s won' % locale.format_string('%d', start_value, grouping=True))
            print('* 종료 평가잔액 : %s won' % locale.format_string('%d', final_value, grouping=True))
        
        _yeild = (final_value - start_value) / start_value * 100.0
        print('*    수익율     : %.2f %%' % (_yeild))

        # and plot it with a single command
        
        if plot == True:
            # import os
            # if os.path.exists("png") is False: os.mkdir("png")
            # _yeild_str = str(round(_yeild,2)).replace(".","_")
            # # os.path.join(pathfile,"output","log.txt")
            # filename = "png/"+ code + "_(" + _yeild_str + ")_" + start_date + "~" + last_date + ".png"

            # # self.cerebro.plot(style='candle', barup='red', bardown='blue')
            # # fig.savefig(filename)
            # # print(data[datetime][-1])
            # # print(data[datetime][0])
            # self.saveplots(self.cerebro,file_path = filename, style='candle', barup='red', bardown='blue')     
            self.cerebro.plot(style='candle', barup='red', bardown='blue')
            return _yeild, "자세히 보기 "+code
        else :         
            return _yeild, "자세히 보기 "+code

    def saveplots(self, cerebro, numfigs=1, iplot=True, start=None, end=None,
                width=16, height=9, dpi=300, tight=True, use=None, file_path = '', **kwargs):

            plotter = plot.Plot(**kwargs)

            figs = []
            for stratlist in cerebro.runstrats:
                for si, strat in enumerate(stratlist):
                    rfig = plotter.plot(strat, figid=si * 100,
                                        numfigs=numfigs, iplot=iplot,
                                        start=start, end=end, use=use)
                    figs.append(rfig)

            for fig in figs:
                for f in fig:
                    f.savefig(file_path, bbox_inches='tight')
            return figs

if __name__ == "__main__":
    # datas = yf.download(tickers=self.filter_list['종목코드'], start_date=self.start_date, last_date=self.last_date, auto_adjust=True, progress=True, threads=False)
    # Simulator(dataReader = self.myDataReader).simulate_each(code=code,index_data=self.index_data, start_date=self.start_date, last_date=self.last_date, plot=False, db="MyDataReader")
    
    Simulator(dataReader = my_data_reader.MyDataReader()).simulate_each(db="MyDataReader")