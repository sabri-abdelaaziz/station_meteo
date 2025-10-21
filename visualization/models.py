from django.db import models

class WeatherMetric(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    temperature = models.FloatField()        # °C
    humidity = models.FloatField()           # %
    pressure = models.FloatField()           # hPa
    wind_speed = models.FloatField(null=True, blank=True)  # m/s
    wind_direction = models.FloatField(null=True, blank=True)  # degrés 0-360
    rainfall = models.FloatField(null=True, blank=True)   # mm
    uv_index = models.FloatField(null=True, blank=True)   # UV index
    condition = models.CharField(max_length=50)  # sunny, rain, cloudy, storm, etc.
    visibility = models.FloatField(null=True, blank=True) # km
    cloud_cover = models.FloatField(null=True, blank=True) # %

    def __str__(self):
        return f"{self.timestamp} - {self.condition}"
