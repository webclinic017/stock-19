# coding=utf-8
import win32com.client
import time
import csv
import pandas as pd
import creon_datareader

g_objCpStatus = win32com.client.Dispatch('CpUtil.CpCybos')
g_objCodeMgr =win32com.client.Dispatch('CpUtil.CpCodeMgr')
g_objFutureMgr = win32com.client.Dispatch('CpUtil.CpFutureCode')
g_objStockChart = win32com.client.Dispatch("CpSysDib.StockChart")
g_objCpSvr7254 = win32com.client.Dispatch('CpSysDib.CpSvr7254')  
# g_objCpTrade = win32com.client.Dispatch('CpUtil.CpTdUtil')

# original_func 콜하기 전에 PLUS 연결 상태 체크하는 데코레이터
def check_PLUS_status(original_func):

    def wrapper(*args, **kwargs):
        bConnect = g_objCpStatus.IsConnect
        if (bConnect == 0):
            print("PLUS가 정상적으로 연결되지 않음.")
            exit()

        return original_func(*args, **kwargs)

    return wrapper


# 서버로부터 과거의 차트 데이터 가져오는 클래스
class CpStockChart:
    def __init__(self):
        self.INTERVAL_TIME = 0.25
        

    def _check_rq_status(self):
        """
        g_objStockChart.BlockRequest() 로 요청한 후 이 메소드로 통신상태 검사해야함
        :return: None
        """
        rqStatus = g_objStockChart.GetDibStatus()
        rqRet = g_objStockChart.GetDibMsg1()
        if rqStatus == 0:
            pass
            # print("통신상태 정상[{}]{}".format(rqStatus, rqRet), end=' ')
        else:
            print("통신상태 오류[{}]{} 종료합니다..".format(rqStatus, rqRet))
            exit()

    # 차트 요청 - 최근일 부터 개수 기준
    @check_PLUS_status
    def RequestDay(self, caller: 'MainWindow', code = "A000020",  from_date=0):
        """
        http://cybosplus.github.io/cpsysdib_rtf_1_/stockchart.htm

        :param code: 종목코드
        :param dwm: 'D':일봉, 'W':주봉, 'M':월봉 (무조건 D)
        :param count: 요청할 데이터 개수
        :param caller: 이 메소드 호출한 인스턴스. 결과 데이터를 caller의 멤버로 전달하기 위함
        :return: None
        """
        g_objStockChart.SetInputValue(0, code)  # 종목코드
        count = 200000
        g_objStockChart.SetInputValue(1, ord('2'))  # 개수로 받기
        g_objStockChart.SetInputValue(4, count)  # 개수로 받기
            
        # 요청항목
        g_objStockChart.SetInputValue(5, [0, # 날짜
                                            2, # 시가
                                            3, # 고가
                                            4, # 저가
                                            5, # 종가
                                            8, # 거래량
                                            9, # 거래대금
                                            12, # 상장주식수
                                            13, # 시가총액
                                            14, # 외국인주문한도수량(ulong)
                                            15, #외국인주문가능수량(ulong)
                                            16, #외국인현보유수량(ulong)
                                            17, #외국인현보유비율(float)
                                            18, #수정주가일자(ulong) - YYYYMMDD
                                            19, #수정주가비율(float)
                                            20, #기관순매수(long)
                                            21, #기관누적순매수(long)
                                            22, #등락주선(long)
                                            23, #등락비율(float)
                                            24, #예탁금(ulonglong)
                                            25, #주식회전율(float)
                                            26, #거래성립률(float)
                                            ])
        # 요청한 항목들을 튜플로 만들어 사용
        rq_column = ('date', 'open', 'high', 'low', 'close', 'volume', 
                        '거래대금', '상장주식수','시가총액','외국인주문한도수량','외국인주문가능수량','외국인현보유수량','외국인현보유비율','수정주가일자','수정주가비율','기관순매수','기관누적순매수','등락주선','등락비율','예탁금','주식회전율','거래성립률')

        g_objStockChart.SetInputValue(6, ord('D'))  # '차트 주기 - 일/주/월
        g_objStockChart.SetInputValue(9, ord('1'))  # 수정주가 사용

        rcv_data = {}
        for col in rq_column:
            rcv_data[col] = []

        
        rcv_count = 0
        while count > rcv_count:
            g_objStockChart.BlockRequest()  # 요청! 후 응답 대기

            self._check_rq_status()  # 통신상태 검사 : 이상시 종료함! 

            time.sleep(self.INTERVAL_TIME)  # 시간당 RQ 제한으로 인해 장애가 발생하지 않도록 딜레이를 줌

            rcv_batch_len = g_objStockChart.GetHeaderValue(3)  # 받아온 데이터 개수

            for i in range(rcv_batch_len):
                for col_idx, col in enumerate(rq_column):
                    rcv_data[col].append(g_objStockChart.GetDataValue(col_idx, i))

            if len(rcv_data['date']) == 0:  # 데이터가 없는 경우
                print(code, '데이터 없음')
                return False

            # rcv_batch_len 만큼 받은 데이터의 가장 오래된 date
            rcv_oldest_date = rcv_data['date'][-1]
            rcv_latest_date = rcv_data['date'][0]

            rcv_count += rcv_batch_len
            caller.return_status_msg = '{} : {} ~ {}'.format(code,rcv_oldest_date,rcv_latest_date)

            # 서버가 가진 모든 데이터를 요청한 경우 break.
            # self.objStockChart.Continue 는 개수로 요청한 경우
            # count만큼 이미 다 받았더라도 계속 1의 값을 가지고 있어서
            # while 조건문에서 count > rcv_count를 체크해줘야 함.
            if not g_objStockChart.Continue:
                break
            if rcv_oldest_date < from_date:
                break

        caller.rcv_data = rcv_data  # 받은 데이터를 caller의 멤버에 저장
        return True

    def waitRqLimit(self, type):
        remainCount = g_objCpStatus.GetLimitRemainCount(type)

        if remainCount > 0 :
            True

        remainTime = g_objCpStatus.LimitRequestRemainTime
        print('조회 제한 회피 time wait %.2f초 ' % (remainTime /1000.0))
        time.sleep(remainTime/1000)
        return True

    def Request_investors_supply(self, code, rqCnt, in_NumOrMoney) :
        rqCnt = 20000

        g_objCpSvr7254.SetInputValue(0,code) # 종목코드
        g_objCpSvr7254.SetInputValue(1,6) # 일자별
        g_objCpSvr7254.SetInputValue(2,20180101) # 시작
        g_objCpSvr7254.SetInputValue(3,20180309) # 종료
        g_objCpSvr7254.SetInputValue(4,ord('0')) # 0 : 순매수 / 1 : 매매비중
        g_objCpSvr7254.SetInputValue(5,0) # 전체

        g_objCpSvr7254.SetInputValue(6,ord('1'))  # 1 : 순매수량 / 2 : 추정금액(백만)

        ret7254 = []

        while True:
            self.waitRqLimit(1)
            g_objCpSvr7254.BlockRequest()
            rqStatus = g_objCpSvr7254.GetDibStatus()
            if rqStatus != 0:
                return (False, ret7254)

            cnt = g_objCpSvr7254.GetHeaderValue(1)

            for i in range(cnt):
                item = {}
                fixed = g_objCpSvr7254.GetDataValue(18,i)
                #잠정치는 일단 버림
                if (fixed == ord('0')):
                    continue

                item['거래량'] = g_objCpSvr7254.GetDataValue(17,i)
                item['일자'] = g_objCpSvr7254.GetDataValue(0,i)
                item['종가'] = g_objCpSvr7254.GetDataValue(14,i)
                item['개인'] = g_objCpSvr7254.GetDataValue(1,i)
                item['외국인'] = g_objCpSvr7254.GetDataValue(2,i)
                item['기관'] = g_objCpSvr7254.GetDataValue(3,i)
                item['대비율'] = g_objCpSvr7254.GetDataValue(16,i)
                ret7254.append(item)

                if(len(ret7254) >=rqCnt):
                    break
            if g_objCpSvr7254.Continue == False:
                break
            if (len(ret7254) >= rqCnt) :
                break

        return (True, ret7254)

    # 차트 요청 - 분간, 틱 차트
    @check_PLUS_status
    def RequestMT(self, caller: 'MainWindow', code = "A000020", from_date=0):
        """
        :param code: 종목 코드
        :param dwm: 'm':분봉, 'T':틱봉
        :param tick_range: 1분봉 or 5분봉, ...
        :param count: 요청할 데이터 개수
        :param caller: 이 메소드 호출한 인스턴스. 결과 데이터를 caller의 멤버로 전달하기 위함
        :return:
        """
        count = 200000  # 서버 데이터 최대 reach 약 18.5만 이므로 (18/02/25 기준)
        g_objStockChart.SetInputValue(0, code)  # 종목코드

        if from_date == 0 :
            # g_objStockChart.SetInputValue(1, ord('1'))  # 기간으로 받기
            # g_objStockChart.SetInputValue(4, count)  # 조회 개수
            
            g_objStockChart.SetInputValue(1, ord('2'))  # 개수로 받기
            g_objStockChart.SetInputValue(4, count)  # 개수로 받기
        else :
            g_objStockChart.SetInputValue(1, ord('1'))  # 기간으로 받기
            g_objStockChart.SetInputValue(3, from_date)  # 기간으로 받기
            
        g_objStockChart.SetInputValue(5, [0, # 날짜
                                            1, # 시간
                                            2, # 시가
                                            3, # 고가
                                            4, # 저가
                                            5, # 종가
                                            8, # 거래량
                                            9, # 거래대금
                                            10, # 누적체결매도수량
                                            11, # 누적체결매수수량
                                            ])
        # 요청한 항목들을 튜플로 만들어 사용
        rq_column = ('date', 'time', 'open', 'high', 'low', 'close', 'volume', '거래대금','누적체결매도수량','누적체결매수수량')

        g_objStockChart.SetInputValue(6, ord('m'))  # '차트 주기 - 분
        g_objStockChart.SetInputValue(7, 1)  # 분틱차트 주기
        g_objStockChart.SetInputValue(9, ord('1'))  # 수정주가 사용

        rcv_data = {}
        for col in rq_column:
            rcv_data[col] = []

        rcv_count = 0
        while count > rcv_count:
            g_objStockChart.BlockRequest()  # 요청! 후 응답 대기
            self._check_rq_status()  # 통신상태 검사
            time.sleep(self.INTERVAL_TIME)  # 시간당 RQ 제한으로 인해 장애가 발생하지 않도록 딜레이를 줌

            rcv_batch_len = g_objStockChart.GetHeaderValue(3)  # 받아온 데이터 개수
            rcv_batch_len = min(rcv_batch_len, count - rcv_count)  # 정확히 count 개수만큼 받기 위함
            for i in range(rcv_batch_len):
                for col_idx, col in enumerate(rq_column):
                    rcv_data[col].append(g_objStockChart.GetDataValue(col_idx, i))

            if len(rcv_data['date']) == 0:  # 데이터가 없는 경우
                print(code, '데이터 없음')
                return False

            # len 만큼 받은 데이터의 가장 오래된 date
            rcv_oldest_date = int('{}{:04}'.format(rcv_data['date'][-1], rcv_data['time'][-1]))
            rcv_latest_date = int('{}{:04}'.format(rcv_data['date'][0], rcv_data['time'][0]))

            rcv_count += rcv_batch_len
            caller.return_status_msg = '{} : {} ~ {}'.format(code,rcv_oldest_date,rcv_latest_date)

            # 서버가 가진 모든 데이터를 요청한 경우 break.
            # g_objStockChart.Continue 는 개수로 요청한 경우
            # count만큼 이미 다 받았더라도 계속 1의 값을 가지고 있어서
            # while 조건문에서 count > rcv_count를 체크해줘야 함.
            if not g_objStockChart.Continue:
                break
            if rcv_oldest_date < from_date:
                break

        # 분봉의 경우 날짜와 시간을 하나의 문자열로 합친 후 int로 변환
        rcv_data['date'] = list(map(lambda x, y: int('{}{:04}'.format(x, y)),
                 rcv_data['date'], rcv_data['time']))
        del rcv_data['time']
        caller.rcv_data = rcv_data  # 받은 데이터를 caller의 멤버에 저장
        return True

