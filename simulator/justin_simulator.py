# coding=utf-8
import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import QtGui
from PyQt5 import uic

# .ui 파일에서 직접 클래스 생성하는 경우 주석 해제
Ui_MainWindow = uic.loadUiType("justin_simulator.ui")[0]

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

app = QApplication

def main_gui():
    global app
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    app.exec_()

if __name__ == "__main__":
    main_gui()