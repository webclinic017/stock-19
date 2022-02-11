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

import io
import multiprocessing as mp
from pandas_to_pyqt_table import PandasModel
from simulator_core import Simulator
import math
import time
from multiprocessing.dummy import Pool as ThreadPool
import sys
from PIL import Image
from pytracing import TraceProfiler
from pycrunch_trace.client.api import trace

# .ui 파일에서 직접 클래스 생성하는 경우 주석 해제
Ui_MainWindow = uic.loadUiType("simulator_v0.2.ui")[0]


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # timer 등록. tick per 1s
        self.timer_1s = QTimer(self)
        self.timer_1s.start(1000)
        self.timer_1s.timeout.connect(self.timeout_1s)
        self.update_status_msg = ""
        self.center()

        self.groupbox_filter_init()
        self.groupbox_simulation_init()

        self.pushButton_profile.clicked.connect(self.profile_start_finish)
        self.disable_all_children(self.groupBox_buy_condition)
        self.disable_all_children(self.groupBox_sell_condition)
        self.disable_all_children(self.groupBox_simulation)
        self.myDataReader = my_data_reader.MyDataReader()

        self.lineEdit_rsi_first_buy.textChanged.connect(
            self.get_lineedit_numbers)
        self.lineEdit_rsi_second_buy.textChanged.connect(
            self.get_lineedit_numbers)
        self.lineEdit_rsi_third_buy.textChanged.connect(
            self.get_lineedit_numbers)
        self.is_profiling = False

    def profile_start_finish(self):
        if self.is_profiling == False:
            print("off -> on")
            self.filename = './simul.out'
            self.fh = io.open(self.filename, mode='w', encoding='utf-8')
            self.tp = TraceProfiler(output=self.fh)
            self.tp.install()
            self.pushButton_profile.setText("성능 프로파일링 중...")
            self.is_profiling = True
        else:
            print("on -> off")
            self.tp.shutdown()
            print('wrote ' + self.filename)
            self.pushButton_profile.setText("성능 프로파일링 종료")
            self.pushButton_profile.setEnabled(False)
            self.fh.close()

    def groupbox_filter_init(self):
        self.index = '^KS11'  # 코스피
        self.radioButton_kosdaq.clicked.connect(
            self.chage_filter_market_status)
        self.pushButton_filter.clicked.connect(self.filter_start)
        self.radioButton_kospi.clicked.connect(self.chage_filter_market_status)

    def groupbox_simulation_init(self):
        self.pushButton_start_simulation.clicked.connect(self.simulation_start)
        self.pushButton_simulation_retry.clicked.connect(
            self.pushButton_simulation_clear)
        self.tableView_result.clicked.connect(self.tableView_result_clicked)

    def pushButton_simulation_clear(self):
        self.tableView_result.clearSpans()

    def get_lineedit_numbers(self):
        first = int(self.lineEdit_rsi_first_buy.text())
        second = int(self.lineEdit_rsi_second_buy.text())
        third = int(self.lineEdit_rsi_third_buy.text())
        self.lineEdit_rsi_first_buy_total.setText(str(first))
        self.lineEdit_rsi_second_buy_total.setText(str(first+second))
        self.lineEdit_rsi_third_buy_total.setText(str(first+second + third))

    def tableView_result_clicked(self, item):
        cellContent = item.data()
        print(cellContent)  # test
        sf = "You clicked on {}".format(cellContent)
        print(sf)
        if "png" in cellContent:
            image = Image.open(cellContent)
            image.show()
        if "자세히 보기" in cellContent:
            code = cellContent.split()[2]
            Simulator(cash=self.cash, commission=self.commission, dataReader=self.myDataReader).simulate_each(code=code,index_data=self.index_data, start_date=self.start_date, last_date=self.last_date, plot=True, db="MyDataReader")

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
        
    
    @trace(additional_excludes=['C:/Users/qmxmp/.conda/envs/py38_64/lib/site-packages/backtrader',
                                "C:/Users/qmxmp/.conda/envs/py38_64/lib/site-packages/pandas"])
    def simulation_start(self,trace):

        # self.disable_all_children(self.groupBox_buy_condition)
        # self.disable_all_children(self.groupBox_sell_condition)
        # self.disable_all_children(self.groupBox_simulation)
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

        self.start_date = self.comboBox_start_year.currentText(
        ) + "-" + self.comboBox_start_month.currentText() + "-01"
        self.last_date = self.comboBox_last_year.currentText(
        ) + "-" + self.comboBox_last_month.currentText() + "-31"

        self.index_data = bt.feeds.PandasData(dataname=yf.download(
            tickers=self.index, start=self.start_date, end=self.last_date, auto_adjust=True, progress=True))

        start = time.time()
        total = self.filter_list.shape[0]

        result_dict = {}
        i = 0
        for index, row in self.filter_list.iterrows():
            code = row['종목코드']
            result, filename = self.calculate_yield(code)
            self.update_status_msg = str(index) + " / " + str(total)
            result_dict[code] = row['회사명'], round(result, 2), filename
            if self.checkBox_test.isChecked():
                if i == 10:
                    break
                else:
                    i = i+1

        result_dataframe = pd.DataFrame.from_dict(
            result_dict, orient='index', columns=('종목명', '수익율', "파일명"))
        result_dataframe.index.name = "종목코드"
        result_dataframe.to_csv("result.csv", encoding='utf-8-sig')
        result_dataframe = pd.read_csv("result.csv")
        self.db_view_model = PandasModel(result_dataframe)
        self.tableView_result.setModel(self.db_view_model)
        self.tableView_result.resizeColumnToContents(0)

        end = time.time()
        print("Total Simulation time : %0.2f sec" % (end - start))

    def calculate_yield(self, code):
        _yield, filename = Simulator(cash=self.cash, commission=self.commission, dataReader=self.myDataReader).simulate_each(code=code,
                                                                                                                             index_data=self.index_data, start_date=self.start_date, last_date=self.last_date, plot=False, db="MyDataReader")
        return _yield, filename

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
