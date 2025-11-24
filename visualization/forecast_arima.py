import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAXResults
from statsmodels.tsa.arima.model import ARIMA
from .models import SensorReading
from datetime import timedelta, datetime
import os
import pickle
import random
import bz2
from django.db import connection
from .db_utils import ensure_tables, get_last_n

# Essayer d'importer joblib (souvent utilisé pour sauvegarder des modèles)
try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False


# -------------------------------------------------------------------
# 🔹 1. ARIMA simple (forecast_api_arima)
# -------------------------------------------------------------------
def forecast_metric_arima(metric_name, steps=24):
    data = SensorReading.objects.all().order_by('timestamp').values('timestamp', metric_name)
    df = pd.DataFrame(data)

    if df.empty:
        return []

    df.set_index('timestamp', inplace=True)
    ts = df[metric_name].astype(float)

    try:
        model = ARIMA(ts, order=(5, 1, 0))
        model_fit = model.fit()
        forecast_values = model_fit.forecast(steps=steps)
    except Exception as e:
        print("ARIMA error:", e)
        return []

    last_time = ts.index[-1]
    forecast = []
    for i, value in enumerate(forecast_values):
        forecast.append({
            "ds": (last_time + timedelta(hours=i+1)).strftime("%Y-%m-%d %H:%M:%S"),
            "yhat": round(float(value), 2)
        })

    return forecast



# -------------------------------------------------------------------
# 🔹 2. ARIMA simple pour dashboard
# -------------------------------------------------------------------
def forecast_metric(metric_values, steps=24):
    metric_values = [float(x) for x in metric_values if x is not None]

    if len(metric_values) < 10:
        return [metric_values[-1]] * steps

    model = ARIMA(metric_values, order=(5, 1, 0))
    model_fit = model.fit()
    forecast = model_fit.forecast(steps=steps)
    return forecast.tolist()



# -------------------------------------------------------------------
# 🔹 3. CHARGEMENT DU MODELE SARIMAX
# -------------------------------------------------------------------
def load_sarima_model(filename: str = "sarima_temperature_prediction.pkl.bz2"):
    """Charge le modèle SARIMA sauvegardé depuis un fichier compressé .bz2.

    `filename` doit être le nom du fichier dans le dossier `forecast_model`.
    Retourne l'objet modèle s'il contient `get_forecast`, sinon lève une erreur.
    """
    model_path = os.path.join(
        os.path.dirname(__file__),
        "forecast_model",
        filename
    )

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")

    try:
        with bz2.BZ2File(model_path, "r") as f:
            sarima_model_loaded = pickle.load(f)

        if hasattr(sarima_model_loaded, 'get_forecast'):
            print(f"DEBUG: Modèle chargé depuis {filename}. Type: {type(sarima_model_loaded)}")
            return sarima_model_loaded
        else:
            raise ValueError(f"Le modèle chargé n'est pas un modèle SARIMAX valide. Type: {type(sarima_model_loaded)}")
    except Exception as e:
        raise ValueError(f"Impossible de charger le modèle depuis {model_path}. Erreur: {e}")



