from django.db import models

class SensorReading(models.Model):
    id = models.AutoField(primary_key=True)        # SERIAL → AutoField in Django
    timestamp = models.DateTimeField(
        null=True,
        blank=True,
        db_column='timestamp'
    )
    device_id = models.CharField(max_length=50, db_column='device_id')
    temperature = models.FloatField(null=True, blank=True)
    humidity = models.FloatField(null=True, blank=True)
    rain = models.IntegerField(null=True, blank=True)
    soil_moisture = models.FloatField(null=True, blank=True)
    light_level = models.FloatField(null=True, blank=True)
    air_quality = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = 'sensor_readings'   # EXACT table name
        managed = False                # NEVER let Django create/alter/delete this table

    def __str__(self):
        return f"{self.device_id} - {self.timestamp}"
