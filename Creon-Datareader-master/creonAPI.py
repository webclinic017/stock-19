# coding=utf-8
import win32com.client
import time

g_objCpStatus = win32com.client.Dispatch('CpUtil.CpCybos')
g_objCodeMgr =win32com.client.Dispatch('CpUtil.CpCodeMgr')
# g_objCpTrade = win32com.client.Dispatch('CpUtil.CpTdUtil')
g_objFutureMgr = win32com.client.Dispatch('CpUtil.CpFutureCode')


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
        self.objStockChart = win32com.client.Dispatch("CpSysDib.StockChart")

    def _check_rq_status(self):
        """
        self.objStockChart.BlockRequest() 로 요청한 후 이 메소드로 통신상태 검사해야함
        :return: None
        """
        rqStatus = self.objStockChart.GetDibStatus()
        rqRet = self.objStockChart.GetDibMsg1()
        if rqStatus == 0:
            pass
            # print("통신상태 정상[{}]{}".format(rqStatus, rqRet), end=' ')
        else:
            print("통신상태 오류[{}]{} 종료합니다..".format(rqStatus, rqRet))
            exit()

    # 차트 요청 - 최근일 부터 개수 기준
    @check_PLUS_status
    def RequestDWM(self, code, dwm, count, caller: 'MainWindow', from_date=0, ohlcv_only=True):
        """
        :param code: 종목코드
        :param dwm: 'D':일봉, 'W':주봉, 'M':월봉
        :param count: 요청할 데이터 개수
        :param caller: 이 메소드 호출한 인스턴스. 결과 데이터를 caller의 멤버로 전달하기 위함
        :return: None
        """
        self.objStockChart.SetInputValue(0, code)  # 종목코드
        self.objStockChart.SetInputValue(1, ord('2'))  # 개수로 받기
        self.objStockChart.SetInputValue(4, count)  # 최근 count개

        if ohlcv_only:
            self.objStockChart.SetInputValue(5, [0, 2, 3, 4, 5, 8])  # 요청항목 - 날짜,시가,고가,저가,종가,거래량
            rq_column = ('date', 'open', 'high', 'low', 'close', 'volume')
        else:
            # 요청항목
            self.objStockChart.SetInputValue(5, [0, # 날짜
                                                2, # 시가
                                                3, # 고가
                                                4, # 저가
                                                5, # 종가
                                                8, # 거래량
                                                13,  # 시가총액
                                                16,  # 외국인현보유수량
                                                20,  # 기관순매수
                                                ])
            # 요청한 항목들을 튜플로 만들어 사용
            rq_column = ('date', 'open', 'high', 'low', 'close', 'volume', 
                         '시가총액', '외국인현보유수량', '기관순매수')

        self.objStockChart.SetInputValue(6, dwm)  # '차트 주기 - 일/주/월
        self.objStockChart.SetInputValue(9, ord('1'))  # 수정주가 사용

        rcv_data = {}
        for col in rq_column:
            rcv_data[col] = []

        rcv_count = 0
        while count > rcv_count:
            self.objStockChart.BlockRequest()  # 요청! 후 응답 대기
            self._check_rq_status()  # 통신상태 검사
            time.sleep(self.INTERVAL_TIME)  # 시간당 RQ 제한으로 인해 장애가 발생하지 않도록 딜레이를 줌

            rcv_batch_len = self.objStockChart.GetHeaderValue(3)  # 받아온 데이터 개수
            rcv_batch_len = min(rcv_batch_len, count - rcv_count)  # 정확히 count 개수만큼 받기 위함
            for i in range(rcv_batch_len):
                for col_idx, col in enumerate(rq_column):
                    rcv_data[col].append(self.objStockChart.GetDataValue(col_idx, i))

            if len(rcv_data['date']) == 0:  # 데이터가 없는 경우
                print(code, '데이터 없음')
                return False

            # rcv_batch_len 만큼 받은 데이터의 가장 오래된 date
            rcv_oldest_date = rcv_data['date'][-1]

            rcv_count += rcv_batch_len
            caller.return_status_msg = '{} / {}'.format(rcv_count, count)

            # 서버가 가진 모든 데이터를 요청한 경우 break.
            # self.objStockChart.Continue 는 개수로 요청한 경우
            # count만큼 이미 다 받았더라도 계속 1의 값을 가지고 있어서
            # while 조건문에서 count > rcv_count를 체크해줘야 함.
            if not self.objStockChart.Continue:
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
        self.objRq = win32com.client.Dispatch('CpSysDib.CpSvr7254')  

        self.objRq.SetInputValue(0,code) # 종목코드
        self.objRq.SetInputValue(1,6) # 일자별
        self.objRq.SetInputValue(2,20180101) # 시작
        self.objRq.SetInputValue(3,20180309) # 종료
        self.objRq.SetInputValue(4,ord('0')) # 0 : 순매수 / 1 : 매매비중
        self.objRq.SetInputValue(5,0) # 전체

        self.objRq.SetInputValue(6,ord('1'))  # 1 : 순매수량 / 2 : 추정금액(백만)

        ret7254 = []

        while True:
            self.waitRqLimit(1)
            self.objRq.BlockRequest()
            rqStatus = self.objRq.GetDibStatus()
            if rqStatus != 0:
                return (False, ret7254)

            cnt = self.objRq.GetHeaderValue(1)

            for i in range(cnt):
                item = {}
                fixed = self.objRq.GetDataValue(18,i)
                #잠정치는 일단 버림
                if (fixed == ord('0')):
                    continue

                item['거래량'] = self.objRq.GetDataValue(17,i)
                item['일자'] = self.objRq.GetDataValue(0,i)
                item['종가'] = self.objRq.GetDataValue(14,i)
                item['개인'] = self.objRq.GetDataValue(1,i)
                item['외국인'] = self.objRq.GetDataValue(2,i)
                item['기관'] = self.objRq.GetDataValue(3,i)
                item['대비율'] = self.objRq.GetDataValue(16,i)
                ret7254.append(item)

                if(len(ret7254) >=rqCnt):
                    break
            if self.objRq.Continue == False:
                break
            if (len(ret7254) >= rqCnt) :
                break

        return (True, ret7254)

    # 차트 요청 - 분간, 틱 차트
    @check_PLUS_status
    def RequestMT(self, code, dwm, tick_range, count, caller: 'MainWindow', from_date=0, ohlcv_only=True):
        """
        :param code: 종목 코드
        :param dwm: 'm':분봉, 'T':틱봉
        :param tick_range: 1분봉 or 5분봉, ...
        :param count: 요청할 데이터 개수
        :param caller: 이 메소드 호출한 인스턴스. 결과 데이터를 caller의 멤버로 전달하기 위함
        :return:
        """
        self.objStockChart.SetInputValue(0, code)  # 종목코드
        self.objStockChart.SetInputValue(1, ord('2'))  # 개수로 받기
        self.objStockChart.SetInputValue(4, count)  # 조회 개수
        if ohlcv_only:
            self.objStockChart.SetInputValue(5, [0, 1, 2, 3, 4, 5, 8])  # 요청항목 - 날짜, 시간,시가,고가,저가,종가,거래량
            rq_column = ('date', 'time', 'open', 'high', 'low', 'close', 'volume')
        else:
            # 요청항목
            self.objStockChart.SetInputValue(5, [0, # 날짜
                                                1, # 시간
                                                2, # 시가
                                                3, # 고가
                                                4, # 저가
                                                5, # 종가
                                                8, # 거래량
                                                13,  # 시가총액
                                                14,  # 외국인주문한도수량
                                                16,  # 외국인현보유수량
                                                17,  # 외국인현보유비율
                                                20,  # 기관순매수
                                                21,  # 기관누적순매수
                                                ])
            # 요청한 항목들을 튜플로 만들어 사용
            rq_column = ('date', 'time', 'open', 'high', 'low', 'close', 'volume', 
                         '시가총액', '외국인주문한도수량', '외국인현보유수량', '외국인현보유비율', '기관순매수', '기관누적순매수')

        self.objStockChart.SetInputValue(6, dwm)  # '차트 주기 - 분/틱
        self.objStockChart.SetInputValue(7, tick_range)  # 분틱차트 주기
        self.objStockChart.SetInputValue(9, ord('1'))  # 수정주가 사용

        rcv_data = {}
        for col in rq_column:
            rcv_data[col] = []

        rcv_count = 0
        while count > rcv_count:
            self.objStockChart.BlockRequest()  # 요청! 후 응답 대기
            self._check_rq_status()  # 통신상태 검사
            time.sleep(self.INTERVAL_TIME)  # 시간당 RQ 제한으로 인해 장애가 발생하지 않도록 딜레이를 줌

            rcv_batch_len = self.objStockChart.GetHeaderValue(3)  # 받아온 데이터 개수
            rcv_batch_len = min(rcv_batch_len, count - rcv_count)  # 정확히 count 개수만큼 받기 위함
            for i in range(rcv_batch_len):
                for col_idx, col in enumerate(rq_column):
                    rcv_data[col].append(self.objStockChart.GetDataValue(col_idx, i))

            if len(rcv_data['date']) == 0:  # 데이터가 없는 경우
                print(code, '데이터 없음')
                return False

            # len 만큼 받은 데이터의 가장 오래된 date
            rcv_oldest_date = int('{}{:04}'.format(rcv_data['date'][-1], rcv_data['time'][-1]))

            rcv_count += rcv_batch_len
            caller.return_status_msg = '{} / {}(maximum)'.format(rcv_count, count)

            # 서버가 가진 모든 데이터를 요청한 경우 break.
            # self.objStockChart.Continue 는 개수로 요청한 경우
            # count만큼 이미 다 받았더라도 계속 1의 값을 가지고 있어서
            # while 조건문에서 count > rcv_count를 체크해줘야 함.
            if not self.objStockChart.Continue:
                break
            if rcv_oldest_date < from_date:
                break

        # 분봉의 경우 날짜와 시간을 하나의 문자열로 합친 후 int로 변환
        rcv_data['date'] = list(map(lambda x, y: int('{}{:04}'.format(x, y)),
                 rcv_data['date'], rcv_data['time']))
        del rcv_data['time']
        caller.rcv_data = rcv_data  # 받은 데이터를 caller의 멤버에 저장
        return True

objStockChart = CpStockChart()
ret, ret7254 = objStockChart.Request_investors_supply("A000020", 20000 , in_NumOrMoney = 1)
if ret == False : 
    print(' 7254 요청 실패')
print(ret7254)