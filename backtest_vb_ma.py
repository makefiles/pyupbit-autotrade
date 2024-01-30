import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import TradeApi

class BackTestVbMa:
    def __init__(self, config):
        # 인증된 객체 가져오기
        trader = TradeApi.get_api("UPBIT", config["COIN"], "KRW")
        
        # 일봉 데이터
        self.df = trader.get_ohlcv_days(config["DAYS"]).reset_index(names='datetime')

        # 슬리피지 + 업비트 매도/매수 수수료 (0.05% * 2)
        self.fee = config["SLIPPAGE"] + config["COMMISSION"]

        # 시작 금액
        self.start_cash = config["CASH"]

        # 변동성 비율
        self.k = config["K"]

    def test(self):
        """ 변동성 돌파 전략 + 이동평균선 교차 전략 """
        df = self.df

        # 변동성 돌파 전략 (Volatility Breakout)
        df['range'] = (df['high'] - df['low']).shift(1)
        df['target_price'] = df['open'] + df['range'] * self.k

        # 이동 평균선 교차 전략 (Moving average crossover)
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()

        # N/A 행 제거
        df = df.dropna().reset_index(drop=True, names='datetime')

        # 매수 신호 (목표 금액에 달성한 경우 목표 금액에 매수해 다음날 시가에 매도한 것으로 판단)
        df['buy'] = np.where((df['low'] < df['target_price']) \
                             & (df['target_price'] < df['high']) \
                             & (df['ma20'] < df['ma10']), 1, 0)
        df['sell'] = np.where(df['buy'].shift(1) == 1, 1, 0)

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
        
        # print(df.to_string())
        # 결과 출력
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

        # 그래프 출력
        self.show(df)
        
    def test2(self) :
        """ 변동성 돌파 전략 + 익일 매매 + 이동평균선 교차 전략 """
        # TODO: 매수/매도일 비교가 필요함
        df = self.df

        # 변동성 돌파 전략 (Volatility Breakout)
        df['range'] = (df['high'] - df['low']).shift(1)
        df['target_price'] = df['open'] + df['range'] * self.k

        # 이동 평균선 교차 전략 (Moving average crossover)
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        
        df['buy'] = 0
        df['sell'] = 0

        # N/A 행 제거
        df = df.dropna().reset_index(drop=True, names='datetime')
        
        before_target_price = 0
        buy_signal = False # 매수 신호
        current_cash = self.start_cash # 현재 자산
        highest_cash = self.start_cash # 자산 최고점
        lowest_cash = self.start_cash # 자산 최저점
        ror = 1 # 수익률
        hpr = 1 # 누적 수익률
        mdd = 0 # 최대 낙폭
        trade_count = 0 # 거래횟수
        win_count = 0 # 승리횟수
        
        for idx, row in df.iterrows() :
            # 매수 신호 확인
            buy_signal = np.where(row['low'] <= row['target_price'] <= row['high'], True, False)
            
            # 매수 표시
            df.loc[idx, 'buy'] = 1 if buy_signal and before_target_price == 0 else 0

            # 전일 매수 가격 기록
            if buy_signal:
                if before_target_price == 0:
                    trade_count += 1 # 거래 횟수 계산
                    before_target_price = row['target_price']
                continue
            
            # 매도 표시
            df.loc[idx, 'sell'] = 1 if before_target_price > 0 else 0

            # 수익률 계산
            ror = row['open'] / before_target_price - self.fee if before_target_price > 0 else 1                

            # 승리 횟수 계산
            win_count += 1 if ror > 1 else 0

            # 누적 수익률 계산
            hpr *= ror
            
            # 현재 자산 갱신
            current_cash *= ror

            # 자산 최고점 갱신
            highest_cash = max(highest_cash, current_cash)

            # 자산 최저점 갱신
            lowest_cash = min(lowest_cash, current_cash)

            # 최대 낙폭 계산
            mdd = max(mdd, (highest_cash - current_cash) / highest_cash * 100)
            
            # 이전 구매 가격 초기화
            before_target_price = 0

        # print(df.to_string())
        # 결과 출력
        print('=' * 40)
        print('변동성 돌파 + 익일 매매 + 이동 평균선 교차 = 테스트 결과')
        print('-' * 40)
        print('총 거래 횟수 : %s' % trade_count)
        print('승리 횟수 : %s' % win_count)
        print('승률 : %s' % (win_count / trade_count * 100 if trade_count > 0 else 0))
        print('누적 수익률 : %s' % hpr)
        print('현재 잔액 : %s' % current_cash)
        print('최고 잔액 : %s' % highest_cash)
        print('최저 잔액 : %s' % lowest_cash)
        print('최대 낙폭 (MDD) : %s' % mdd)
        print('=' * 40)
        
        # 그래프 출력
        self.show(df)
        
    def show(self, df):
        """ 그래프 표시 """
        # plot setting
        plt.figure(figsize = (20, 10))
        sns.set_style('whitegrid')

        # get data
        if df['buy'].sum() == 0: return
        coin_y = df['open'].values
        buy_x = df[df['buy']==1].index.values
        sell_x = df[df['sell']==1].index.values
        buy_x = buy_x[:(len(sell_x))]
        if coin_y.shape[0] == sell_x[-1]:
            buy_x = buy_x[:-1]
            sell_x = sell_x[:-1]

        # plot data
        plt.plot(coin_y, c = 'gray', label='coin price', linewidth=1.2)
        plt.scatter(buy_x, coin_y[buy_x], c='lime', s=15, label='buy/sell point')
        plt.scatter(sell_x, coin_y[sell_x], c='lime', s=15)
        for idx in range(0, len(buy_x)):
            rec_xs = [buy_x[idx], sell_x[idx]]
            rec_ys = [coin_y[buy_x[idx]], coin_y[sell_x[idx]]]
            if rec_ys[0] < rec_ys[1]:
                rec_color = 'blue'
            else:
                rec_ys[0], rec_ys[1] = rec_ys[1], rec_ys[0]
                rec_color = 'red'
            plt.gca().add_patch(patches.Rectangle((rec_xs[0], rec_ys[0]), 
                                                rec_xs[1]-rec_xs[0], 
                                                rec_ys[1]-rec_ys[0],
                                                alpha = 0.4,
                                                color = rec_color))
        # legend
        plt.gca().add_patch(patches.Rectangle((0, 0), 0, 0, color = 'blue', label = 'benefit'))
        plt.gca().add_patch(patches.Rectangle((0, 0), 0, 0, color = 'red', label = 'loss'))
        plt.legend()

        # plot setting
        plt.ylim(min(coin_y)*0.95, max(coin_y)*1.05)
        plt.xticks(list(range(0, len(df), 1)), labels = df['datetime'][list(range(0, len(df), 1))], rotation = 45)
        plt.show()


BackTestVbMa({
    "COIN": "BTC",
    "DAYS": 100,
    "CASH": 1000000,
    "SLIPPAGE": 0.002,
    "COMMISSION": 0.001,
    "K": 0.3
}).test()
