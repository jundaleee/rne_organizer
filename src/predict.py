"""predict_app 로직 — 6개 입력값으로 가공 온도를 예측한다."""

import json
from pathlib import Path

import pandas as pd

FEATURES = [
    "DDI",
    "Ct_100",
    "DNA_conc",
    "DNA_purity_260280",
    "DNA_purity_260230",
    "marinade_pH",
]


def load_model(model_path: Path):
    if not model_path.exists():
        return None
    import joblib

    return joblib.load(model_path)


def load_metadata(metadata_path: Path) -> dict:
    if not metadata_path.exists():
        return {}
    with open(metadata_path, "r", encoding="utf-8") as f:
        return json.load(f)


def predict_temperature(model, inputs: dict) -> float:
    X = pd.DataFrame([[inputs[f] for f in FEATURES]], columns=FEATURES)
    return float(model.predict(X)[0])


def range_check(train_df: pd.DataFrame, inputs: dict) -> dict:
    """입력값이 학습 데이터 범위(min~max) 안인지 피처별로 확인.
    범위 밖이면 외삽(extrapolation)이라 예측을 신뢰하기 어렵다는 뜻."""
    flags = {}
    for f in FEATURES:
        if f not in train_df.columns:
            continue
        col = train_df[f].dropna()
        if col.empty:
            continue
        lo, hi = float(col.min()), float(col.max())
        flags[f] = {"value": inputs[f], "min": lo, "max": hi, "in_range": lo <= inputs[f] <= hi}
    return flags
