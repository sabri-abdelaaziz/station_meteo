from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import WeatherMetric
from .forms import WeatherMetricForm
import requests
from django.shortcuts import render
from .forecast_arima import forecast_metric_arima, generate_forecast

from django.shortcuts import render
from .models import WeatherMetric

def api_latest(request):
    """API REST: retourne la dernière mesure météo."""
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




def all_metrics(request):
    """API REST: retourne toutes les mesures météo enregistrées."""
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




# your_app/views.py
from django.shortcuts import render
from .models import WeatherMetric
from .forecast_arima import forecast_metric

# views.py
from django.shortcuts import render
from .models import WeatherMetric
from .forecast_arima import forecast_metric  # your ARIMA forecast function

# views.py
from django.shortcuts import render
from .models import WeatherMetric
from .forecast_arima import forecast_metric

def dashboard(request):
    # Fetch all metrics ordered by timestamp
    all_metrics = WeatherMetric.objects.all().order_by('timestamp')
    
    # Handle empty dataset
    if not all_metrics.exists():
        context = {
            "metrics": {},
            "forecast": {},
            "latest": None,
            "recommendations": []
        }
        return render(request, "visualization/index.html", context)

    # Historical data
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
        "wind_speed": wind_speed[-24:]  # Optional: last 24h for wind
    }

    # Generate AI-based recommendations
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

def forecast_view(request):
    forecast = generate_forecast()  # returns dict with temperature, rainfall, uv_index
    return render(request, 'visualization/forecast.html', {'forecast': forecast})

# weather_recommendations.py
def generate_recommendations(forecast):
    recommendations = []

    # Temperature-based recommendation
    temp = forecast['temperature'][0]  # next hour temp
    if temp < 10:
        recommendations.append("It's quite cold 🌬️ – wear a warm jacket if going outside.")
    elif 10 <= temp <= 25:
        recommendations.append("Temperature is nice 🌤️ – perfect for outdoor activities!")
    else:
        recommendations.append("It's hot 🥵 – stay hydrated if you go out.")

    # Rain-based recommendation
    rain_prob = forecast['rainfall'][0]  # % chance of rain
    if rain_prob > 60:
        recommendations.append(f"Carry an umbrella today – {rain_prob}% chance of rain ☔")

    # UV-based recommendation
    uv_index = forecast['uv_index'][0]
    if uv_index >= 6:
        recommendations.append("UV index is high ☀️ – wear sunscreen or a hat!")

   
    return recommendations


def forecast_api_arima(request):
    """
    Returns ARIMA predictions for temperature, rainfall, and UV.
    """
    try:
        temp_forecast = forecast_metric_arima('temperature')
        rain_forecast = forecast_metric_arima('rainfall')
        uv_forecast = forecast_metric_arima('uv_index')

        # Probability of rain in next 3 hours
        rain_next_3h = [f['yhat'] for f in rain_forecast[:3]]
        rain_probability = min(100, max(0, int((sum([1 for r in rain_next_3h if r>0])/3)*100)))

        uv_peak = max([f['yhat'] for f in uv_forecast]) if uv_forecast else 0
        uv_peak_time = uv_forecast[[f['yhat'] for f in uv_forecast].index(uv_peak)]['ds'] if uv_forecast else ""

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

def add_weather_metric(request):
    """Formulaire pour ajouter manuellement des données météo."""
    if request.method == 'POST':
        form = WeatherMetricForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = WeatherMetricForm()
    return render(request, 'visualization/add_metric.html', {'form': form})


def metrics_list(request):
    """Liste de toutes les mesures avec récupération de la dernière via l’API."""
    latest_data = {}
    error_message = None

    # 🔹 Fetch the latest data from your API
    try:
        response = requests.get("http://127.0.0.1:8000/api/latest/", timeout=5)
        if response.status_code == 200:
            latest_data = response.json()
        else:
            error_message = f"Erreur API ({response.status_code}) : {response.text}"
    except requests.exceptions.RequestException as e:
        error_message = f"Erreur de connexion à l’API : {e}"

    # 🔹 Get all metrics from DB
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

def settings_view(request):
    """Page de paramètres (facultatif pour maintenant)."""
    return render(request, 'visualization/settings.html', {})
