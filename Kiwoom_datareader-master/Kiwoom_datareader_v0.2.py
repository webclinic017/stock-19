# coding=utf-8
import time
import sys
import datetime
import pandas as pd
import threading
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import QtGui
from PyQt5 import uic

from kiwoomAPI import KiwoomAPI
import decorators

form_class = uic.loadUiType("Kiwoom_datareader-master/Kiwoom_datareader_v0.2.ui")[0]

class MainWindow(QMainWindow, form_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.kw = KiwoomAPI()

        # login
        self.kw.comm_connect()

        # status bar 에 출력할 메세지를 저장하는 변수
        # 어떤 모듈의 실행 완료를 나타낼 때 쓰인다.
        self.return_status_msg = ''

        # timer 등록. tick per 1s
        self.timer_1s = QTimer(self)
        self.timer_1s.start(1000)
        self.timer_1s.timeout.connect(self.timeout_1s)

        KiwoomAPI.TR_REQ_TIME_INTERVAL = 2

        # pushButton '실행'이 클릭될 시 실행될 함수 연결
        self.pushButton.clicked.connect(self.start_button)
        
        # list = self.kw.dynamicCall("GetCodeListByMarket(QString)",0)
        # kospi = list.split(';')
        # for code in kospi:
        #     # name = self.kw.get_master_code_name(code)
        #     # self.addItemText = code
        #     # print(self.addItemText)    
        #     self.listWidget_Test1.addItem(code)

        list = self.kw.dynamicCall("GetCodeListByMarket(QString)",10)
        kosdoq = list.split(';')
        for code in kosdoq:
            self.listWidget_Test1.addItem(code)

    def timeout_1s(self):
        current_time = QTime.currentTime()

        text_time = current_time.toString("hh:mm:ss")
        time_msg = "현재시간: " + text_time

        state = self.kw.get_connect_state()
        if state == 1:
            state_msg = "서버 연결 중"
        else:
            state_msg = "서버 미 연결 중"

        if self.return_status_msg == '':
            statusbar_msg = state_msg + " | " + time_msg
        else:
            statusbar_msg = state_msg + " | " + time_msg + " | " + self.return_status_msg

        self.statusbar.showMessage(statusbar_msg)

    def start_button(self):
        self.start_button_each()
        # t = threading.Thread(target=self.start_button_each,args=())
        # t.start()

    def fetch_minuate_data(self,code):
        name = self.kw.get_master_code_name(code)
        
        tick_range = 1
        input_dict = {}
        ohlcv = None

        # 일봉 조회의 경우 현재 날짜부터 과거의 데이터를 조회함
        # 현 시점부터 과거로 약 160일(약 60000개)의 데이터까지만 제공된다. (2018-02-20)
        input_dict['종목코드'] = code
        input_dict['틱범위'] = tick_range
        input_dict['수정주가구분'] = 1

        self.kw.set_input_value(input_dict)
        self.kw.comm_rq_data("opt10080_req", "opt10080", 0, "0101")
        ohlcv = self.kw.latest_tr_data

        while self.kw.is_tr_data_remained == True:
            self.kw.set_input_value(input_dict)
            self.kw.comm_rq_data("opt10080_req", "opt10080", 2, "0101")
            for key, val in self.kw.latest_tr_data.items():
                ohlcv[key][-1:] = val

        df = pd.DataFrame(ohlcv, columns=['date','open', 'high', 'low', 'close', 'volume'])

        df.insert(2,'time', df['date'].astype('int64')%1000000)
        df['date'] = df['date'].astype('int64')/1000000

        firstdate = str(df.min()['date'].astype('int64'))
        lastdate = str(df.max()['date'].astype('int64'))
        
        # df.rename(index={'date': 'Date'}, columns={'open':'Open','high':'High','low':'Low','close':'Close','volume':'Volume','high':'High'})

        # con = sqlite3.connect("./stock_price_"+base_date+"_"+code +".db")
        # df.to_sql(code, con, if_exists='replace')
        # df.to_csv("stock_price_"+ code +".csv")
        print(firstdate)
        print(lastdate)

        df.to_csv("./data/분봉_"+name+"_"+code+"_"+firstdate+"_"+lastdate+".csv")

    def start_button_each(self):
        print(str(self.listWidget_Test1.count()))
        for i in range(self.listWidget_Test1.count()) :
            print(i)
            item = self.listWidget_Test1.takeItem(i)
            code = item.text()
            name = self.kw.get_master_code_name(code)
            fullname = name + "("+code+")"
            print("Start  " + fullname)
            self.listWidget_Test2.addItem(name + "("+code+")")
            self.fetch_minuate_data(code)
            print("Done  " + fullname)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    app.exec_()
