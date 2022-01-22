# coding=utf-8
import sqlite3
import pandas as pd
import os

class MyDataReader:
    def __init__(self):
        # print(os.getcwd())
        self.datapath = ('../Creon-Datareader-master/db/일봉/일봉_전종목.db')
        if os.path.exists(self.datapath):
            print("DB file is OK! ("+self.datapath+")")
        else:
            print(self.datapath + " in not exist!")

    # code = "D0011025" # 코나아이
    # code = "A052400 # 코나아이
    # code = "A005930" # 삼성전자
    # code = "A306200" # 세아제강
    def get_data_with_time(self, code="A052400", start_date=20201201, last_date=20220101):
        con = sqlite3.connect(self.datapath)
        query = 'SELECT * FROM ' + code + ' WHERE date BETWEEN ' + str(start_date) + ' AND ' + str(last_date)
        # print(query)
        dataframe = pd.read_sql(query, con)
        # print("get_data_with_time : " + dataframe.head(5))              
        dataframe['date'] = pd.to_datetime(
            dataframe['date'], format='%Y%m%d', errors='raise')
        dataframe.rename(columns={'date': 'datetime'}, inplace=True)
        # dataframe.columns.values[0] = 'datetime'
        dataframe.set_index('datetime', inplace=True)  
        return dataframe

if __name__ == "__main__":
    MyDataReader().get_data_with_time().head(5)