# 종목코드 관리하는 클래스
class CpCodeMgr:
    def __init__(self):
        self.interval = 0.2

    # 마켓에 해당하는 종목코드 리스트 반환하는 메소드
    def get_code_list(self, market):
        """
        :param market: 1:코스피, 2:코스닥, ...
        :return: market에 해당하는 코드 list
        """
        code_list = g_objCodeMgr.GetStockListByMarket(market)
        return code_list

    # 부구분코드를 반환하는 메소드
    def get_section_code(self, code):
        section_code = g_objCodeMgr.GetStockSectionKind(code)
        return section_code

    # 종목 코드를 받아 종목명을 반환하는 메소드
    def get_code_name(self, code):
        code_name = g_objCodeMgr.CodeToName(code)
        return code_name

    def get_kospi200(self):
        allcodelist= g_objCodeMgr.GetGroupCodeList(180)
        return allcodelist
    
    def is_kospi200(self,code):
        allcodelist= g_objCodeMgr.GetStockKospi200Kind(code)
        return allcodelist
    
    def get_kosdaq150(self):
        allcodelist= g_objCodeMgr.GetGroupCodeList(390)
        return allcodelist

def create_index_list_file(index_kind):
    cpCodeMgr = CpCodeMgr()
    func = "cpCodeMgr.get_"+index_kind
    codes=eval(func)()
    if index_kind in "kospi200" : 
        ycode_postfix = ".KS"
    elif index_kind in "kosdaq150" : 
        ycode_postfix = ".KQ"
    dict ={}
    for code in codes :
        name = cpCodeMgr.get_code_name(code)
        ycode = code.split("A")[1]+ycode_postfix
        dict[code] = ycode, name, index_kind
    code_list = pd.DataFrame.from_dict(dict, orient='index', columns=('야후코드' ,'회사명',"시장구분"))
    code_list.index.name="종목코드"
    code_list.to_csv(index_kind+".csv",encoding='utf-8-sig')

if __name__ == "__main__":
    # create_index_list_file("kospi200")
    # create_index_list_file("kosdaq150")
    creon_datareader.main_gui()    
