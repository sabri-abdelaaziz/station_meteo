from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import WeatherMetric
from .forms import WeatherMetricForm
import requests
import json

# Imports ARIMA & Forecast
from .forecast_arima import forecast_metric_arima, generate_forecast
from .forecast_arima import forecast_metric


# ------------------------------
# 🔹 API: dernière mesure météo
# ------------------------------
def api_latest(request):
    latest = WeatherMetric.objects.last()
    if not latest:
        return JsonResponse({"error": "No data available"}, status=404)

    return JsonResponse({
        "temperature": latest.temperature,
        "humidity": latest.humidity,
        "pressure": latest.pressure,
        "condition": latest.condition,
        "timestamp": latest.timestamp.strftime("%H:%M:%S")
    })


# ------------------------------
# 🔹 API: toutes les mesures
# ------------------------------
def all_metrics(request):
    metrics = WeatherMetric.objects.all().order_by('-timestamp')
    if not metrics.exists():
        return JsonResponse({"error": "No data available"}, status=404)

    data = [
        {
            "temperature": m.temperature,
            "humidity": m.humidity,
            "pressure": m.pressure,
            "condition": m.condition,
            "timestamp": m.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        }
        for m in metrics
    ]

    return JsonResponse(data, safe=False)


# ------------------------------
# 🔹 Dashboard principal
# ------------------------------
def dashboard(request):
    all_metrics = WeatherMetric.objects.all().order_by('timestamp')

    if not all_metrics.exists():
        context = {
            "metrics": {},
            "forecast": {},
            "latest": None,
            "recommendations": []
        }
        return render(request, "visualization/index.html", context)

    # Historical
    temperature = [m.temperature for m in all_metrics]
    rainfall = [m.rainfall for m in all_metrics]
    uv_index = [m.uv_index for m in all_metrics]
    humidity = [m.humidity for m in all_metrics]
    pressure = [m.pressure for m in all_metrics]
    wind_speed = [m.wind_speed for m in all_metrics]
    wind_direction = [m.wind_direction for m in all_metrics]
    visibility = [m.visibility for m in all_metrics]
    cloud_cover = [m.cloud_cover for m in all_metrics]
    timestamps = [m.timestamp.strftime("%H:%M") for m in all_metrics]

    # Forecast next 24 hours
    temp_forecast = forecast_metric(temperature, steps=24)
    rain_forecast = forecast_metric(rainfall, steps=24)
    uv_forecast = forecast_metric(uv_index, steps=24)

    forecast = {
        "temperature": temp_forecast,
        "rainfall": rain_forecast,
        "uv_index": uv_forecast,
        "wind_speed": wind_speed[-24:]
    }

    recommendations = generate_recommendations(forecast)
    latest = all_metrics.last()

    context = {
        "metrics": {
            "temperature": temperature,
            "humidity": humidity,
            "pressure": pressure,
            "wind_speed": wind_speed,
            "wind_direction": wind_direction,
            "rainfall": rainfall,
            "uv_index": uv_index,
            "visibility": visibility,
            "cloud_cover": cloud_cover,
            "timestamps": timestamps,
        },
        "forecast": forecast,
        "latest": latest,
        "recommendations": recommendations
    }

    return render(request, "visualization/index.html", context)


# ------------------------------
# 🔹 Page forecast
# ------------------------------
def forecast_view(request):
    forecast = generate_forecast()  # returns dict with hour_1, hour_2, hour_3, hour_4, hour_5
    print("DEBUG forecast:", forecast)  # <-- debug dans console
    
    return render(request, 'visualization/forecast.html', {'forecast': forecast})



# ------------------------------
# 🔹 Recommandations météo
# ------------------------------
def generate_recommendations(forecast):
    recommendations = []

    temp = forecast['temperature'][0]
    if temp < 10:
        recommendations.append("It's quite cold 🌬️ – wear a warm jacket if going outside.")
    elif 10 <= temp <= 25:
        recommendations.append("Temperature is nice 🌤️ – perfect for outdoor activities!")
    else:
        recommendations.append("It's hot 🥵 – stay hydrated.")

    rain_prob = forecast['rainfall'][0]
    if rain_prob > 60:
        recommendations.append(f"Carry an umbrella today – {rain_prob}% chance of rain ☔")

    uv_index = forecast['uv_index'][0]
    if uv_index >= 6:
        recommendations.append("UV index is high ☀️ – wear sunscreen!")

    return recommendations


# ------------------------------
# 🔹 API Forecast ARIMA (corrigé)
# ------------------------------
def forecast_api_arima(request):
    try:
        temp_forecast = forecast_metric_arima('temperature')
        rain_forecast = forecast_metric_arima('rainfall')
        uv_forecast = forecast_metric_arima('uv_index')

        rain_next_3h = [f['yhat'] for f in rain_forecast[:3]]
        rain_probability = min(100, max(0, int((sum([1 for r in rain_next_3h if r > 0]) / 3) * 100)))

        uv_values = [f['yhat'] for f in uv_forecast] if uv_forecast else []
        uv_peak = max(uv_values) if uv_values else 0
        uv_peak_time = uv_forecast[uv_values.index(uv_peak)]['ds'] if uv_values else ""

        data = {
            'temperature_forecast': temp_forecast,
            'rain_forecast': rain_forecast,
            'uv_forecast': uv_forecast,
            'rain_probability_next_3h': rain_probability,
            'uv_peak': uv_peak,
            'uv_peak_time': uv_peak_time
        }

    except Exception as e:
        data = {'error': str(e)}

    return JsonResponse(data)


# ------------------------------
# 🔹 Ajouter une donnée météo
# ------------------------------
def add_weather_metric(request):
    if request.method == 'POST':
        form = WeatherMetricForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = WeatherMetricForm()
    return render(request, 'visualization/add_metric.html', {'form': form})


# ------------------------------
# 🔹 Liste des mesures + API
# ------------------------------
def metrics_list(request):
    latest_data = {}
    error_message = None

    try:
        response = requests.get("http://127.0.0.1:8000/api/latest/", timeout=5)
        if response.status_code == 200:
            latest_data = response.json()
        else:
            error_message = f"Erreur API ({response.status_code}) : {response.text}"
    except requests.exceptions.RequestException as e:
        error_message = f"Erreur de connexion à l’API : {e}"

    all_metrics = WeatherMetric.objects.all().order_by('timestamp')

    metrics = {
        "temperature": [m.temperature for m in all_metrics],
        "humidity": [m.humidity for m in all_metrics],
        "pressure": [m.pressure for m in all_metrics],
        "timestamps": [m.timestamp.strftime("%H:%M") for m in all_metrics],
        "condition": latest_data.get("condition", "unknown"),
        "latest": latest_data,
        "error": error_message,
    }

    return render(request, 'visualization/metrics_list.html', {
        'metrics': metrics,
        'all_metrics': all_metrics,
    })


# ------------------------------
# 🔹 Settings
# ------------------------------
def settings_view(request):
    return render(request, 'visualization/settings.html', {})
