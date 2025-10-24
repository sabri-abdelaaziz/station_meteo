import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from .models import WeatherMetric
from datetime import timedelta

def forecast_metric_arima(metric_name, steps=24):
    """
    Forecast next 'steps' hours/days for a given metric using ARIMA.
    """
    # Load historical data
    data = WeatherMetric.objects.all().order_by('timestamp').values('timestamp', metric_name)
    df = pd.DataFrame(data)
    if df.empty:
        return []

    df.set_index('timestamp', inplace=True)
    ts = df[metric_name].astype(float)

    # Fit ARIMA model (simple: order can be tuned)
    try:
        model = ARIMA(ts, order=(5,1,0))  # (p,d,q) can be adjusted
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=steps)
    except Exception as e:
        print("ARIMA error:", e)
        return []

    # Prepare output as list of dicts with timestamps
    last_time = ts.index[-1]
    forecast_data = []
    for i, value in enumerate(forecast):
        forecast_data.append({
            "ds": (last_time + timedelta(hours=i+1)).strftime("%Y-%m-%d %H:%M:%S"),
            "yhat": round(value, 2)
        })

    return forecast_data
from datetime import timedelta


def forecast_metric(metric_values, steps=24):
    # Make sure metric_values is a numeric list
    metric_values = [float(x) for x in metric_values if x is not None]

    if len(metric_values) < 10:  # ARIMA needs more points
        return [metric_values[-1]] * steps

    model = ARIMA(metric_values, order=(5,1,0))  # tune order if needed
    model_fit = model.fit()
    forecast = model_fit.forecast(steps=steps)
    return forecast.tolist()


def generate_forecast():
    # Load historical data
    metrics = WeatherMetric.objects.order_by('-timestamp')[:100]  # last 100 records
    df = pd.DataFrame(list(metrics.values('timestamp', 'temperature', 'rainfall', 'uv_index')))
    df.set_index('timestamp', inplace=True)

    forecast = {}

    # Forecast function for each metric
    def forecast_arima(series, steps=1):
        series = series.dropna()
        if len(series) < 10:  # too few points
            return [series.iloc[-1]] * steps
        model = ARIMA(series, order=(1,1,1))
        model_fit = model.fit()
        pred = model_fit.forecast(steps=steps)
        return pred.tolist()

    forecast['temperature'] = forecast_arima(df['temperature'], steps=5)
    forecast['rainfall'] = forecast_arima(df['rainfall'], steps=5)
    forecast['uv_index'] = forecast_arima(df['uv_index'], steps=5)

    return forecast