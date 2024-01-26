from prophet import Prophet
import numpy as np
import pyupbit
import yaml
import logging

logging.getLogger("prophet").setLevel(logging.WARNING)
logging.getLogger("cmdstanpy").disabled = True

# 설정 읽기
with open('config.yaml', encoding='UTF-8') as f:
    """설정 파일 읽기"""
    _cfg = yaml.load(f, Loader=yaml.FullLoader)
upbit = pyupbit.Upbit(_cfg['UPBIT_ACCESS'], _cfg['UPBIT_SECRET'])


class BackTestVbProphet:
    def __init__(self, config):
        # 결과 데이터
        self.result_df = None

        # 테스트 일수
        self.test_days = config["TEST_DAYS"]

        # 학습 시간
        self.study_time = config["STUDY_DAYS"] * 24

        # 일봉 데이터
        self.daily_df = pyupbit.get_ohlcv(config["TICKER"], count=config["TEST_DAYS"]).reset_index()

        # 시봉 데이터
        self.hourly_df = (pyupbit.get_ohlcv(config["TICKER"], interval="minute60",
                                            count=self.test_days * 24 + self.study_time).reset_index())

        # 슬리피지 + 업비트 매도/매수 수수료 (0.05% * 2)
        self.fee = config["SLIPPAGE"] + config["COMMISSION"]

        # 시작 금액
        self.start_cash = config["CASH"]

        # 변동성 비율
        self.k = config["K"]

    def test(self):
        """ 테스트 """
        df = self.daily_df

        # 변동성 돌파 전략 (Volatility Breakout)
        df['range'] = (df['high'] - df['low']).shift(1)
        df['target_price'] = df['open'] + df['range'] * self.k

        # 15일 데이터 시계열 예측 전략 (Prophet)
        # print(df.to_string())
        df['predict'] = df.apply(lambda row: self.predict_price(row.name, row['index']), axis=1)
        print('\r')

        # 매수 신호 (목표 금액에 달성한 경우 목표 금액에 매수해 다음날 시가에 매도한 것으로 판단)
        df['buy'] = np.where((df['low'] < df['target_price']) \
                             & (df['target_price'] < df['high']) \
                             & (df['target_price'] < df['predict']), 1, 0)

        # 수익률 계산 (다음날 시가와 당일 종가의 시간 차이가 거의 없어 종가로 계산)
        df['ror'] = np.where(df['buy'] == 1,
                             df['close'] / df['target_price'] - self.fee, 1)

        # 누적 수익률 계산
        df['hpr'] = df['ror'].cumprod()

        # 낙폭 계산 (cash 로 계산 가능)
        df['dd'] = (df['hpr'].cummax() - df['hpr']) / df['hpr'].cummax() * 100

        # 현재 자산 기록
        df['cash'] = self.start_cash
        df['cash'] = df['cash'] * df['ror'].cumprod()

        # 승리 횟수 기록
        df['win'] = np.where(df['ror'] > 1, 1, 0)

        # 결과 출력
        self.print(df)

    def print(self, df):
        """ 결과 출력 """
        print('=' * 40)
        print('변동성 돌파 + 시계열 예측 = 테스트 결과')
        print('-' * 40)
        print('총 거래 횟수 : %s' % df['buy'].sum())
        print('승리 횟수 : %s' % df['win'].sum())
        print('승률 : %s' % (df['win'].sum() / df['buy'].sum() * 100 if df['buy'].sum() > 0 else 0))
        print('누적 수익률 : %s' % df.iloc[-1]['hpr'])
        print('현재 잔액 : %s' % df.iloc[-1]['cash'])
        print('최고 잔액 : %s' % df['cash'].max())
        print('최저 잔액 : %s' % df['cash'].min())
        print('최대 낙폭 (MDD) : %s' % df['dd'].max())
        print('=' * 40)

    def progress_bar(self, current, total, width=50):
        """ 프로그레스바 """
        percent = float(current) / float(total)
        bar = "#" * int(percent * width)
        empty = " " * (width - len(bar))
        print("\rProgress: [{0}] {1}/{2} ({3:.0f}%)".format(bar + empty, current, total, percent * 100), end="")

    def predict_price(self, index, date):
        """ Prophet 시계열 예측 가격 """
        df = self.hourly_df
        df = df[df['index'] <= date].iloc[-self.study_time:]  # date 이전 15일 시봉
        data_df = df[['index', 'close']].rename(columns={'index': 'ds', 'close': 'y'})
        model = Prophet()
        model.fit(data_df)
        future = model.make_future_dataframe(periods=24, freq='H')
        forecast = model.predict(future)
        close_df = forecast[forecast['ds'] == forecast.iloc[-1]['ds'].replace(hour=9)]
        if len(close_df) == 0:
            close_df = forecast[forecast['ds'] == data_df.iloc[-1]['ds'].replace(hour=9)]
        close_value = close_df['yhat'].values[0]
        self.progress_bar(index + 1, self.test_days)
        return close_value

BackTestVbProphet({
    "TICKER": "KRW-BTC",
    "TEST_DAYS": 160,
    "STUDY_DAYS": 15,
    "CASH": 1000000,
    "SLIPPAGE": 0.002,
    "COMMISSION": 0.001,
    "K": 0.5
}).test()