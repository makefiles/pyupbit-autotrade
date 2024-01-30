from prophet import Prophet
import TradeApi

trader = TradeApi.get_api("UPBIT", "BTC", "KRW")

# 15일 분량 시봉 데이터 #
df = trader.get_ohlcv_hours(15 * 24)
df = df.reset_index()
df['ds'] = df['index']
df['y'] = df['close']
data = df[['ds', 'y']]
model = Prophet()
model.fit(data)
future = model.make_future_dataframe(periods=24, freq='H')
forecast = model.predict(future)
closeDf = forecast[forecast['ds'] == forecast.iloc[-1]['ds'].replace(hour=9)]
if len(closeDf) == 0:
    closeDf = forecast[forecast['ds'] == data.iloc[-1]['ds'].replace(hour=9)]
closeValue = closeDf['yhat'].values[0]

print(closeValue)
fig = model.plot(forecast)
fig.show()
# fig_com = model.plot_components(forecast)
# fig_com.show()

import pybithumb
price_df = pybithumb.get_candlestick("BTC",  chart_intervals="24h")
print(len(price_df))