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

trader = TradeApi.get_api("UPBIT", "BTC", "KRW")
trader.start_predicting_price()
def start_predicting_price(self):
    """ 예측 스케쥴 시작 """
    self.get_predicted_price(None, 20)
    schedule.every().hour.do(lambda: self.get_predicted_price(None, 20))

# 시작 메세지 슬랙 전송
trader.message("AutoTrade start")

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