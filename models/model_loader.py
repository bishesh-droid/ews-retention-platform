import joblib
import os

MODELS_DIR = os.path.dirname(os.path.abspath(__file__))
SAVED_MODELS_DIR = os.path.join(MODELS_DIR, "saved_models")

def load_model(model_filename):
    path = os.path.join(SAVED_MODELS_DIR, model_filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Model file not found: {path}")
    return joblib.load(path)
