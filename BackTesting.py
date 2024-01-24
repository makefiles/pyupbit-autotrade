import pyupbit
import numpy as np
import yaml
from prophet import Prophet

with open('config.yaml', encoding='UTF-8') as f:
    """설정 파일 읽기"""
    _cfg = yaml.load(f, Loader=yaml.FullLoader)
upbit = pyupbit.Upbit(_cfg['UPBIT_ACCESS'], _cfg['UPBIT_SECRET'])

class BackTesting:
    def __init__(self, daily_data, start_cash):
        self.daily_data = daily_data # 일봉 데이터
        self.fee = 0.002 + 0.001 # 슬리피지 + 업비트 매도/매수 수수료 (0.05% * 2)
        self.buy_signal = False # 매수 신호

        self.start_cash = start_cash # 시작 자산
        self.current_cash = start_cash # 현재 자산
        self.highest_cash = start_cash # 자산 최고점
        self.lowest_cash = start_cash # 자산 최저점

        self.ror = 1 # 수익률
        self.accumulated_ror = 1 # 누적 수익률
        self.mdd = 0 # 최대 낙폭

        self.trade_count = 0 # 거래횟수
        self.win_count = 0 # 승리횟수

    def execute(self):
        # 목표 매수가
        self.daily_data['range'] = self.daily_data['high'] - self.daily_data['low']
        self.daily_data['target'] = self.daily_data['open'] + self.daily_data['range'].shift(1) * 0.4
        # self.daily_data['ma5'] = self.daily_data['open'].rolling(5).mean()
        # self.daily_data['ma10'] = self.daily_data['open'].rolling(10).mean()
        # self.daily_data = self.daily_data.dropna()
        print(self.daily_data)

        for idx, row in df.iterrows():
            # 매수 신호 확인
            # 목표가에 달성한 경우 목표가에 매수해 다음날 시가에 매도한 것으로 판단
            self.buy_signal = np.where(row['low'] <= row['target'] <= row['high'], True, False)

            # 거래횟수 계산
            self.trade_count += 1 if self.buy_signal else 0

            # 수익률 계산
            # 다음날 시가와 당일 종가의 시간차이가 거의 없으므로 종가로 계산
            self.ror = row['close'] / row['target'] - self.fee if self.buy_signal else 1

            # 승리 횟수 계산
            self.win_count += 1 if self.ror > 1 else 0

            # 누적 수익률 계산
            self.accumulated_ror *= self.ror

            # 현재 자산 갱신
            self.current_cash *= self.ror

            # 자산 최고점 갱신
            self.highest_cash = max(self.highest_cash, self.current_cash)

            # 자산 최저점 갱신
            self.lowest_cash = min(self.lowest_cash, self.current_cash)

            # 최대 낙폭 계산
            dd = (self.highest_cash - self.current_cash) / self.highest_cash * 100
            self.mdd = max(self.mdd, dd)

        self.result()

    def result(self) :
        print('='*40)
        print('테스트 결과')
        print('-'*40)
        print('총 거래 횟수 : %s' %self.trade_count)
        print('승리 횟수 : %s' %self.win_count)
        print('승률 : %s' %(self.win_count / self.trade_count * 100))
        print('누적 수익률 : %s' %self.accumulated_ror)
        print('현재 잔액 : %s' % self.current_cash)
        print('최고 잔액 : %s' % self.highest_cash)
        print('최저 잔액 : %s' % self.lowest_cash)
        print('최대 낙폭 (MDD) : %s' % self.mdd)
        print('='*40)

df = pyupbit.get_ohlcv("KRW-BTC", count=160) # 일봉 데이터
backtest = BackTesting(df, 1000000)
backtest.execute()