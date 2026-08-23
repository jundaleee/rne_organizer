"""data/raw/의 원자료 CSV를 합쳐서 DDI를 계산한 실측 데이터셋을 만든다.

입력 (data/raw/):
    NanoDrop_raw.csv   컬럼: sample_id, DNA_conc, DNA_purity_260280, DNA_purity_260230
    qPCR_Ct_raw.csv    컬럼: sample_id, Ct_100, Ct_600 (미검출이면 빈 칸 또는 "Undetermined")
    samples_meta.csv   컬럼: sample_id, date, member, group, marinade, temp_c, time_min, marinade_pH
                       (총괄 앱 데이터 입력 탭을 쓰면 data/processed/samples_log.csv가 이 역할을 대신한다)

출력:
    data/processed/ddi_data_real.csv

실행:
    python scripts/data_preprocessing.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from src.paths import DATA_PROCESSED_DIR, DATA_RAW_DIR
from src.state import UNDETERMINED_CT

NANODROP_RAW = DATA_RAW_DIR / "NanoDrop_raw.csv"
QPCR_RAW = DATA_RAW_DIR / "qPCR_Ct_raw.csv"
META_RAW = DATA_RAW_DIR / "samples_meta.csv"
OUTPUT_CSV = DATA_PROCESSED_DIR / "ddi_data_real.csv"


def _read_csv_or_none(path: Path):
    if not path.exists():
        print(f"[skip] {path.name} 없음 — 아직 이 원자료가 없다면 정상이다.")
        return None
    return pd.read_csv(path)


def build() -> pd.DataFrame:
    nanodrop = _read_csv_or_none(NANODROP_RAW)
    qpcr = _read_csv_or_none(QPCR_RAW)
    meta = _read_csv_or_none(META_RAW)

    if nanodrop is None or qpcr is None:
        raise SystemExit(
            "NanoDrop_raw.csv와 qPCR_Ct_raw.csv가 둘 다 있어야 전처리할 수 있다.\n"
            "총괄 앱의 '데이터 입력' 탭을 쓰고 있다면, 이 스크립트 대신 "
            "data/processed/samples_log.csv를 바로 학습에 써도 된다 "
            "(scripts/build_final_model.py는 두 소스 중 있는 쪽을 자동으로 쓴다)."
        )

    df = nanodrop.merge(qpcr, on="sample_id", how="outer", validate="one_to_one")
    if meta is not None:
        df = df.merge(meta, on="sample_id", how="left")

    # qPCR에서 미검출("Undetermined" 또는 빈 칸)이면 Ct=40으로 치환 (마스터 문서 아이디어 B)
    df["qc_flag"] = "ok"
    undetermined_mask = df["Ct_600"].isna() | (df["Ct_600"].astype(str).str.lower() == "undetermined")
    df.loc[undetermined_mask, "qc_flag"] = "undetermined"
    df["Ct_600"] = pd.to_numeric(df["Ct_600"], errors="coerce")
    df.loc[undetermined_mask, "Ct_600"] = UNDETERMINED_CT

    df["DDI"] = df["Ct_600"] - df["Ct_100"]

    return df


if __name__ == "__main__":
    df = build()
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"{len(df)}개 행 → {OUTPUT_CSV}")
    print(df["qc_flag"].value_counts())
