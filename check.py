import json
import pandas as pd

def calculate_bollinger_lower1(prices, period=20, stddev=2):
    ma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    lower = ma - (std * stddev)
    return lower

def calculate_bollinger_lower2(prices, period=30, stddev=2):
    ma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    lower = ma - (std * stddev)
    return lower

def check_crossover(bollinger_lower1, bollinger_lower2):
    if len(bollinger_lower1) < 2 or len(bollinger_lower2) < 2:
        return False
    return (
        bollinger_lower1[-2] < bollinger_lower2[-2] and
        bollinger_lower1[-1] > bollinger_lower2[-1]
    )

def find_crossover_stocks(json_path, output_path='selected.json'):
    with open(json_path, 'r', encoding='utf-8') as f:
        stock_data = json.load(f)

    selected_stocks = {}

    for code, stock_info in stock_data.items():
        ohlcv_list = stock_info.get("ohlcv", [])
        if len(ohlcv_list) < 60:
            continue  # 데이터 부족

        df = pd.DataFrame(ohlcv_list)
        df = df.sort_values(by='date')  # 날짜 오름차순 정렬

        if 'close' not in df:
            continue

        df['close'] = df['close'].astype(float)

        bollinger_lower1 = calculate_bollinger_lower1(df['close'])
        bollinger_lower2 = calculate_bollinger_lower2(df['close'])

        if check_crossover(bollinger_lower1.values, bollinger_lower2.values):
            selected_stocks[code] = {
                "name": stock_info.get("name", ""),
                "last_date": df['date'].iloc[-1],
                "last_close": df['close'].iloc[-1]
            }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(selected_stocks, f, ensure_ascii=False, indent=2)

    print(f"조건에 맞는 종목 {len(selected_stocks)}개가 {output_path}에 저장되었습니다.")
    return selected_stocks


if __name__ == '__main__':
    json_file = 'all_stock_data.json'
    find_crossover_stocks(json_file, output_path='selected.json')


