import pyupbit
import yaml
import requests
import datetime
import schedule
from prophet import Prophet

def get_api(trader, ticker):
    
    if trader.lower() == "upbit":
        api = UpbitTrader(ticker)
    
    return api

class TradeApi:
    def __init__(self, trader, ticker):
        self.trader = trader
        self.ticker = ticker
        self.predicted_close_price = 0
        with open('config.yaml', encoding='UTF-8') as f:
            _cfg = yaml.load(f, Loader=yaml.FullLoader)
        self.discord_webhook_url = _cfg['DISCORD_WEBHOOK_URL']

    def get_public(self):
        None
    
    def get_private(self):
        None

    def get_target_price(self, k):
        None
    
    def get_start_time(self):
        None
    
    def get_ma(self, days):
        None
    
    def get_balance(self, ticker):
        None
    
    def get_current_price(self):
        None
    
    def buy_ticker(self, krw):
        None
    
    def sell_ticker(self, btc):
        None
    
    def message(self, msg):
        """디스코드 메세지 전송"""
        now = datetime.datetime.now()
        message = {"content": f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {str(msg)}"}
        requests.post(self.discord_webhook_url, data=message)
        print(message)
    
    def predict_price(self, df = None, study_days = 20):
        None
    
    def get_predict_price(self):
        return self.predicted_close_price
    
    def set_predict_price(self, df):
        """ Prophet으로 당일 종가 가격 예측 """
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
        return "Used %s API (%s)" % (self.trader, self.ticker)

class UpbitTrader(TradeApi):
    def __init__(self, ticker):
        """ 초기화 & 거래 종목 선택 """
        super().__init__("UPBIT", ticker)
        with open('config.yaml', encoding='UTF-8') as f:
            _cfg = yaml.load(f, Loader=yaml.FullLoader)
        self.upbit = pyupbit.Upbit(_cfg['API_ACCESS'], _cfg['API_SECRET'])
        self.commission = 0.05
        self.min_krw = 5000
        self.min_btc = 0.0005
        
        # 시계열 예측
        self.predict_price(study_days = 20)
        #schedule.every().hour.do(lambda: self.predict_price(study_days = 20))
        
    def get_public(self):
        """ 공개 API 객체 """
        return pyupbit
    
    def get_target_price(self, k):
        """ 변동성 돌파 전략으로 매수 목표가 조회 """
        df = pyupbit.get_ohlcv(super().ticker, interval="day", count=2)
        return df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * k
    
    def get_start_time(self):
        """ 시작 시간 조회 """
        df = pyupbit.get_ohlcv(super().ticker, interval="day", count=1)
        return df.index[0]

    def get_ma(self, days):
        """ n일 이동 평균선 조회 """
        df = pyupbit.get_ohlcv(super().ticker, interval="day", count=days)
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
        return pyupbit.get_orderbook(ticker = super().ticker)["orderbook_units"][0]["ask_price"]

    def buy_ticker(self, krw):
        """ 매수 """
        if krw > self.min_krw: # 거래 최소 금액
            return self.upbit.buy_market_order(super().ticker, krw * (1 - self.commission / 100)) # 커미션이 0.05 라면 0.9995 를 뺌
        return None

    def sell_ticker(self, btc):
        """ 매도 """
        if btc > self.min_btc: # 거래 최소 코인
            return self.upbit.sell_market_order(super().ticker, btc * (1 - self.commission / 100)) # 커미션이 0.05 라면 0.9995 를 뺌
        return None
    
    def predict_price(self, df = None, study_days = 20):
        """ 시계열 예측 """
        if df is None:
            df = pyupbit.get_ohlcv(self.ticker, interval = "minute60", count = study_days * 24)
            print(df)
            df = df.reset_index(names='datetime')
        return super().set_predict_price(df)

get_api("UPBIT", "BTC")