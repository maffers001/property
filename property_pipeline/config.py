"""Configuration and constants for the property pipeline."""

import os
from pathlib import Path

BASE_DIR = Path(os.environ.get("DATA_PATH", str(Path(__file__).resolve().parent.parent / "data" / "property")))

BANK_DOWNLOAD_DIR = BASE_DIR / "bank-download"
GENERATED_DIR = BASE_DIR / "generated"
CHECKED_DIR = BASE_DIR / "checked"
REVIEW_DIR = BASE_DIR / "review"

DB_PATH = Path(os.environ.get("DB_PATH", str(BASE_DIR / "labels.db")))
MODEL_PATH = Path(os.environ.get("MODEL_PATH", str(BASE_DIR / "ml_model.joblib")))

RSA_CAPITAL_DATE = "2022-08-01"

STARLING_ACCOUNT = "60-83-71 00558156"

CONFIDENCE_AUTO_ACCEPT = 0.93
CONFIDENCE_FORCE_REVIEW = 0.75

STRENGTH_CONFIDENCE = {
    "strong": 0.99,
    "medium": 0.93,
    "weak": 0.86,
    "catch_all": 0.65,
}
