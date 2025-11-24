from django import forms
from .models import SensorReading


class WeatherMetricForm(forms.ModelForm):
    """Formulaire nommé `WeatherMetricForm` (pour compatibilité) mais basé
    sur le modèle `SensorReading` présent dans `models.py`.
    Champs exposés : `device_id`, `timestamp`, `temperature`, `humidity`,
    `rain`, `soil_moisture`, `light_level`, `air_quality`.
    """
    class Meta:
        model = SensorReading
        fields = [
            'device_id', 'timestamp', 'temperature', 'humidity', 'rain',
            'soil_moisture', 'light_level', 'air_quality'
        ]
        widgets = {
            'device_id': forms.TextInput(attrs={'class': 'form-control'}),
            'timestamp': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'temperature': forms.NumberInput(attrs={'step': 0.1, 'class': 'form-control'}),
            'humidity': forms.NumberInput(attrs={'step': 0.1, 'class': 'form-control'}),
            'rain': forms.NumberInput(attrs={'step': 1, 'class': 'form-control'}),
            'soil_moisture': forms.NumberInput(attrs={'step': 0.1, 'class': 'form-control'}),
            'light_level': forms.NumberInput(attrs={'step': 0.1, 'class': 'form-control'}),
            'air_quality': forms.NumberInput(attrs={'step': 0.1, 'class': 'form-control'}),
        }