# -------------------------------------------------------------------
# 🔹 4. FORECAST avec 10 LAGS EXOGÈNES - Prédictions pour 5 heures
# -------------------------------------------------------------------
def generate_forecast():
    """
    Génère les prédictions pour les 5 prochaines heures en utilisant:
    - SARIMA pour la température (avec lags exogènes)
    - Variables aléatoires pour tester les inputs
    - Logique des lags : résultat heure 1 → dernière lag pour heure 2,
      résultats heures 1-2 → 2 dernières lags pour heure 3, etc.
    """
    steps = 5  # Prédictions pour les 5 prochaines heures
    
    # ========== TEMPÉRATURE avec SARIMA ==========
    try:
        model = load_sarima_model()
        print(f"DEBUG: Modèle SARIMA chargé avec succès. Type: {type(model)}")
    except Exception as e:
        error_msg = f"SARIMA model not loaded: {e}"
        print(f"DEBUG ERROR: {error_msg}")
        return {"error": error_msg}

    # S'assurer que les tables existent
    try:
        ensure_tables()
    except Exception as e:
        print(f"DEBUG ERROR: Impossible de créer/valider les tables: {e}")

    # Essayer de récupérer les 10 dernières températures depuis la table `meteo_hourly`
    try:
        temperature_list = get_last_n('meteo_hourly', 10, 'temp_c')

        # Si pas assez de valeurs, tenter la table `meteo_10sec`
        if len(temperature_list) < 10:
            extra = get_last_n('meteo_10sec', 10 - len(temperature_list), 'temp_c')
            temperature_list = (extra + temperature_list)[-10:]

        # Si toujours insuffisant, fallback sur le modèle Django `SensorReading`
        if len(temperature_list) < 10:
            data = SensorReading.objects.all().order_by('-timestamp').values_list('temperature', flat=True)[:10]
            temperature_list = list(reversed([float(x) for x in data]))

        # Remplir si encore insuffisant
        if len(temperature_list) < 10:
            if temperature_list:
                last_temp = temperature_list[-1]
                temperature_list = [last_temp] * (10 - len(temperature_list)) + temperature_list
            else:
                temperature_list = [20.0] * 10

        print(f"DEBUG: Températures récupérées: {temperature_list}")
    except Exception as e:
        print(f"DEBUG ERROR: Erreur lors de la récupération des températures: {e}")
        temperature_list = [20.0] * 10
    
    # Calculer l'heure de base (maintenant)
    base_time = datetime.now()
    print(f"DEBUG: Heure de base: {base_time}")

    # Générer les prédictions de température pour les 5 prochaines heures
    # temp_lags contiendra les valeurs historiques + les prédictions successives
    temp_lags = temperature_list.copy()
    forecast_results = []  # Liste pour stocker les résultats de chaque heure
    
    for step in range(steps):
        # Construire exogènes (lags 1 → 10) avec les dernières valeurs disponibles
        # Pour l'heure step+1, on utilise les 10 dernières valeurs de temp_lags
        future_exog = {}
        for i in range(1, 11):
            if len(temp_lags) >= i:
                # Prendre les i dernières valeurs disponibles
                future_exog[f"Temp_C_lag_{i}"] = [temp_lags[-i]]
            else:
                # Si pas assez de données, utiliser la première valeur
                future_exog[f"Temp_C_lag_{i}"] = [temp_lags[0]]
        
        exog_df = pd.DataFrame(future_exog)
        print(f"DEBUG: Heure {step+1} - Lags utilisés: {[temp_lags[-i] for i in range(1, min(11, len(temp_lags)+1))]}")
        
        try:
            forecast = model.get_forecast(steps=1, exog=exog_df)
            predicted_temp = round(float(forecast.predicted_mean.iloc[0]), 2)
            conf_int = forecast.conf_int().iloc[0]
            lower_bound = round(float(conf_int[0]), 2)
            upper_bound = round(float(conf_int[1]), 2)
        except Exception as e:
            print(f"DEBUG: Erreur lors de la prédiction heure {step+1}: {e}")
            # En cas d'erreur, utiliser la dernière valeur avec une petite variation
            predicted_temp = round(float(temp_lags[-1]) + random.uniform(-0.5, 0.5), 2)
            lower_bound = round(predicted_temp - 1.0, 2)
            upper_bound = round(predicted_temp + 1.0, 2)
        
        # Calculer l'heure de prédiction (base_time + step+1 heures)
        prediction_time = base_time + timedelta(hours=step+1)
        
        # Stocker le résultat de cette heure
        forecast_results.append({
            'temperature': predicted_temp,
            'lower': lower_bound,
            'upper': upper_bound,
            'alert': get_temperature_alert(predicted_temp),
            'time': prediction_time.strftime("%H:%M"),
            'datetime': prediction_time.strftime("%Y-%m-%d %H:%M")
        })
        
        # Mettre à jour temp_lags pour les prochaines prédictions
        # On garde les 9 dernières valeurs et on ajoute la nouvelle prédiction
        # Cela décale la liste : la première valeur est supprimée, la nouvelle prédiction est ajoutée à la fin
        # Exemple: [16,16,16,15,15,15,15,16,17,19] → prédiction 19.1 → [16,16,15,15,15,15,16,17,19,19.1]
        temp_lags = temp_lags[-9:] + [predicted_temp]
        print(f"DEBUG: Heure {step+1} - Température prédite: {predicted_temp}°C")
        print(f"DEBUG: Heure {step+1} - Lags mis à jour (10 valeurs): {temp_lags}")
        print(f"DEBUG: Heure {step+1} - Lag_1 (plus récent) = {temp_lags[-1]}, Lag_10 (plus ancien) = {temp_lags[0]}")
    
    # Construire le dictionnaire de retour avec les 5 heures
    result = {}
    for i in range(1, 6):
        result[f'hour_{i}'] = forecast_results[i-1]
    
    return result


