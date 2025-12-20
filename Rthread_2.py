import requests
from PyQt5.QtCore import QThread, pyqtSignal

class Thread2(QThread):
    data_ready = pyqtSignal(list)

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url
    def run(self):
        try:
            resp = requests.get(self.url)
            resp.raise_for_status()
            lines = resp.text.strip().split("\n")

            table_data = []
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 3:
                    code = parts[0]
                    name = " ".join(parts[1:-1])
                    last_close = parts[-1]
                    table_data.append([code, name, last_close])
                print(code, name, last_close)
            self.data_ready.emit(table_data)

            #column_head = ["종목번호", "종목명", "보유수량", "매입가", "현재가", "평가손익", "수익률(%)"]
            #colCount = len(column_head)
            #rowCount = self.k.kiwoom.dynamicCall("GetRepeatCnt(QString, QString)", sTrCode, sRQName)
            #self.parent.redstockTableWidget_1.setColumnCount(colCount)                           # 행 갯수
            #self.parent.redstockTableWidget_1.setRowCount(rowCount)                               # 열 갯수 (종목 수)
            #self.parent.redstockTableWidget_1.setHorizontalHeaderLabels(column_head)              # 행의 이름 삽입

        except Exception as e:
            print("Thread2 Error:", e)
            self.data_ready.emit([])

