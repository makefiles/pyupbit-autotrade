import datetime
import time
import schedule
from prophet import Prophet
import TradeApi

COIN = "BTC"
CURRENCY = "KRW"

# API 객체 생성
trader = TradeApi.get_api("UPBIT", COIN, CURRENCY)

# 가격 예측 스케쥴링
trader.get_predicted_price(None, 20)
schedule.every().hour.do(lambda: trader.get_predicted_price(None, 20))

# 시작 메세지 슬랙 전송
trader.message("AutoTrade start")

'''
TODO:
    1. 매도시 수수료 계산 이상함 (완료) --> 매수에만 계산함
    2. 변동성 돌파 + 익일 매매 + 시계열 예측 구현
    3. 전액 매수 후 더이상 구매 처리가 필요 없으므로 루프 대기 기능
    4. 1시간 단위로 현재 가격 정보 보여주기
'''
while True:
    time.sleep(1)
    try:
        schedule.run_pending()
        now = datetime.datetime.now()
        start_time = trader.get_start_time()
        end_time = start_time + datetime.timedelta(days=1)
        if start_time < now < end_time - datetime.timedelta(seconds=10):
            target_price = trader.get_target_price()
            current_price = trader.get_current_price()
            predicted_close_price = trader.get_predicted_price()
            if target_price < current_price < predicted_close_price:
                trader.buy_coin(trader.get_balance(CURRENCY))
        else:
            trader.sell_coin(trader.get_balance(COIN))
    except Exception as e:
        trader.message(e)
