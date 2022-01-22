# coding=utf-8
import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import QtGui
from PyQt5 import uic
import my_data_reader
import backtrader as bt
import yfinance as yf
import tqdm as tqdm
import numpy as np
import pandas as pd

import multiprocessing as mp
from pandas_to_pyqt_table import PandasModel
from simulator_core import Simulator
import math
import time
from multiprocessing.dummy import Pool as ThreadPool
import sys

# .ui 파일에서 직접 클래스 생성하는 경우 주석 해제
Ui_MainWindow = uic.loadUiType("justin_simulator.ui")[0]


class Worker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, codes_dataframe, cash, commission, start_date, last_date, plot, index_data, core_num=1, update_status_msg=""):
        super().__init__()
        self.update_status_msg = update_status_msg
        self.pool = ThreadPool(core_num)
        self.filter_list = codes_dataframe
        self.index_data = index_data
        self.plot = plot
        self.cash = cash
        self.commission = commission
        self.start_date = start_date
        self.last_date = last_date
        self.myDataReader= my_data_reader.MyDataReader()

    def run(self):
        
        start = time.time()

        # results = self.pool.map(self.calculate_yield, self.filter_list['종목코드'])
        total = self.filter_list.shape[0]
        for index, row in tqdm.tqdm(self.filter_list.iterrows(), total=total): 
            code = row['종목코드']
            result = self.calculate_yield(code)
            self.update_status_msg = str(index) + " / " + str(total)
            row['수익율'] = result
        print(self.filter_list)

        end = time.time() 
        print("Total Simulation time : {end - start:.2f} sec", end - start)


    def calculate_yield(self, code):
        _yield = Simulator(cash=self.cash, commission=self.commission, dataReader = self.myDataReader).simulate_each(code=code,
                                                                                     index_data=self.index_data, start_date=self.start_date, last_date=self.last_date, plot=self.plot, db="MyDataReader")
        return _yield


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # timer 등록. tick per 1s
        self.timer_1s = QTimer(self)
        self.timer_1s.start(1000)
        self.timer_1s.timeout.connect(self.timeout_1s)
        self.update_status_msg = ""
        self.index = '^KS11'  # 코스피
        self.radioButton_kosdaq.clicked.connect(
            self.chage_filter_market_status) 
        self.radioButton_kospi.clicked.connect(self.chage_filter_market_status)
        self.pushButton_filter.clicked.connect(self.filter_start)
        self.pushButton_start_simulation.clicked.connect(self.simulation_start)
        self.disable_all_children(self.groupBox_buy_condition)
        self.disable_all_children(self.groupBox_sell_condition)
        self.disable_all_children(self.groupBox_simulation)
        self.myDataReader= my_data_reader.MyDataReader()
        self.center()

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def chage_filter_market_status(self, state):
        if self.radioButton_kosdaq.isChecked():
            print("radioButton_kosdaq checked!")
        elif self.radioButton_kospi.isChecked():
            print("radioButton_kospi checked!")

    def travel_all_children(self, groupbox, bool):
        for child in groupbox.findChildren(QLineEdit):
            child.setEnabled(bool)
        for child in groupbox.findChildren(QComboBox):
            child.setEnabled(bool)
        for child in groupbox.findChildren(QRadioButton):
            child.setEnabled(bool)
        for child in groupbox.findChildren(QPushButton):
            child.setEnabled(bool)

    def disable_all_children(self, groupbox):
        self.travel_all_children(groupbox, False)

    def enable_all_children(self, groupbox):
        self.travel_all_children(groupbox, True)

    def simulation_start(self):
        self.disable_all_children(self.groupBox_buy_condition)
        self.disable_all_children(self.groupBox_sell_condition)
        self.disable_all_children(self.groupBox_simulation)
        self.disable_all_children(self.groupBox_filter)
        self.update_status_msg = "시뮬레이션 시작"

        if self.radioButton_kosdaq.isChecked():
            self.index = '^KQ11'  # 코스닥
        elif self.radioButton_kospi.isChecked():
            self.index = '^KS11'  # 코스피
        self.cash = int(self.lineEdit_start_cash.text())
        self.commission = float(self.lineEdit_commission.text())

        params = dict(
        # rsi 셋팅
        rsi_period=self.lineEdit_rsi_period.text(),
        upperband=self.lineEdit_rsi_upper.text(),
        lowerband=self.lineEdit_rsi_lower.text(),
        # envelope 셋팅
        envelope_period=self.lineEdit_envel_period.text(),
        perc=self.lineEdit_envel_perc.text(),
        # 최대 보유 시간
        target_day=self.lineEdit_target_day.text(),
        target_due_date=self.checkBox_target_due_date.isChecked(),
        # 익절 조건
        target_rsi=self.lineEdit_target_rsi.text(),
        # 3단 비중 조절
        rsi_first_band=self.lineEdit_rsi_first_band.text(),
        rsi_second_band=self.lineEdit_rsi_second_band.text(),
        rsi_third_band=self.lineEdit_rsi_third_band.text(),
        first_buy=float(self.lineEdit_rsi_first_buy.text())/100,
        second_buy=float(self.lineEdit_rsi_second_buy.text())/100,
        third_buy=(float(self.lineEdit_rsi_third_buy.text())-1)/100,
        )
        print(params)
        # simulate_each(self, code="000660.KS", index='^KQ11', start_date='2018-01-01', last_date='2018-12-31', plot=True):
        self.start_date = self.comboBox_start_year.currentText(
        ) + "-" + self.comboBox_start_month.currentText() + "-01"
        self.last_date = self.comboBox_last_year.currentText(
        ) + "-" + self.comboBox_last_month.currentText() + "-31"

        self.index_data = bt.feeds.PandasData(dataname=yf.download(
            tickers=self.index, start=self.start_date, end=self.last_date, auto_adjust=True, progress=True))

        # self.tableWidget.setRowCount(len(self.filter_list))

        # self.worker = Worker(codes_dataframe=self.filter_list, commission=self.commission, cash=self.cash,
        #                      index_data=self.index_data, start_date=self.start_date, last_date=self.last_date, plot=False, update_status_msg = self.update_status_msg)
        # self.worker.start()
        
        # results = self.pool.map(self.calculate_yield, self.filter_list['종목코드'])

        start = time.time()
        total = self.filter_list.shape[0]
        i = 0
        for index, row in self.filter_list.iterrows() : 
            code = row['종목코드']
            result,filename = self.calculate_yield(code)
            self.update_status_msg = str(index) + " / " + str(total)
            row['수익율'] = result
            row['파일명'] = filename
            i = i+1;
            if i == 10 : break
            
        print(self.filter_list)

        end = time.time() 
        print("Total Simulation time : {end - start:.2f} sec", end - start)

    def calculate_yield(self, code):
        _yield = Simulator(cash=self.cash, commission=self.commission, dataReader = self.myDataReader).simulate_each(code=code,
                                                                                     index_data=self.index_data, start_date=self.start_date, last_date=self.last_date, plot=True, db="MyDataReader")
        return _yield

    def filter_start(self):
        self.enable_all_children(self.groupBox_buy_condition)
        self.enable_all_children(self.groupBox_sell_condition)
        self.enable_all_children(self.groupBox_simulation)
        self.disable_all_children(self.groupBox_filter)
        self.update_status_msg = "필터 시작"
        if self.radioButton_kosdaq.isChecked() is True:
            file_name = 'kosdaq150.csv'
        elif self.radioButton_kospi.isChecked() is True:
            file_name = 'kospi200.csv'

        self.filter_list = pd.read_csv(file_name)

        self.db_view_model = PandasModel(self.filter_list)
        self.tableView.setModel(self.db_view_model)
        self.tableView.resizeColumnToContents(0)


    def timeout_1s(self):
        statusbar_msg = self.update_status_msg 
        self.statusbar.showMessage(statusbar_msg)

app = QApplication


def main_gui():
    global app
    app = QApplication(sys.argv)
    mainWindow = MainWindow()

    mainWindow.show()
    app.exec_()


if __name__ == "__main__":
    main_gui()
