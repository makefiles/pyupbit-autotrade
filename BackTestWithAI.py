import pyupbit, yaml, time
import numpy as np
from prophet import Prophet

### 매개변수 ###
TICKER="KRW-BTC"
DAYS=160
CASH=1000000

# 초기화
with open('config.yaml', encoding='UTF-8') as f:
    """설정 파일 읽기"""
    _cfg = yaml.load(f, Loader=yaml.FullLoader)
upbit = pyupbit.Upbit(_cfg['UPBIT_ACCESS'], _cfg['UPBIT_SECRET'])
hourly_data = pyupbit.get_ohlcv(TICKER, interval="minute60", count= DAYS * 24 + 15 * 24).reset_index() # 시봉 데이터
daily_data = pyupbit.get_ohlcv(TICKER, count=DAYS).reset_index() # 일봉 데이터
fee = 0.002 + 0.001 # 슬리피지 + 업비트 매도/매수 수수료 (0.05% * 2)
buy_signal = False # 매수 신호
start_cash = CASH # 시작 자산
current_cash = CASH # 현재 자산
highest_cash = CASH # 자산 최고점
lowest_cash = CASH # 자산 최저점
ror = 1 # 수익률
accumulated_ror = 1 # 누적 수익률
mdd = 0 # 최대 낙폭
trade_count = 0 # 거래횟수
win_count = 0 # 승리횟수

# 결과 출력
def result():
    print('='*40)
    print('테스트 결과')
    print('-'*40)
    print('총 거래 횟수 : %s' % trade_count)
    print('승리 횟수 : %s' % win_count)
    print('승률 : %s' % (win_count / trade_count * 100))
    print('누적 수익률 : %s' % accumulated_ror)
    print('현재 잔액 : %s' % current_cash)
    print('최고 잔액 : %s' % highest_cash)
    print('최저 잔액 : %s' % lowest_cash)
    print('최대 낙폭 (MDD) : %s' % mdd)
    print('='*40)

# 시계열 예측
def predict_price(date):
    df = hourly_data
    df = df[df['index'] <= date].iloc[-(15 * 24):] # date 이전 15일 시봉
    df['ds'] = df['index']
    df['y'] = df['close']
    data = df[['ds','y']]
    model = Prophet()
    model.fit(data)
    future = model.make_future_dataframe(periods=24, freq='H')
    forecast = model.predict(future)
    closeDf = forecast[forecast['ds'] == forecast.iloc[-1]['ds'].replace(hour=9)]
    if len(closeDf) == 0:
        closeDf = forecast[forecast['ds'] == data.iloc[-1]['ds'].replace(hour=9)]
    closeValue = closeDf['yhat'].values[0]
    return closeValue

# 목표 매수가
daily_data['range'] = daily_data['high'] - daily_data['low']
daily_data['target'] = daily_data['open'] + daily_data['range'].shift(1) * 0.5
daily_data['predict'] = daily_data['index'].apply(predict_price)        
daily_data['ma5'] = daily_data['open'].rolling(5).mean()
daily_data['ma10'] = daily_data['open'].rolling(10).mean()
daily_data = daily_data.dropna()

for idx, row in daily_data.iterrows():
    # 매수 신호 확인 (목표가에 달성한 경우 목표가에 매수해 다음날 시가에 매도한 것으로 판단)
    buy_signal = np.where(row['low'] <= row['target'] <= row['high'] and row['target'] <= row['predict'], True, False)
    #buy_signal = np.where(row['low'] <= row['target'] <= row['high'] and row['ma5'] < row['target'] and row['ma10'] < row['target'] , True, False)

    # 수익률 계산 (다음날 시가와 당일 종가의 시간차이가 거의 없으므로 종가로 계산)
    ror = row['close'] / row['target'] - fee if buy_signal else 1
    trade_count += 1 if buy_signal else 0 # 거래횟수 계산
    win_count += 1 if ror > 1 else 0 # 승리 횟수 계산
    accumulated_ror *= ror # 누적 수익률 계산
    current_cash *= ror # 현재 자산 갱신
    highest_cash = max(highest_cash, current_cash) # 자산 최고점 갱신
    lowest_cash = min(lowest_cash, current_cash) # 자산 최저점 갱신
    dd = (highest_cash - current_cash) / highest_cash * 100 # 최대 낙폭 계산
    mdd = max(mdd, dd)

print(daily_data)
result()