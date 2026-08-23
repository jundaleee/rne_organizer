"""최종 XGBoost 모델을 학습해서 models/final_xgb_model.pkl로 저장한다.

데이터 소스는 아래 우선순위로 자동 선택한다 (숫자가 낮을수록 우선):
  1. data/processed/ddi_data_real.csv        (scripts/data_preprocessing.py 결과물, 실측)
  2. data/processed/samples_log.csv          (총괄 앱에서 바로 쌓인 실측 데이터, qc_flag=="ok" 20개 이상일 때)
  3. data/processed/ddi_data_v2_demo.csv     (scripts/generate_synthetic_data.py 결과물, 가상 데이터)

실측 데이터가 없으면 3번(가상 데이터)으로 자동 대체하면서 콘솔에 경고를 출력하고,
models/model_metadata.json에 is_synthetic=True를 남긴다. 앱은 이 플래그를 보고
"⚠️ 시뮬레이션 데이터로 학습됨" 배너를 띄운다 (docs/research_master.md 16절 요구사항).

marinade가 없는(none) 행은 marinade_pH를 7.0(중성)으로 채운다 — 마스터 문서 14절 규칙.

실행:
    python scripts/build_final_model.py
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

from src.paths import DATA_PROCESSED_DIR, DEMO_SYNTHETIC_CSV, MODEL_METADATA_JSON, MODEL_PKL, REPO_ROOT
from src.predict import FEATURES

REAL_DDI_CSV = DATA_PROCESSED_DIR / "ddi_data_real.csv"
SAMPLES_LOG_CSV = DATA_PROCESSED_DIR / "samples_log.csv"

MIN_REAL_ROWS = 20  # 이보다 적으면 아직 "실제 학습"으로 보기 어렵다고 판단해 합성 데이터로 대체
TARGET_COL = "temp_c"


def _git_commit_hash() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT, check=True, capture_output=True, text=True, timeout=15,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "qc_flag" in df.columns:
        df = df[df["qc_flag"] == "ok"]
    df["marinade_pH"] = pd.to_numeric(df.get("marinade_pH"), errors="coerce").fillna(7.0)
    for col in FEATURES + [TARGET_COL]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(subset=[c for c in FEATURES if c in df.columns] + [TARGET_COL])


def load_training_data():
    """(DataFrame, source_name, is_synthetic) 반환."""
    if REAL_DDI_CSV.exists():
        df = _prepare(pd.read_csv(REAL_DDI_CSV))
        if len(df) >= MIN_REAL_ROWS:
            return df, str(REAL_DDI_CSV.relative_to(REPO_ROOT)), False
        print(f"[info] {REAL_DDI_CSV.name}에 유효 행이 {len(df)}개뿐이라 실측 학습 기준({MIN_REAL_ROWS}개) 미달.")

    if SAMPLES_LOG_CSV.exists():
        df = _prepare(pd.read_csv(SAMPLES_LOG_CSV))
        if len(df) >= MIN_REAL_ROWS:
            return df, str(SAMPLES_LOG_CSV.relative_to(REPO_ROOT)), False
        print(f"[info] {SAMPLES_LOG_CSV.name}에 유효 행이 {len(df)}개뿐이라 실측 학습 기준({MIN_REAL_ROWS}개) 미달.")

    if not DEMO_SYNTHETIC_CSV.exists():
        print("[info] 합성 데모 데이터가 없어서 새로 생성한다 (scripts/generate_synthetic_data.py).")
        from scripts.generate_synthetic_data import generate

        DEMO_SYNTHETIC_CSV.parent.mkdir(parents=True, exist_ok=True)
        generate().to_csv(DEMO_SYNTHETIC_CSV, index=False)

    df = _prepare(pd.read_csv(DEMO_SYNTHETIC_CSV))
    print(
        f"[synthetic-data-warning] 실측 데이터가 충분치 않아 합성 데이터 {len(df)}행으로 학습한다. "
        "이 모델의 MAE/성능 지표는 연구 결과가 아니라 파이프라인 검증용이다."
    )
    return df, str(DEMO_SYNTHETIC_CSV.relative_to(REPO_ROOT)), True


def train(df: pd.DataFrame):
    X = df[FEATURES]
    y = df[TARGET_COL]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = XGBRegressor(
        n_estimators=200, max_depth=4, learning_rate=0.08, random_state=42,
    )
    model.fit(X_train, y_train)

    holdout_mae = float(mean_absolute_error(y_test, model.predict(X_test)))

    # 배포용 최종 모델은 전체 데이터로 다시 학습 (holdout은 참고용 지표를 얻기 위함일 뿐)
    final_model = XGBRegressor(
        n_estimators=200, max_depth=4, learning_rate=0.08, random_state=42,
    )
    final_model.fit(X, y)

    return final_model, holdout_mae


if __name__ == "__main__":
    df, source, is_synthetic = load_training_data()
    model, holdout_mae = train(df)

    import joblib

    MODEL_PKL.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PKL)

    metadata = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit_hash(),
        "data_source": source,
        "is_synthetic": is_synthetic,
        "n_samples": len(df),
        "features": FEATURES,
        "target": TARGET_COL,
        "holdout_mae_c": round(holdout_mae, 4),
        "note": (
            "합성(시뮬레이션) 데이터로 학습됨 — 이 MAE는 연구 결과가 아니다."
            if is_synthetic
            else "실측 데이터로 학습됨."
        ),
    }
    with open(MODEL_METADATA_JSON, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"모델 저장: {MODEL_PKL}")
    print(f"메타데이터: {MODEL_METADATA_JSON}")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
