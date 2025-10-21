from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import WeatherMetric

def dashboard(request):
    latest = WeatherMetric.objects.last()
    metrics = {
        "temperature": [m.temperature for m in WeatherMetric.objects.all()],
        "humidity": [m.humidity for m in WeatherMetric.objects.all()],
        "pressure": [m.pressure for m in WeatherMetric.objects.all()],
        "timestamps": [m.timestamp.strftime("%H:%M") for m in WeatherMetric.objects.all()],
        "condition": latest.condition if latest else "unknown",
    }
    return render(request, "visualization/index.html", {"metrics": metrics})

def api_latest(request):
    """Retourne la dernière mesure en JSON pour mise à jour dynamique"""
    latest = WeatherMetric.objects.last()
    return JsonResponse({
        "temperature": latest.temperature,
        "humidity": latest.humidity,
        "pressure": latest.pressure,
        "condition": latest.condition,
        "timestamp": latest.timestamp.strftime("%H:%M:%S")
    })


from .forms import WeatherMetricForm

def add_weather_metric(request):
    if request.method == 'POST':
        form = WeatherMetricForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('dashboard')  # redirect to your dashboard page
    else:
        form = WeatherMetricForm()
    return render(request, 'visualization/add_metric.html', {'form': form})
from django.contrib.auth.decorators import login_required

# Historique des mesures
def metrics_list(request):
    metrics = WeatherMetric.objects.all().order_by('-timestamp')
    return render(request, 'visualization/metrics_list.html', {'metrics': metrics})

# Page de paramètres
def settings_view(request):
    # Ici tu peux gérer des paramètres comme la fréquence de mise à jour,
    # seuils d'alerte, unités, etc.
    if request.method == 'POST':
        # Exemple : traiter un formulaire de paramètres
        # form = SettingsForm(request.POST)
        # if form.is_valid():
        #     form.save()
        #     return redirect('settings')
        pass
    # Sinon, afficher les paramètres actuels
    return render(request, 'visualization/settings.html', {})
