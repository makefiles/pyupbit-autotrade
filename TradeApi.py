import pyupbit
import pybithumb
import yaml
import requests
import datetime
import time
import math
from prophet import Prophet
import logging
logging.getLogger("prophet").setLevel(logging.WARNING)
logging.getLogger("cmdstanpy").disabled = True

def get_api(trader, coin, currency):
    
    if trader.lower() == "upbit":
        api = UpbitTrader(coin, currency)
    
    return api

# TODO: Python 공부를 위해 클래스를 만들었으나 좀 복잡해 짐
class TradeApi:
    def __init__(self, trader, coin, currency):
        self.trader = trader
        self.coin = coin
        self.currency = currency
        self.predicted_close_price = 0
        with open('config.yaml', encoding='UTF-8') as f:
            _cfg = yaml.load(f, Loader=yaml.FullLoader)
        self.discord_webhook_url = _cfg['DISCORD_WEBHOOK_URL']

    def get_ohlcv_days(self, count):
        pass

    def get_ohlcv_hours(self, count):
        pass

    def get_target_price(self):
        pass
    
    def get_start_time(self):
        pass
    
    def get_ma(self, days):
        pass
    
    def get_balance(self, ticker):
        pass
    
    def get_current_price(self):
        pass
    
    def buy_coin(self, krw):
        pass
    
    def sell_coin(self, btc):
        pass
    
    def message(self, msg):
        """디스코드 메세지 전송"""
        now = datetime.datetime.now()
        message = {"content": f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {str(msg)}"}
        requests.post(self.discord_webhook_url, data=message)
        print(message)
    
    def get_predicted_price(self):
        """ 예측된 가격 가져오기 """
        return self.predicted_close_price
    
    def get_predicted_price(self, df = None, study_days = 20):
        """ 가격 예측 전처리 (상속 구현) """
        pass
    
    def get_predicted_price(self, df):
        """ Prophet 가격 예측 (상속 안함) """
        data_df = df[['datetime', 'close']].rename(columns={'datetime': 'ds', 'close': 'y'})
        model = Prophet()
        model.fit(data_df)
        future = model.make_future_dataframe(periods=24, freq='H')
        forecast = model.predict(future)
        close_df = forecast[forecast['ds'] == forecast.iloc[-1]['ds'].replace(hour=9)]
        if len(close_df) == 0:
            close_df = forecast[forecast['ds'] == data_df.iloc[-1]['ds'].replace(hour=9)]
        self.predicted_close_price = close_df['yhat'].values[0]
        return self.predicted_close_price
    
    def __str__(self):
        return "Used %s API (%s, %s)" % (self.trader, self.coin, self.currency)

class UpbitTrader(TradeApi):
    def __init__(self, coin, currency):
        """ 초기화 & 거래 종목 선택 """
        super().__init__("UPBIT", coin, currency)
        with open('config.yaml', encoding='UTF-8') as f:
            _cfg = yaml.load(f, Loader=yaml.FullLoader)
        self.upbit = pyupbit.Upbit(_cfg['API_ACCESS'], _cfg['API_SECRET'])
        self.pyupbit = pyupbit
        self.ticker = self.currency + "-" + self.coin
        
        # 필요 상수 선언
        self.commission = 0.05
        self.k = 0.3
        self.min_krw = 5000
        self.min_btc = 0.0005
    
    def get_ohlcv_days(self, count):
        return pyupbit.get_ohlcv(self.ticker, interval="day", count=count)
    
    def get_ohlcv_hours(self, count):
        return pyupbit.get_ohlcv(self.ticker, interval="minute60", count=count)
    
    def get_target_price(self):
        """ 변동성 돌파 전략으로 매수 목표가 조회 """
        df = self.get_ohlcv_days(2)
        return df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * self.k
    
    def get_start_time(self):
        """ 시작 시간 조회 """
        df = self.get_ohlcv_days(1)
        return df.index[0]

    def get_ma(self, days):
        """ n일 이동 평균선 조회 """
        df = self.get_ohlcv_days(days)
        return df['close'].rolling(days).mean().iloc[-1]

    def get_balance(self, ticker):
        """잔고 조회"""
        balances = self.upbit.get_balances()
        for b in balances:
            if b['currency'] == ticker:
                if b['balance'] is not None:
                    return float(b['balance'])
                else:
                    return 0
        return 0

    def get_current_price(self):
        """ 현재가 조회 """
        return pyupbit.get_orderbook(ticker = self.ticker)["orderbook_units"][0]["ask_price"]

    def buy_coin(self, krw):
        """ 매수 """
        krw = math.floor(krw)
        if krw >= self.min_krw: # 거래 최소 금액
            result = self.upbit.buy_market_order(self.ticker, krw * (1 - self.commission / 100)) # 커미션이 0.05 라면 0.9995 를 뺌
            super().message(self.ticker + " Buy : " + str(result))
            return result
        return None

    def sell_coin(self, btc):
        """ 매도 """
        if btc >= self.min_btc: # 거래 최소 코인
            result = self.upbit.sell_market_order(self.ticker, btc) # 커미션 알아서 빠져나감
            super().message(self.ticker + " Sell : " + str(result))
            return result
        return None
    
    def get_predict_price(self, df = None, study_days = 20):
        """ 시계열 예측 """
        if df is None:
            df = self.get_ohlcv_hours(study_days * 24)
            df = df.reset_index(names='datetime')
        return super().get_predicted_price(df)

 # TODO: 너무 이상하다... 일단 사용하지 않음
class BithumbTrader(TradeApi):
    def __init__(self, coin, currency):
        """ 초기화 & 거래 종목 선택 """
        super().__init__("BITHUMB", coin, currency)
        with open('config.yaml', encoding='UTF-8') as f:
            _cfg = yaml.load(f, Loader=yaml.FullLoader)
        self.bithumb = pybithumb.Bithumb(_cfg['API_ACCESS'], _cfg['API_SECRET'])
        self.pybithumb = pybithumb
        
        # 필요 상수 선언
        self.commission = 0.05
        self.k = 0.3
        self.min_krw = 5000
        self.min_btc = 0.0005
    
    def get_ohlcv_days(self, count):
        df = pybithumb.get_candlestick(self.coin, self.currency, "24h")
        return df.tail(count)
    
    def get_ohlcv_hours(self, count):
        df = pybithumb.get_candlestick(self.coin, self.currency, "1h")
        return df.tail(count)
    
    def get_target_price(self):
        """ 변동성 돌파 전략으로 매수 목표가 조회 """
        df = self.get_ohlcv_days(2)
        return df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * self.k
    
    def get_start_time(self):
        """ 시작 시간 조회 """
        df = self.get_ohlcv_days(1)
        return df.index[0]

    def get_ma(self, days):
        """ n일 이동 평균선 조회 """
        df = self.get_ohlcv_days(days)
        return df['close'].rolling(days).mean().iloc[-1]

    def get_balance(self, ticker):
        """잔고 조회"""
        balance = self.bithumb.get_balance(ticker)
        if balance is not None:
            return balance
        else:
            return 0

    def get_current_price(self):
        """ 현재가 조회 """
        return pybithumb.get_orderbook(self.coin, self.currency)["asks"][0]["price"]

    def buy_coin(self, krw):
        """ 매수 """
        while True:
            try:
                krw = krw[2] - krw[3] # 현금 보유 금액
                krw = krw * (1 - self.commission / 100)
                krw = krw - (krw % 1000) # 천원단위
                if krw < 500:
                    super().message("보유 금액이 너무 작음 :%.2f" % krw)
                    return
                
                while True:
                    sell_price = self.get_current_price()
                    if sell_price > krw:
                        sell_price = krw
                    unit = krw / float(sell_price) # 호가창 첫번째 가격으로 구매 가능 금액을 나눔
                    unit = math.trunc(unit * 10000) / 10000 # 소수점 네자리 이상 버림
                    if unit == 0:
                        super().message("보유 금액이 너무 작음 :%.2f" % krw)
                        return
                    elif unit < 0.001:
                        super().message("unit이 최소 단위보다 작음 :%.4f" % unit)
                        return
                    sell_price = int(sell_price)
                    order = self.bithumb.buy_limit_order(self.coin, sell_price, unit, self.currency)
                    if order is not None and type(order) is tuple:
                        super().message("Buy : " + str(order))
                        return
                    elif order is not None:
                        super().message("Buy one more : " + str(order))
                        if order.get('status') == '5500':
                            krw = krw - 10000 # 만원 빼서 재도전
                            continue
                        elif order.get('status') == '5600':
                            return
                    else:
                        time.sleep(1)
            except Exception as e:
                super().message(e)
                time.sleep(1)

    def sell_coin(self, btc):
        """ 매도 """
        while True:
            try:
                unit = btc[0]
                if unit == 0:
                    super().message("보유 코인(%s) 이 없음" % self.coin)
                    return
                
                order = self.bithumb.sell_market_order(self.coin, unit, self.currency)
                if order is not None:
                    super().message("Sell : " + str(order))
                    return
                else:
                    time.sleep(1)
            except Exception as e:
                super().message(e)
                time.sleep(1)
    
    def get_predict_price(self, df = None, study_days = 20):
        """ 시계열 예측 """
        if df is None:
            df = self.get_ohlcv_hours(study_days * 24)
            df = df.reset_index(names='datetime')
        return super().get_predicted_price(df)