def generate_forecast_days(steps=5):
    """Génère une prévision pour les `steps` prochains jours en utilisant la table `meteo_daily`.

    Retourne une liste de dicts: [{'date': 'YYYY-MM-DD', 'temp': x}, ...]
    """
    try:
        ensure_tables()
    except Exception as e:
        print(f"DEBUG ERROR: ensure_tables failed: {e}")

    # Récupérer les 10 dernières moyennes journalières
    try:
        daily = get_last_n('meteo_daily', 10, 'temp_mean')
    except Exception:
        daily = []

    # Si pas de données journalières, construire à partir de SensorReading
    if not daily:
        try:
            qs = SensorReading.objects.all()
            if qs.exists():
                # Agréger par date
                df = pd.DataFrame(list(qs.values('timestamp', 'temperature')))
                df['date'] = pd.to_datetime(df['timestamp']).dt.date
                daily_df = df.groupby('date')['temperature'].mean().reset_index()
                daily = daily_df['temperature'].astype(float).tolist()[-10:]
        except Exception as e:
            print(f"DEBUG ERROR building daily from SensorReading: {e}")

    if not daily:
        daily = [20.0] * 10

    # Première tentative : utiliser un modèle SARIMA daily s'il existe
    try:
        daily_model = load_sarima_model("sarima_temperature_daily_prediction.pkl.bz2")
        # Certains modèles retournent un objet avec get_forecast
        try:
            forecast = daily_model.get_forecast(steps=steps)
            preds = [float(x) for x in forecast.predicted_mean]
            base_date = datetime.now().date()
            results = []
            for i, p in enumerate(preds, start=1):
                d = base_date + timedelta(days=i)
                results.append({'date': d.strftime("%Y-%m-%d"), 'temp': round(float(p), 2)})
            return results
        except Exception as e:
            print(f"DEBUG ERROR using daily SARIMA model: {e}")
            # si le chargement a réussi mais la prédiction a échoué, tomber sur le fallback
    except FileNotFoundError:
        # Pas de modèle daily trouvé — on utilisera le fallback ci-dessous
        pass
    except Exception as e:
        print(f"DEBUG ERROR loading daily model: {e}")

    # Fallback : ajuster un ARIMA simple sur la série quotidienne construite
    series = pd.Series(daily)
    try:
        model = ARIMA(series, order=(2, 1, 0))
        model_fit = model.fit()
        preds = model_fit.forecast(steps=steps)
        base_date = datetime.now().date()
        results = []
        for i, p in enumerate(preds, start=1):
            d = base_date + timedelta(days=i)
            results.append({'date': d.strftime("%Y-%m-%d"), 'temp': round(float(p), 2)})
        return results
    except Exception as e:
        print(f"DEBUG ERROR in generate_forecast_days: {e}")
        # Fallback simple: repeat last value
        last = daily[-1]
        base_date = datetime.now().date()
        return [{'date': (base_date + timedelta(days=i)).strftime("%Y-%m-%d"), 'temp': round(float(last), 2)} for i in range(1, steps+1)]


def get_temperature_alert(temp):
    """Génère une alerte basée sur la température"""
    if temp < 0:
        return "❄️ Très froid"
    elif temp < 10:
        return "🧊 Froid"
    elif temp > 35:
        return "🔥 Très chaud"
    elif temp > 30:
        return "☀️ Chaud"
    else:
        return "✅ Normal"



# -------------------------------------------------------------------
# 🔹 5. Petite fonction ARIMA rapide
# -------------------------------------------------------------------
def forecast_arima(series, steps=1):
    series = series.dropna()
    if len(series) < 10:
        return [series.iloc[-1]] * steps

    model = ARIMA(series, order=(1, 1, 1))
    model_fit = model.fit()
    pred = model_fit.forecast(steps=steps)
    return pred.tolist()
