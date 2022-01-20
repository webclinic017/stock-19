# coding=utf-8
import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import QtGui
from PyQt5 import uic

import pandas as pd
from pandas_to_pyqt_table import PandasModel

# .ui 파일에서 직접 클래스 생성하는 경우 주석 해제
Ui_MainWindow = uic.loadUiType("justin_simulator.ui")[0]

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)  
        # self.kosdaq = False
        # self.kospi = False
        self.checkbox_filter_kosdaq.stateChanged.connect(self.chage_filter_kosdaq_status)
        self.checkbox_filter_kospi.stateChanged.connect(self.chage_filter_kospi_status)
        self.pushButton_filter.clicked.connect(self.filter_start)
        self.center()

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def chage_filter_kosdaq_status(self,state) :
        self.kosdaq = True if state ==2 else self.kosdaq == False
        print("self.kosdaq =" + str(self.kosdaq))
        
    def chage_filter_kospi_status(self,state) :
        self.kospi = True if state ==2 else self.kospi == False
        print("self.kospi = " + str(self.kospi))
    
    def filter_start(self) : 
        self.pushButton_filter.setEnabled(False)
        
        dict = {}
        if self.checkbox_filter_kosdaq.isChecked() is True:
            with open('kosdaq150.list','r') as file:
                for line in file: 
                    code = line.strip()
                    dict[code] = "코스닥150"
        if self.checkbox_filter_kospi.isChecked() is True:
            with open('kospi200.list','r') as file:
                for line in file : 
                    code = line.strip()
                    dict[code] = "코스피200"

        filter_list = pd.DataFrame(list(dict.items()),
                                       columns=('종목코드', '사장구분'))

        self.db_view_model = PandasModel(filter_list)
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