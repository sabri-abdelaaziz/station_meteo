from django.urls import path
from . import views
from django.contrib.auth import views as auth_views  # pour logout

urlpatterns = [
    path('', views.dashboard, name='dashboard'),  # Dashboard
    path('metrics/', views.metrics_list, name='metrics_list'),  # Historique
    path('add/', views.add_weather_metric, name='add_metric'),  # Ajouter données
    path('settings/', views.settings_view, name='settings'),  # Paramètres
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),  # Déconnexion
    path('api/metrics/latest/', views.api_latest, name='api_latest'),  # API for latest metrics 
    path('api/metrics/all/',views.all_metrics, name='api_all_metrics'),
    path('forecast/', views.forecast_view, name='forecast'),  # <-- Forecast page
]
