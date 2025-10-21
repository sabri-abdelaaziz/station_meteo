from django import forms
from .models import WeatherMetric

class WeatherMetricForm(forms.ModelForm):
    class Meta:
        model = WeatherMetric
        fields = [
            'temperature', 'humidity', 'pressure',
            'wind_speed', 'wind_direction', 'rainfall',
            'uv_index', 'visibility', 'cloud_cover', 'condition'
        ]
        widgets = {
            'temperature': forms.NumberInput(attrs={'step': 0.1, 'class': 'form-control'}),
            'humidity': forms.NumberInput(attrs={'step': 0.1, 'class': 'form-control'}),
            'pressure': forms.NumberInput(attrs={'step': 0.1, 'class': 'form-control'}),
            'wind_speed': forms.NumberInput(attrs={'step': 0.1, 'class': 'form-control'}),
            'wind_direction': forms.NumberInput(attrs={'step': 1, 'class': 'form-control'}),
            'rainfall': forms.NumberInput(attrs={'step': 0.1, 'class': 'form-control'}),
            'uv_index': forms.NumberInput(attrs={'step': 0.1, 'class': 'form-control'}),
            'visibility': forms.NumberInput(attrs={'step': 0.1, 'class': 'form-control'}),
            'cloud_cover': forms.NumberInput(attrs={'step': 1, 'class': 'form-control'}),
   'condition': forms.Select(choices=[
    ('sunny', 'Ensoleillé'),
    ('rain', 'Pluie'),
    ('cloudy', 'Nuageux'),
    ('storm', 'Orage'),
    ('snow', 'Neige'),
    ('fog', 'Brouillard'),
    ('unknown', 'Inconnu')
            ], attrs={'class':'form-control'}),
        }
