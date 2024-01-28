import pyupbit
import requests
import datetime
import time
import yaml
import schedule
from prophet import Prophet

# TODO: 변동성 돌파 + 익일 매매 + 시계열 예측 구현

TICKER = "BTC"
KRW_TICKER = "KRW-" + TICKER
COMMISSION = 0.05
STUDY_DAYS = 20
K = 0.3
MIN_KRW = 5000
MIN_BTC = 0.0005

with open('config.yaml', encoding='UTF-8') as f:
    """설정 파일 읽기"""
    _cfg = yaml.load(f, Loader=yaml.FullLoader)
UPBIT_ACCESS = _cfg['UPBIT_ACCESS']
UPBIT_SECRET = _cfg['UPBIT_SECRET']
DISCORD_WEBHOOK_URL = _cfg['DISCORD_WEBHOOK_URL']
upbit = pyupbit.Upbit(UPBIT_ACCESS, UPBIT_SECRET)

def post_message(msg):
    """디스코드 메세지 전송"""
    now = datetime.datetime.now()
    message = {"content": f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {str(msg)}"}
    requests.post(DISCORD_WEBHOOK_URL, data=message)
    print(message)

def get_target_price(ticker, k):
    """변동성 돌파 전략으로 매수 목표가 조회"""
    df = pyupbit.get_ohlcv("KRW-" + ticker, interval="day", count=2)
    target_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * k
    return target_price

def get_start_time(ticker):
    """시작 시간 조회"""
    df = pyupbit.get_ohlcv("KRW-" + ticker, interval="day", count=1)
    start_time = df.index[0]
    return start_time

def get_ma(ticker, days):
    """ n일 이동 평균선 조회 """
    df = pyupbit.get_ohlcv(ticker, interval="day", count=days)
    ma = df['close'].rolling(days).mean().iloc[-1]
    return ma

def get_balance(ticker):
    """잔고 조회"""
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == ticker:
            if b['balance'] is not None:
                return float(b['balance'])
            else:
                return 0
    return 0

def get_current_price(ticker):
    """현재가 조회"""
    return pyupbit.get_orderbook(ticker = ticker)["orderbook_units"][0]["ask_price"]

def buy_coin(ticker, krw):
    if krw > MIN_KRW: # 거래 최소 금액
        result = upbit.buy_market_order(ticker, krw * (1 - COMMISSION / 100)) # 커미션이 0.05 라면 0.9995 를 뺌
        post_message(ticker + " buy : " + str(result))
        return result
    return None

def sell_coin(ticker, btc):
    if btc > MIN_BTC: # 거래 최소 코인
        result = upbit.sell_market_order(ticker, btc * (1 - COMMISSION / 100)) # 커미션이 0.05 라면 0.9995 를 뺌
        post_message(ticker + " sell : " + str(result))
        return result
    return None

predicted_close_price = 0
def predict_price(ticker, days):
    """Prophet으로 당일 종가 가격 예측"""
    global predicted_close_price
    df = pyupbit.get_ohlcv(ticker, interval = "minute60", count = days * 24)
    df = df.reset_index(names='datetime')
    df['ds'] = df['datetime']
    df['y'] = df['close']
    data = df[['ds','y']]
    model = Prophet()
    model.fit(data)
    future = model.make_future_dataframe(periods=24, freq='H')
    forecast = model.predict(future)
    close_df = forecast[forecast['ds'] == forecast.iloc[-1]['ds'].replace(hour=9)]
    if len(close_df) == 0:
        close_df = forecast[forecast['ds'] == data.iloc[-1]['ds'].replace(hour=9)]
    close_value = close_df['yhat'].values[0]
    predicted_close_price = close_value

# 시작 메세지 슬랙 전송
post_message("AutoTrade start")
# 시계열 예측
predict_price(KRW_TICKER, STUDY_DAYS)
schedule.every().hour.do(lambda: predict_price(KRW_TICKER, STUDY_DAYS))
while True:
    try:
        schedule.run_pending()
        now = datetime.datetime.now()
        start_time = get_start_time(KRW_TICKER)
        end_time = start_time + datetime.timedelta(days=1)
        if start_time < now < end_time - datetime.timedelta(seconds=10):
            target_price = get_target_price(KRW_TICKER, K)
            current_price = get_current_price(KRW_TICKER)
            if target_price < current_price < predicted_close_price:
                buy_coin(KRW_TICKER, get_balance("KRW"))
        else:
            sell_coin(KRW_TICKER, get_balance(TICKER))
        time.sleep(1)
    except Exception as e:
        print(e)
        post_message(e)
        time.sleep(1)