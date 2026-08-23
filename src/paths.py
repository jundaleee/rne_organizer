"""저장소 안의 모든 경로를 한 곳에서 정의한다.
다른 모듈이 상대경로를 각자 계산하면서 미묘하게 어긋나는 걸 막기 위함."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

DATA_RAW_DIR = REPO_ROOT / "data" / "raw"
DATA_PROCESSED_DIR = REPO_ROOT / "data" / "processed"
SAMPLES_LOG_CSV = DATA_PROCESSED_DIR / "samples_log.csv"
DEMO_SYNTHETIC_CSV = DATA_PROCESSED_DIR / "ddi_data_v2_demo.csv"

MODELS_DIR = REPO_ROOT / "models"
MODEL_PKL = MODELS_DIR / "final_xgb_model.pkl"
MODEL_METADATA_JSON = MODELS_DIR / "model_metadata.json"

DOCS_DIR = REPO_ROOT / "docs"
