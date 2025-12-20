import sys
import json
import time
import pandas as pd
from PyQt5.QtWidgets import QApplication
from PyQt5.QAxContainer import QAxWidget

# 일봉 데이터 수집기 클래스 정의
class Kiwoom:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.ocx = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")

        # 이벤트 핸들 연결
        self.ocx.OnEventConnect.connect(self._on_login)
        self.ocx.OnReceiveTrData.connect(self._on_receive_tr_data)

        self.login_ok = False
        self.tr_data = None
        self.data_ready = False

    def connect(self):
        self.ocx.dynamicCall("CommConnect()")
        self.app.exec_()

    def _on_login(self, err_code):
        if err_code == 0:
            print(">> 로그인 성공")
            self.login_ok = True
        else:
            print(">> 로그인 실패")
        self.app.quit()

    def get_code_list(self):
        kospi = self.ocx.dynamicCall("GetCodeListByMarket(QString)", ["0"]).split(';')
        kosdaq = self.ocx.dynamicCall("GetCodeListByMarket(QString)", ["10"]).split(';')
        codes = list(filter(None, kospi + kosdaq))
        print(f">> 총 종목 수: {len(codes)}")
        return codes

    def get_stock_name(self, code):
        return self.ocx.dynamicCall("GetMasterCodeName(QString)", [code])

    def is_valid_stock(self, code, name):
        keywords = ['ETF', 'ETN', '리츠', '스팩', '레버리지', '인버스', 'KODEX', 'TIGER', 'KBSTAR', 'KIWOOM',
                    'TIMEFOLIO', '1Q', 'BNK', 'HK', 'UNICORN', 'RISE', 'WON', 'ACE', 'PLUS', 'KoAct', 'HANARO', 'SOL']
        if any(k in name for k in keywords):
            return False
        # 거래정지 확인
        status = self.ocx.dynamicCall("GetMasterStockState(QString)", [code])
        status_keywords = ['거래정지', '관리종목', '감리종목', '투자유의종목']
        if any(k in status for k in status_keywords):
            return False
        return True

    def get_ohlcv(self, code):
        self.tr_data = []
        self.data_ready = False

        self.ocx.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
        self.ocx.dynamicCall("SetInputValue(QString, QString)", "기준일자", "")
        self.ocx.dynamicCall("SetInputValue(QString, QString)", "수정주가구분", "1")
        self.ocx.dynamicCall("CommRqData(QString, QString, int, QString)",
                             "opt10081_req", "opt10081", 0, "0101")
        while not self.data_ready:
            self.app.processEvents()
        return self.tr_data

    def _on_receive_tr_data(self, screen_no, rqname, trcode, recordname, prev_next):
        count = self.ocx.dynamicCall("GetRepeatCnt(QString, QString)", trcode, rqname)
        result = []

        for i in range(count):
            date = self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)",
                                        trcode, rqname, i, "일자").strip()
            open_ = self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)",
                                         trcode, rqname, i, "시가").strip()
            high = self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)",
                                        trcode, rqname, i, "고가").strip()
            low = self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)",
                                       trcode, rqname, i, "저가").strip()
            close = self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)",
                                         trcode, rqname, i, "현재가").strip()
            volume = self.ocx.dynamicCall("GetCommData(QString, QString, int, QString)",
                                          trcode, rqname, i, "거래량").strip()

            result.append({
                "date": date,
                "open": int(open_),
                "high": int(high),
                "low": int(low),
                "close": int(close),
                "volume": int(volume)
            })

        self.tr_data = result[:240]  # 최대 240개만 저장
        #self.tr_data = result  # 최대 240개만 저장
        self.data_ready = True

# 기본 컨디션 계산
# EMA 이동평균선
def EMA(series, span):
    return series.ewm(span=span, adjust=False).mean()

# --------------------------
# 실행 메인 함수
# --------------------------
if __name__ == "__main__":
    kiwoom = Kiwoom()
    kiwoom.connect()

    all_data = {}
    codes = kiwoom.get_code_list()

    for idx, code in enumerate(codes):
        name = kiwoom.get_stock_name(code)
        if not kiwoom.is_valid_stock(code, name):
            continue

        print(f"[{idx+1}/{len(codes)}] {code} {name} 데이터 요청 중...")
        try:
            ohlcv = kiwoom.get_ohlcv(code)
            all_data[code] = {
                "name": name,
                "ohlcv": ohlcv
            }
        except Exception as e:
            print(f"  >> {code} {name} 실패: {e}")
        time.sleep(0.25)  # 과도한 요청 방지

    with open("all_stock_data.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)

    print("✅ 모든 데이터 저장 완료: all_stock_data.json")

    # 파일 불러오기
    with open("all_stock_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    selected = []

    for code, info in data.items():
        name = info["name"]
        ohlcv = pd.DataFrame(info["ohlcv"])
        if len(ohlcv) < 60:  # 데이터 부족시 스킵
            continue

        # 쌓이는 순서, 날짜 기준으로 오름차순
        ohlcv = ohlcv.sort_values("date")

        # condition 1  주봉 20 이동평균과 종가 만나는 조건 ===
        ohlcv["date"] = pd.to_datetime(ohlcv["date"], format="%Y%m%d")
        ohlcv.set_index("date", inplace=True)
        weekly = ohlcv.resample("W").last()  # 주봉 데이터 (마지막 거래일 종가)
        weekly["ma20"] = weekly["close"].rolling(20).mean()

        if len(weekly.dropna()) == 0:
            continue

        latest_week_close = weekly["close"].iloc[-1]
        latest_week_ma20 = weekly["ma20"].iloc[-1]

        cond1 = abs(latest_week_close - latest_week_ma20) / latest_week_ma20 < 0.01  # 1% 이내 차이

        # condition 2, 일봉 정배열 5 < 20일 기준
        ohlcv["ma5"] = ohlcv["close"].rolling(5).mean()
        ohlcv["ma20"] = ohlcv["close"].rolling(20).mean()
        cond2 = ohlcv["ma5"].iloc[-1] > ohlcv["ma20"].iloc[-1]

        # condition 3, MACD oscillator > 0
        close = ohlcv["close"]
        macd = EMA(close, 12) - EMA(close, 26)
        signal = EMA(macd, 9)
        osc = macd - signal
        cond3 = osc.iloc[-1] > 0

        # 모든 조건 충족
        if cond1 and cond2 and cond3:
            close_price = int(ohlcv["close"].iloc[-1])
            selected.append(f"{code} {name} {close_price}")

    # TXT 파일 저장
    with open("selected.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(selected))

    print("조건에 맞는 종목이 selected.txt에 저장되었습니다.")