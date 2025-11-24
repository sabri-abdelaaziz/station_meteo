from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import SensorReading
from .forms import WeatherMetricForm
import requests
import json

# Imports ARIMA & Forecast
from .forecast_arima import forecast_metric_arima, generate_forecast
from .forecast_arima import forecast_metric
from .db_utils import ensure_tables, get_last_n
from .forecast_arima import generate_forecast_days


# ------------------------------
# 🔹 API: dernière mesure météo
# ------------------------------
def api_latest(request):
    latest = SensorReading.objects.last()
    if not latest:
        return JsonResponse({"error": "No data available"}, status=404)

    return JsonResponse({
        "temperature": latest.temperature if latest.temperature is not None else 0,
        "humidity": latest.humidity if latest.humidity is not None else 0,
        "rain": latest.rain if latest.rain is not None else 0,
        "device_id": latest.device_id or "Capteur",
        "timestamp": latest.timestamp.strftime("%H:%M:%S") if latest.timestamp else "N/A"
    })


# ------------------------------
# 🔹 API: toutes les mesures
# ------------------------------
def all_metrics(request):
    metrics = SensorReading.objects.all().order_by('-timestamp')
    if not metrics.exists():
        return JsonResponse({"error": "No data available"}, status=404)

    data = [
        {
            "temperature": m.temperature,
            "humidity": m.humidity,
            "rain": m.rain,
            "device_id": m.device_id,
            "timestamp": m.timestamp.strftime("%Y-%m-%d %H:%M:%S") if m.timestamp else "N/A"
        }
        for m in metrics
    ]

    return JsonResponse(data, safe=False)


# ------------------------------
# 🔹 Dashboard principal
# ------------------------------
def dashboard(request):
    # Filtrer au niveau de la base de données et récupérer les derniers enregistrements
    all_metrics_list = list(SensorReading.objects.filter(temperature__isnull=False).order_by('-timestamp')[:1000])
    all_metrics_list.reverse()  # Réorganiser en ordre chronologique pour les graphes

    if not all_metrics_list:
        context = {
            "metrics": {},
            "forecast": {},
            "latest": None,
            "recommendations": []
        }
        return render(request, "visualization/index.html", context)

    # Historical
    temperature = [m.temperature for m in all_metrics_list if m.temperature is not None]
    rain = [m.rain if m.rain is not None else 0 for m in all_metrics_list if m.temperature is not None]
    humidity = [m.humidity if m.humidity is not None else 0 for m in all_metrics_list if m.temperature is not None]
    soil_moisture = [m.soil_moisture if m.soil_moisture is not None else 0 for m in all_metrics_list if m.temperature is not None]
    light_level = [m.light_level if m.light_level is not None else 0 for m in all_metrics_list if m.temperature is not None]
    air_quality = [m.air_quality if m.air_quality is not None else 0 for m in all_metrics_list if m.temperature is not None]
    # Replace missing attributes with empty lists
    uv_index = []
    pressure = []
    wind_speed = []
    wind_direction = []
    visibility = []
    cloud_cover = []
    timestamps = [m.timestamp.strftime("%H:%M") for m in all_metrics_list if m.temperature is not None]

    # Forecast next 24 hours
    temp_forecast = forecast_metric(temperature, steps=24)
    rain_forecast = forecast_metric(rain, steps=24) if rain else []
    uv_forecast = []

    forecast = {
        "temperature": temp_forecast,
        "rainfall": rain_forecast,
        "uv_index": uv_forecast,
        "wind_speed": []
    }

    recommendations = generate_recommendations(forecast)
    latest = all_metrics_list[-1] if all_metrics_list else None

    context = {
        "metrics": {
            "temperature": temperature,
            "humidity": humidity,
            "rain": rain,
            "soil_moisture": soil_moisture,
            "light_level": light_level,
            "air_quality": air_quality,
            "timestamps": timestamps,
        },
        "forecast": forecast,
        "latest": latest,
        "recommendations": recommendations
    }

    # Récupérer les 10 dernières valeurs horaires depuis la base PostgreSQL
    try:
        ensure_tables()
        last_10 = get_last_n('meteo_hourly', 10, 'temp_c')
    except Exception as e:
        print(f"DEBUG: impossible de charger last_10 depuis PostgreSQL: {e}")
        last_10 = []

    context['last_10_hourly'] = last_10
    # Générer prévision 5 jours pour le dashboard
    try:
        forecast_5days = generate_forecast_days(steps=5)
    except Exception as e:
        print(f"DEBUG: impossible de générer forecast_5days: {e}")
        forecast_5days = []

    context['forecast_5days'] = forecast_5days

    return render(request, "visualization/index.html", context)


