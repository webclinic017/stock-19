# coding=utf-8
import sys
import os
import gc
from itsdangerous import TimedJSONWebSignatureSerializer
import pandas as pd
import tqdm as tqdm
import sqlite3

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import QtGui
from PyQt5 import uic

import numpy as np

import creonAPI
import decorators
from pandas_to_pyqt_table import PandasModel
# from creon_datareader_ui import Ui_MainWindow
from utils import is_market_open, available_latest_date, preformat_cjk

# .ui 파일에서 직접 클래스 생성하는 경우 주석 해제
Ui_MainWindow = uic.loadUiType("creon_datareader.ui")[0]


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.objStockChart = creonAPI.CpStockChart()
        self.objCodeMgr = creonAPI.CpCodeMgr()
        self.objStockChart.INTERVAL_TIME = 0.2

        self.rcv_data = dict()  # RQ후 받아온 데이터 저장 멤버
        self.update_status_msg = ''  # status bar 에 출력할 메세지 저장 멤버
        self.return_status_msg = ''  # status bar 에 출력할 메세지 저장 멤버

        # timer 등록. tick per 1s
        self.timer_1s = QTimer(self)
        self.timer_1s.start(1000)
        self.timer_1s.timeout.connect(self.timeout_1s)

        # 서버에 존재하는 종목코드 리스트와 로컬DB에 존재하는 종목코드 리스트
        self.df_code_name_from_server = pd.DataFrame()
        # self.db_code_day_latest_df = pd.DataFrame()

        self.db_directory = ''

        # 기존 저장된 분봉/일봉 데이터 불러오기
        self.connect_code_list_view()

        # 다운로드 클릭시 서버에서 데이터 받아오기
        self.pushButton.clicked.connect(self.update_price_db)

        # 일부 "/" 가 들어간 종목명 blacklist 처리
        self.blacklist = ['Q500058', 'Q530072', 'Q550060']

    def closeEvent(self, a0: QtGui.QCloseEvent):
        sys.exit()

    def connect_code_list_view(self):
        # DB 경로 가져오기
        db_directory = self.lineEdit.text()

        # 분봉 디렉토리 설정 후 없으면 생성
        self.directory_min_db = db_directory+"/분봉"
        if not os.path.exists(self.directory_min_db):
            os.makedirs(self.directory_min_db)
        self.file_lists = os.listdir(self.directory_min_db)

        # 일봉 디렉토리 설정 후 없으면 생성, 일봉 파일 설정
        db_directory_day = db_directory + "/일봉/"
        if not os.path.exists(db_directory_day):
            os.makedirs(db_directory_day)
        self.db_file_day = db_directory_day + "일봉_전종목.db"

        # 서버 종목 정보 가져와서 dataframe으로 저장
        self.code_list = self.objCodeMgr.get_code_list(
            1) + self.objCodeMgr.get_code_list(2)
        self.name_list = list(
            map(self.objCodeMgr.get_code_name, self.code_list))
        self.df_code_name_from_server = pd.DataFrame({'종목코드': self.code_list, '종목명': self.name_list},
                                                     columns=('종목코드', '종목명'))

        df_latest_min_db = self.get_df_latest_min_db()
        df_latest_day_db = self.get_df_latest_day_db()

        self.df_code_name_latest_db = pd.merge(
            self.df_code_name_from_server, df_latest_min_db, how='outer', on='종목코드')
        self.df_code_name_latest_db = pd.merge(
            self.df_code_name_latest_db, df_latest_day_db, how='outer', on='종목코드')
        self.df_code_name_latest_db["파일명"] = "분봉_" + self.df_code_name_latest_db["종목코드"] + \
            "_" + self.df_code_name_latest_db["종목명"] + ".db"
        self.df_code_name_latest_db.fillna(0, inplace=True)

        self.db_view_model = PandasModel(self.df_code_name_latest_db)
        self.tableView.setModel(self.db_view_model)
        self.tableView.resizeColumnToContents(0)

    def get_df_latest_min_db(self):
        # 파일 리스트에서 분봉 갱신일자 가져오기
        self.dict_file_latest_list = {}
        from_date = np.dtype(np.int64)
        for file in self.file_lists:
            file_path = self.directory_min_db + "/" + file
            if not os.path.exists(file_path):
                print(file_path + " is not exist")
                self.dict_file_latest_list[code] = from_date
                continue

            con = sqlite3.connect(file_path)
            cursor = con.cursor()
            code = file.split("_")[1]
            try:
                cursor.execute(
                    "SELECT date FROM stock ORDER BY date DESC LIMIT 1")
                from_date = cursor.fetchall()[0][0]
                self.dict_file_latest_list[code] = from_date
            except:
                print("Exception : " + file +
                      " has no from_date. Set from_date to 0")
                self.dict_file_latest_list[code] = 0
                con.close()
                os.remove(file_path)

        db_code_min_latest_df = pd.DataFrame(list(self.dict_file_latest_list.items()),
                                             columns=('종목코드', '분봉 갱신날짜'))

        return db_code_min_latest_df

    def get_df_latest_day_db(self):
        # 로컬 DB에 저장된 종목 정보 가져와서 dataframe으로 저장
        # print(os.getcwd() + str(os.path.exists(self.db_file_day)) )

        con = sqlite3.connect(self.db_file_day)
        cursor = con.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        db_code_list = cursor.fetchall()

        dict_df_code_latest = {}
        try:
            for db_code in db_code_list:
                cmd = "SELECT date FROM {} ORDER BY date DESC LIMIT 1".format(
                    db_code[0])
                cursor.execute(cmd)
                dict_df_code_latest[db_code[0]] = cursor.fetchall()[0][0]
        except IndexError:
            print("Exception : " + db_code + " no data. skip")

        db_code_day_latest_df = pd.DataFrame(list(dict_df_code_latest.items()),
                                             columns=('종목코드', '일봉 갱신날짜'))

        return db_code_day_latest_df

    def update_price_db(self):
        self.pushButton.setEnabled(False)

        # 분봉/일봉에 대해서만 아래 코드가 효과가 있음.
        if is_market_open():
            print("ERROR: 장중에는 데이터 수집에 오류가 있을 수 있습니다.")

        if self.comboBox.currentText() in "일봉":
            self.update_price_db_day()
            self.update_price_db_min()
        else:
            self.update_price_db_min()
            self.update_price_db_day()

        self.pushButton.setEnabled(False)

    @decorators.return_status_msg_setter
    def update_price_db_min(self):
        count = 200000  # 서버 데이터 최대 reach 약 18.5만 이므로 (18/02/25 기준)
        tick_range = 1
        columns = ['open', 'high', 'low', 'close', 'volume']

        from_date = np.dtype(np.int64)
        for index, row in tqdm.tqdm(self.df_code_name_latest_db.iterrows(), total=self.df_code_name_latest_db.shape[0]):

            file_path = self.directory_min_db + "/" + row['파일명']
            code = row['종목코드']
            name = row['종목명']
            if code in self.blacklist:
                continue

            with sqlite3.connect(file_path) as con:
                # self.update_status_msg = '[{}] {}'.format(code, name)
                # t.set_description(preformat_cjk(self.update_status_msg, 25))
                # t.update(1)

                if row['분봉 갱신날짜']:
                    from_date = row['분봉 갱신날짜']
                else:
                    from_date = 0

                if self.objStockChart.RequestMT(code, ord('m'), tick_range, count, self, from_date, ohlcv_only=True) == False:
                    print("RequestMT() return False")
                    continue

                df = pd.DataFrame(self.rcv_data, columns=columns,
                                  index=self.rcv_data['date'])

                # 기존 DB와 겹치는 부분 제거
                if from_date != 0:
                    df = df.loc[:from_date]
                    df = df.iloc[:-1]

                # 뒤집어서 저장 (결과적으로 date 기준 오름차순으로 저장됨)
                df = df.iloc[::-1]
                df.to_sql(name="stock", con=con,
                          if_exists='append', index_label='date')

                # 메모리 overflow 방지
                del df
                gc.collect()

        self.connect_code_list_view()

    @decorators.return_status_msg_setter
    def update_price_db_day(self, count=1):
        columns = ['open', 'high', 'low', 'close', 'volume', '거래대금', '상장주식수', '시가총액', '외국인주문한도수량', '외국인주문가능수량',
                   '외국인현보유수량', '외국인현보유비율', '수정주가일자', '수정주가비율', '기관순매수', '기관누적순매수', '등락주선', '등락비율', '예탁금', '주식회전율', '거래성립률']

        with sqlite3.connect(self.db_file_day) as con:
            cursor = con.cursor()
            count = 0
            total = self.df_code_name_latest_db.shape[0]
            for index, row in tqdm.tqdm(self.df_code_name_latest_db.iterrows(), total=total):
                code = row['종목코드']

                if row['일봉 갱신날짜']:
                    from_date = row['일봉 갱신날짜']
                else:
                    from_date = 20020101

                if self.objStockChart.RequestDay(self, code = code,  from_date = from_date) == False:
                    print("RequestDWM() return False")
                    continue

                df = pd.DataFrame(self.rcv_data, columns=columns,
                                  index=self.rcv_data['date'])
                # df['외국인 순매수']
                # 기존 DB와 겹치는 부분 제거
                if from_date != 0:
                    df = df.loc[:from_date]
                    df = df.iloc[:-1]

                # 뒤집어서 저장 (결과적으로 date 기준 오름차순으로 저장됨)
                df = df.iloc[::-1]
                df.to_sql(code, con, if_exists='append', index_label='date')

                # 메모리 overflow 방지
                del df
                gc.collect()
                self.update_status_msg = '{} / {}'.format(count, total)
                count += 1

        self.connect_code_list_view()

    def timeout_1s(self):
        current_time = QTime.currentTime()

        text_time = current_time.toString("hh:mm:ss")
        time_msg = "현재시간: " + text_time

        if self.return_status_msg == '':
            statusbar_msg = time_msg
        else:
            statusbar_msg = time_msg + " | " + self.update_status_msg + \
                " | " + self.return_status_msg

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
