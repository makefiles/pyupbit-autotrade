import pyupbit
import requests
import datetime
import time
import yaml
import schedule
from prophet import Prophet
import TradeApi

# TODO: 변동성 돌파 + 익일 매매 + 시계열 예측 구현

TICKER = "BTC"
KRW_TICKER = "KRW-" + TICKER
COMMISSION = 0.05
STUDY_DAYS = 20
K = 0.3
MIN_KRW = 5000
MIN_BTC = 0.0005

trader = TradeApi.get_api("UPBIT", "KRW-BTC")

# 시작 메세지 슬랙 전송
trader.message("AutoTrade start")

predicted_close_price = 0
def predict_price(ticker, days):
    """Prophet으로 당일 종가 가격 예측"""
    global predicted_close_price
    df = trader.get_public().get_ohlcv(ticker, interval = "minute60", count = days * 24)
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
                buy_result = buy_coin(KRW_TICKER, get_balance("KRW"))
                if buy_result is not None:
                    post_message(KRW_TICKER + " buy : " + str(buy_result))
        else:
            sell_result = sell_coin(KRW_TICKER, get_balance(TICKER))
            if sell_result is not None:
                post_message(KRW_TICKER + " sell : " + str(sell_result))
        time.sleep(1)
    except Exception as e:
        print(e)
        post_message(e)
        time.sleep(1)