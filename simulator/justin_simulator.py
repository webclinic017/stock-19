# coding=utf-8
import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import QtGui
from PyQt5 import uic

import backtrader as bt
import yfinance as yf

import numpy as np
import pandas as pd

import multiprocessing as mp
from pandas_to_pyqt_table import PandasModel
from simulator_core import Simulator

from multiprocessing.dummy import Pool as ThreadPool 
import time
import traceback
import sys

# .ui 파일에서 직접 클래스 생성하는 경우 주석 해제
Ui_MainWindow = uic.loadUiType("justin_simulator.ui")[0]


class Worker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, codes_dataframe, cash, commission, start_date, last_date, plot, index_data, core_num = 8):
        super().__init__()
        self.core_num = core_num
        self.filter_list = codes_dataframe
        self.index_data = index_data
        self.plot = plot
        self.cash = cash
        self.commission = commission
        self.start_date = start_date
        self.last_date = last_date

    def run(self):
        pool = ThreadPool(self.core_num) 
        results = pool.map(self.calculate_yield, self.filter_list['종목코드'])
        print(results)
        # self.finished.emit(data)

    def calculate_yield(self, code):
        _yield = Simulator(cash=self.cash, commission=self.commission).simulate_each(code=code,
            index_data=self.index_data, start_date=self.start_date, last_date=self.last_date, plot=False)
        return _yield

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.index = '^KS11'  # 코스피
        self.radioButton_kosdaq.clicked.connect(
            self.chage_filter_market_status)
        self.radioButton_kospi.clicked.connect(self.chage_filter_market_status)
        self.pushButton_filter.clicked.connect(self.filter_start)
        self.pushButton_start_simulation.clicked.connect(self.simulation_start)
        self.disable_all_children(self.groupBox_buy_condition)
        self.disable_all_children(self.groupBox_sell_condition)
        self.disable_all_children(self.groupBox_simulation)

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
        print('시뮬레이션 start')

        if self.radioButton_kosdaq.isChecked():
            self.index = '^KQ11'  # 코스닥
        elif self.radioButton_kospi.isChecked():
            self.index = '^KS11'  # 코스피
        self.cash = int(self.lineEdit_start_cash.text())
        self.commission = float(self.lineEdit_commission.text())

        # simulate_each(self, code="000660.KS", index='^KQ11', start_date='2018-01-01', last_date='2018-12-31', plot=True):
        self.start_date = self.comboBox_start_year.currentText(
        ) + "-" + self.comboBox_start_month.currentText() + "-01"
        self.last_date = self.comboBox_last_year.currentText(
        ) + "-" + self.comboBox_last_month.currentText() + "-31"

        self.index_data = bt.feeds.PandasData(dataname=yf.download(
            tickers=self.index, start_date=self.start_date, last_date=self.last_date, auto_adjust=True, progress=False))

        # self.tableWidget.setRowCount(len(self.filter_list))

        self.worker = Worker(codes_dataframe = self.filter_list, commission=self.commission, cash=self.cash,
                             index_data=self.index_data, start_date=self.start_date, last_date=self.last_date, core_num = 1, plot=False)
        self.worker.start()

    # def simulate_each(self, code):

    #     # called by each thread
    #     def get_web_data(url):
    #         return {'col1': 'something', 'request_data': requests.get(url).text}

    #     urls = ["http://google.com", "http://yahoo.com"]
    #     results = pool.map(get_web_data, urls)

    def filter_start(self):
        self.enable_all_children(self.groupBox_buy_condition)
        self.enable_all_children(self.groupBox_sell_condition)
        self.enable_all_children(self.groupBox_simulation)
        self.disable_all_children(self.groupBox_filter)

        dict = {}
        if self.radioButton_kosdaq.isChecked() is True:
            with open('kosdaq150.list', 'r') as file:
                for line in file:
                    code = line.strip()
                    dict[code] = "코스닥150"
        elif self.radioButton_kospi.isChecked() is True:
            with open('kospi200.list', 'r') as file:
                for line in file:
                    code = line.strip()
                    dict[code] = "코스피200"

        self.filter_list = pd.DataFrame(list(dict.items()),
                                        columns=('종목코드', '사장구분'))

        self.db_view_model = PandasModel(self.filter_list)
        self.tableView.setModel(self.db_view_model)
        self.tableView.resizeColumnToContents(0)


app = QApplication


def main_gui():
    global app
    app = QApplication(sys.argv)
    mainWindow = MainWindow()

    mainWindow.show()
    app.exec_()


if __name__ == "__main__":
    main_gui()
