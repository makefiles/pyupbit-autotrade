import pyupbit
from prophet import Prophet

upbit = pyupbit.Upbit('dWmkkEWu7qwTC7iB2V06i3YxTpPIFx5YuBaBHUb3', 'oGsxfUlmyLw9lQpW9wxESloIpScIcNRdzmTa7iuD')

# 15일 분량 시봉 데이터 가져오기 #
df = pyupbit.get_ohlcv("KRW-BTC", interval="minute60", count=360)
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
fig1 = model.plot(forecast)
fig1.show()
fig2 = model.plot_components(forecast)
fig2.show()