# ------------------------------
# 🔹 Page forecast
# ------------------------------
def forecast_view(request):
    # Générer la prévision pour 5 prochaines heures et 5 prochains jours
    try:
        forecast_hours = generate_forecast()  # dict with hour_1..hour_5
    except Exception as e:
        print(f"DEBUG: generate_forecast error: {e}")
        forecast_hours = {}

    try:
        forecast_days = generate_forecast_days(steps=5)
    except Exception as e:
        print(f"DEBUG forecast_days error: {e}")
        forecast_days = []

    # Récupérer 10 dernières valeurs horaires pour affichage
    try:
        ensure_tables()
        last_10 = get_last_n('meteo_hourly', 10, 'temp_c')
    except Exception as e:
        print(f"DEBUG: impossible de charger last_10 depuis PostgreSQL: {e}")
        last_10 = []

    context = {
        'forecast_hours': forecast_hours,
        'forecast_days': forecast_days,
        'last_10': last_10,
    }

    return render(request, 'visualization/forecast.html', context)



# ------------------------------
# 🔹 Recommandations météo
# ------------------------------
def generate_recommendations(forecast):
    recommendations = []

    if forecast.get('temperature'):
        temp = forecast['temperature'][0] if isinstance(forecast['temperature'], list) else forecast['temperature']
        if temp < 10:
            recommendations.append("It's quite cold 🌬️ – wear a warm jacket if going outside.")
        elif 10 <= temp <= 25:
            recommendations.append("Temperature is nice 🌤️ – perfect for outdoor activities!")
        else:
            recommendations.append("It's hot 🥵 – stay hydrated.")

    if forecast.get('rainfall'):
        rain_prob = forecast['rainfall'][0] if isinstance(forecast['rainfall'], list) else forecast['rainfall']
        if rain_prob > 60:
            recommendations.append(f"Carry an umbrella today – {rain_prob}% chance of rain ☔")

    return recommendations


# ------------------------------
# 🔹 API Forecast ARIMA (corrigé)
# ------------------------------
def forecast_api_arima(request):
    try:
        temp_forecast = forecast_metric_arima('temperature')
        rain_forecast = forecast_metric_arima('rain')

        rain_next_3h = [f['yhat'] for f in rain_forecast[:3]]
        rain_probability = min(100, max(0, int((sum([1 for r in rain_next_3h if r > 0]) / 3) * 100)))

        data = {
            'temperature_forecast': temp_forecast,
            'rain_forecast': rain_forecast,
            'rain_probability_next_3h': rain_probability,
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

    all_metrics_qs = SensorReading.objects.all().order_by('timestamp')

    metrics = {
        "temperature": [m.temperature for m in all_metrics_qs if m.temperature is not None],
        "humidity": [m.humidity for m in all_metrics_qs if m.humidity is not None],
        "rain": [m.rain for m in all_metrics_qs if m.rain is not None],
        "timestamps": [m.timestamp.strftime("%H:%M") if m.timestamp else "" for m in all_metrics_qs],
        "latest": latest_data,
        "error": error_message,
    }

    return render(request, 'visualization/metrics_list.html', {
        'metrics': metrics,
        'all_metrics': all_metrics_qs,
    })


# ------------------------------
# 🔹 Settings
# ------------------------------
def settings_view(request):
    return render(request, 'visualization/settings.html', {})
