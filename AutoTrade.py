import pyupbit

import requests
import datetime
import time
import yaml
import schedule
from prophet import Prophet

with open('config.yaml', encoding='UTF-8') as f:
    """설정 파일 읽기"""
    _cfg = yaml.load(f, Loader=yaml.FullLoader)
UPBIT_ACCESS = _cfg['UPBIT_ACCESS']
UPBIT_SECRET = _cfg['UPBIT_SECRET']
DISCORD_WEBHOOK_URL = _cfg['DISCORD_WEBHOOK_URL']

def post_message(msg):
    """디스코드 메세지 전송"""
    now = datetime.datetime.now()
    message = {"content": f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {str(msg)}"}
    requests.post(DISCORD_WEBHOOK_URL, data=message)
    print(message)

def get_target_price(ticker, k):
    """변동성 돌파 전략으로 매수 목표가 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=2)
    target_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * k
    return target_price

def get_start_time(ticker):
    """시작 시간 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=1)
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
    return pyupbit.get_orderbook(ticker=ticker)["orderbook_units"][0]["ask_price"]

predicted_close_price = 0
def predict_price(ticker):
    """Prophet으로 당일 종가 가격 예측"""
    global predicted_close_price
    df = pyupbit.get_ohlcv(ticker, interval="minute60")
    df = df.reset_index()
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
    predicted_close_price = closeValue
predict_price("KRW-BTC")
schedule.every().hour.do(lambda: predict_price("KRW-BTC"))

# 로그인
upbit = pyupbit.Upbit(UPBIT_ACCESS, UPBIT_SECRET)
# 시작 메세지 슬랙 전송
post_message("autotrade start")

while True:
    try:
        now = datetime.datetime.now()
        start_time = get_start_time("KRW-BTC")
        end_time = start_time + datetime.timedelta(days=1)

        if start_time < now < end_time - datetime.timedelta(seconds=10):
            target_price = get_target_price("KRW-BTC", 0.5)
            ma3_price = get_ma("KRW-BTC", 3)
            ma5_price = get_ma("KRW-BTC", 5)
            current_price = get_current_price("KRW-BTC")
            if target_price < current_price \
                and ma3_price < current_price \
                and ma5_price < current_price \
                and current_price < predicted_close_price:
                krw = get_balance("KRW")
                if krw > 5000:
                    buy_result = upbit.buy_market_order("KRW-BTC", krw*0.9995)
                    post_message("BTC buy : " +str(buy_result))
        else:
            btc = get_balance("BTC")
            if btc > 0.00008:
                sell_result = upbit.sell_market_order("KRW-BTC", btc*0.9995)
                post_message("BTC buy : " +str(sell_result))
        time.sleep(1)
    except Exception as e:
        print(e)
        post_message(e)
        time.sleep(1)