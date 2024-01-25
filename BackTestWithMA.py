import numpy as np
import pyupbit
import yaml

with open('config.yaml', encoding='UTF-8') as f:
    """설정 파일 읽기"""
    _cfg = yaml.load(f, Loader=yaml.FullLoader)
upbit = pyupbit.Upbit(_cfg['UPBIT_ACCESS'], _cfg['UPBIT_SECRET'])

class BackTestWithMA:
    def __init__(self, ticker="KRW-BTC", days=160, start_cash=1000000, K=0.5):
        self.daily_data = pyupbit.get_ohlcv(ticker, count=days).reset_index()  # 일봉 데이터
        self.fee = 0.002 + 0.001  # 슬리피지 + 업비트 매도/매수 수수료 (0.05% * 2)
        self.buy_signal = False  # 매수 신호
        self.start_cash = start_cash  # 시작 자산
        self.current_cash = start_cash  # 현재 자산
        self.highest_cash = start_cash  # 자산 최고점
        self.lowest_cash = start_cash  # 자산 최저점
        self.ror = 1  # 수익률
        self.accumulated_ror = 1  # 누적 수익률
        self.mdd = 0  # 최대 낙폭
        self.trade_count = 0  # 거래횟수
        self.win_count = 0  # 승리횟수
        self.K = K #

    def execute(self):
        # 변동성 돌파 전략
        self.daily_data['range'] = (self.daily_data['high'] - self.daily_data['low']).shift(1)
        self.daily_data['target_price'] = self.daily_data['open'] + self.daily_data['range'] * 0.5

        # 이동 평균선 교차 전략
        self.daily_data['ma5'] = self.daily_data['close'].rolling(5).mean()
        self.daily_data['ma10'] = self.daily_data['close'].rolling(10).mean()
        self.daily_data = self.daily_data.dropna()

        print(self.daily_data)

        for idx, row in self.daily_data.iterrows():
            # 매수 신호 확인 (목표가에 달성한 경우 목표가에 매수해 다음날 시가에 매도한 것으로 판단)
            self.buy_signal = np.where(row['low'] < row['target_price'] < row['high'] and row['ma10'] < row['ma5'], True, False)

            # 수익률 계산 (다음날 시가와 당일 종가의 시간차이가 거의 없으므로 종가로 계산)
            self.ror = row['close'] / row['target_price'] - self.fee if self.buy_signal else 1
            self.trade_count += 1 if self.buy_signal else 0  # 거래횟수 계산
            self.win_count += 1 if self.ror > 1 else 0  # 승리 횟수 계산
            self.accumulated_ror *= self.ror  # 누적 수익률 계산
            self.current_cash *= self.ror  # 현재 자산 갱신
            self.highest_cash = max(self.highest_cash, self.current_cash)  # 자산 최고점 갱신
            self.lowest_cash = min(self.lowest_cash, self.current_cash)  # 자산 최저점 갱신
            dd = (self.highest_cash - self.current_cash) / self.highest_cash * 100  # 최대 낙폭 계산
            self.mdd = max(self.mdd, dd)

        self.result()

    def result(self):
        print('=' * 40)
        print('MA 테스트 결과')
        print('-' * 40)
        print('총 거래 횟수 : %s' % self.trade_count)
        print('승리 횟수 : %s' % self.win_count)
        print('승률 : %s' % (self.win_count / self.trade_count * 100))
        print('누적 수익률 : %s' % self.accumulated_ror)
        print('현재 잔액 : %s' % self.current_cash)
        print('최고 잔액 : %s' % self.highest_cash)
        print('최저 잔액 : %s' % self.lowest_cash)
        print('최대 낙폭 (MDD) : %s' % self.mdd)
        print('=' * 40)

BackTestWithMA("KRW-BTC", 160, 1000000).execute()
