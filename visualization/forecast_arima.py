import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAXResults
from statsmodels.tsa.arima.model import ARIMA
from .models import WeatherMetric
from datetime import timedelta, datetime
import os
import pickle
import random
import bz2
from django.db import connection

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
    data = WeatherMetric.objects.all().order_by('timestamp').values('timestamp', metric_name)
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
def load_sarima_model():
    """
    Charge le modèle SARIMA sauvegardé depuis un fichier compressé .bz2
    """
    model_path = os.path.join(
        os.path.dirname(__file__),
        "forecast_model",
        "sarima_temperature_prediction.pkl.bz2"   # Fichier compressé avec bz2
    )

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")

    # Charger le modèle depuis le fichier compressé bz2
    try:
        with bz2.BZ2File(model_path, "r") as f:
            sarima_model_loaded = pickle.load(f)
        
        # Vérifier que c'est bien un modèle SARIMAX
        if hasattr(sarima_model_loaded, 'get_forecast'):
            print(f"DEBUG: Modèle chargé avec bz2 + pickle. Type: {type(sarima_model_loaded)}")
            return sarima_model_loaded
        else:
            raise ValueError(f"Le modèle chargé n'est pas un modèle SARIMAX valide. Type: {type(sarima_model_loaded)}, Attributs: {dir(sarima_model_loaded)[:10]}")
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

    # Récupérer les 10 dernières températures depuis PostgreSQL, table meteo
    try:
        with connection.cursor() as cursor:
            # Requête SQL pour récupérer les 10 dernières températures
            # Compatible PostgreSQL
            query = """
                SELECT temperature 
                FROM meteo 
                ORDER BY timestamp DESC 
                LIMIT 10
            """
            cursor.execute(query)
            results = cursor.fetchall()
            
            # Extraire les températures et les inverser pour avoir les plus anciennes en premier
            # results est une liste de tuples, on extrait le premier élément de chaque tuple
            temperature_list = [float(row[0]) for row in reversed(results)]
            
            # Si on n'a pas 10 valeurs, compléter avec la dernière valeur disponible
            if len(temperature_list) < 10:
                if len(temperature_list) > 0:
                    last_temp = temperature_list[-1]
                    temperature_list = [last_temp] * (10 - len(temperature_list)) + temperature_list
                else:
                    # Si aucune donnée, utiliser des valeurs par défaut
                    temperature_list = [20.0] * 10
                    print("DEBUG: Aucune donnée dans la table meteo, utilisation de valeurs par défaut")
            
            print(f"DEBUG: Températures récupérées depuis PostgreSQL: {temperature_list}")
            print(f"DEBUG: Nombre de valeurs: {len(temperature_list)}")
            print(f"DEBUG: Lag_1 (plus récent) = {temperature_list[-1]}, Lag_10 (plus ancien) = {temperature_list[0]}")
            
    except Exception as e:
        print(f"DEBUG ERROR: Erreur lors de la récupération depuis PostgreSQL: {e}")
        # En cas d'erreur, utiliser des valeurs par défaut
        temperature_list = [20.0] * 10
        print(f"DEBUG: Utilisation de valeurs par défaut: {temperature_list}")
    
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
