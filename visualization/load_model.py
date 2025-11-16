import pickle
import os

MODEL_PATH = os.path.join(
    os.path.dirname(__file__),     # your_app/
    "forecast_model",
    "sarima_temperature_prediction.pkl"
)

def load_sarima_model():
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    return model
