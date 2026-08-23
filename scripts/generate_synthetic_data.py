"""노이즈 강건 시뮬레이션(합성) 데이터 생성기.

docs/research_master.md 11절 "노이즈 강건 ML 파이프라인"의 채널 분리 설계를 그대로 구현한다.
⚠️ 이 스크립트가 만드는 데이터는 전부 가짜(synthetic)다. 파이프라인 코드가 돌아가는지
확인하고 build_final_model.py를 미리 테스트해보기 위한 것이지, 연구 결과가 아니다.
실측 데이터가 들어오면 이 파일이 아니라 scripts/data_preprocessing.py가 만드는
data/processed/ddi_data_real.csv를 학습에 써야 한다.

실행:
    python scripts/generate_synthetic_data.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from src.paths import DEMO_SYNTHETIC_CSV

RNG_SEED = 42
EA_KJ_MOL = 130.0  # 아레니우스 활성화 에너지 (마스터 문서 3절)
R_GAS = 8.314e-3  # kJ/(mol·K)

TEMPS = [50, 60, 70, 75, 80, 90, 100]
TIMES = [15, 30, 60]
REPS = 3
MARINADES = {"soy": 6, "gochujang": 6}  # 그룹당 반복 수 (18개 = 2종 × 온도3 × 반복3, docs 11절)
MARINADE_TEMPS = [60, 80, 100]

CT_100_BASE = 18.0


def arrhenius_ct600_increase(temp_c: float, time_min: float, rng: np.random.Generator) -> float:
    """열 손상 채널: 온도가 높고 시간이 길수록 Ct_600이 아레니우스 식을 따라 증가."""
    t_kelvin = temp_c + 273.15
    k = np.exp(-EA_KJ_MOL / (R_GAS * t_kelvin)) * 1e18  # 스케일 상수는 임의 보정값
    increase = k * time_min * 0.0008
    return float(increase + rng.normal(0, 0.3))


def acid_damage(ph: float, rng: np.random.Generator) -> float:
    """산성 손상 채널: 고추장(pH 4.5~5)에서만, 중성(pH 7)과의 차이에 비례해 Ct_600에 추가."""
    return float(max(0.0, (7.0 - ph)) * 0.9 + rng.normal(0, 0.2))


def matrix_interference(marinade: str, rng: np.random.Generator) -> dict:
    """매트릭스 간섭 채널: conc 감소, purity_230 저하. DDI에는 영향 주지 않는다."""
    if marinade == "none":
        conc_penalty, purity230_penalty = 0.0, 0.0
    elif marinade == "soy":
        conc_penalty, purity230_penalty = 4.0, 0.25
    else:  # gochujang
        conc_penalty, purity230_penalty = 7.0, 0.45
    return {
        "conc_penalty": conc_penalty + rng.normal(0, 1.0),
        "purity230_penalty": purity230_penalty + rng.normal(0, 0.05),
    }


def make_row(sample_id, group, marinade, temp_c, time_min, rng: np.random.Generator) -> dict:
    ct_100 = CT_100_BASE + rng.normal(0, 0.3)
    ct600_increase = arrhenius_ct600_increase(temp_c, time_min, rng)

    ph = 7.0
    if marinade == "gochujang":
        ph = float(np.clip(rng.normal(4.7, 0.15), 4.0, 5.2))
        ct600_increase += acid_damage(ph, rng)
    elif marinade == "soy":
        ph = float(np.clip(rng.normal(6.2, 0.15), 5.5, 6.8))

    ct_600 = ct_100 + max(0.0, ct600_increase)

    mi = matrix_interference(marinade, rng)
    conc = float(max(2.0, 55.0 - mi["conc_penalty"]))
    purity_280 = float(np.clip(rng.normal(1.85, 0.05), 1.5, 2.1))
    purity_230 = float(np.clip(2.15 - mi["purity230_penalty"], 1.0, 2.4))

    qc_flag = "ok"
    if ct_600 - ct_100 > 18 and rng.random() < 0.5:
        ct_600 = np.nan
        qc_flag = "undetermined"
    elif rng.random() < 0.03:
        qc_flag = "outlier_suspect"
        ct_600 += rng.normal(0, 3.0)

    batch_effect = 1.0 + rng.normal(0, 0.05)  # 추출 날짜별 ±5% 계통 오차

    return {
        "sample_id": sample_id,
        "group": group,
        "marinade": marinade,
        "temp_c": temp_c,
        "time_min": time_min,
        "Ct_100": round(ct_100 * batch_effect, 3),
        "Ct_600": round(ct_600 * batch_effect, 3) if not np.isnan(ct_600) else np.nan,
        "DDI": round((ct_600 - ct_100), 3) if not np.isnan(ct_600) else np.nan,
        "DNA_conc": round(conc, 2),
        "DNA_purity_260280": round(purity_280, 3),
        "DNA_purity_260230": round(purity_230, 3),
        "marinade_pH": round(ph, 2),
        "qc_flag": qc_flag,
    }


def generate() -> pd.DataFrame:
    rng = np.random.default_rng(RNG_SEED)
    rows = []
    idx = 0

    for temp in TEMPS:
        for time_min in TIMES:
            for rep in range(1, REPS + 1):
                idx += 1
                sample_id = f"HT_{temp:03d}C_{time_min:02d}M_R{rep}"
                rows.append(make_row(sample_id, "heat", "none", temp, time_min, rng))

    for marinade, count in MARINADES.items():
        for temp in MARINADE_TEMPS:
            for rep in range(1, REPS + 1):
                idx += 1
                sample_id = f"{marinade.upper()}_{temp:03d}C_30M_R{rep}"
                rows.append(make_row(sample_id, "marinade", marinade, temp, 30, rng))

    for rep in range(1, 4):
        rows.append(make_row(f"CTRL_R{rep}", "control", "none", 25, 0, rng))

    df = pd.DataFrame(rows)
    df.loc[df["group"] == "control", ["Ct_600", "DDI"]] = [df["Ct_100"].iloc[0], 0.5]
    return df


if __name__ == "__main__":
    df = generate()
    DEMO_SYNTHETIC_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(DEMO_SYNTHETIC_CSV, index=False)
    print(f"[synthetic-data-warning] {len(df)}개 행의 가상(합성) 데이터를 생성했다: {DEMO_SYNTHETIC_CSV}")
    print("이 데이터는 파이프라인 테스트 전용이며 실제 연구 결과가 아니다.")
    print(df["qc_flag"].value_counts())
