import numpy as np
import pyupbit
import yaml

# 설정 읽기
with open('config.yaml', encoding='UTF-8') as f:
    """설정 파일 읽기"""
    _cfg = yaml.load(f, Loader=yaml.FullLoader)
upbit = pyupbit.Upbit(_cfg['UPBIT_ACCESS'], _cfg['UPBIT_SECRET'])


class BackTestVbMa:
    def __init__(self, config):
        # 일봉 데이터
        self.df = pyupbit.get_ohlcv(config["TICKER"], count=config["DAYS"]).reset_index()

        # 슬리피지 + 업비트 매도/매수 수수료 (0.05% * 2)
        self.fee = config["SLIPPAGE"] + config["COMMISSION"]

        # 시작 금액
        self.start_cash = config["CASH"]

        # 변동성 비율
        self.k = config["K"]

    def test(self):
        """ 테스트 """
        df = self.df

        # 변동성 돌파 전략 (Volatility Breakout)
        df['range'] = (df['high'] - df['low']).shift(1)
        df['target_price'] = df['open'] + df['range'] * self.k

        # 이동 평균선 교차 전략 (Moving average crossover)
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()

        # N/A 행 제거
        df = df.dropna().reset_index(drop=True)
        # print(df.to_string())

        # 매수 신호 (목표 금액에 달성한 경우 목표 금액에 매수해 다음날 시가에 매도한 것으로 판단)
        df['buy'] = np.where((df['low'] < df['target_price']) \
                             & (df['target_price'] < df['high']) \
                             & (df['ma10'] < df['ma5']), 1, 0)

        # 수익률 계산 (다음날 시가와 당일 종가의 시간 차이가 거의 없어 종가로 계산)
        df['ror'] = np.where(df['buy'] == 1, df['close'] / df['target_price'] - self.fee, 1)

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
        print('변동성 돌파 + 이동 평균선 교차 = 테스트 결과')
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


BackTestVbMa({
    "TICKER": "KRW-BTC",
    "DAYS": 160,
    "CASH": 1000000,
    "SLIPPAGE": 0.002,
    "COMMISSION": 0.001,
    "K": 0.5
}).test()
