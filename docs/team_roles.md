# 팀 구성과 폴더 규칙

## 팀 구성

| 이름 | 역할 | 주로 만지는 폴더 |
|---|---|---|
| 최준혁 | 총괄 · AI/ML | `scripts/`, `src/`, `models/`, `docs/` |
| 실험 담당 A | Wet-Lab (열처리·추출) | `data/raw/`, 총괄 앱 `데이터 입력` 탭 |
| 실험 담당 B | Wet-Lab (qPCR) | `data/raw/`, 총괄 앱 `데이터 입력` 탭 |
| 실험 담당 C | Wet-Lab (장비·시약 관리) | `data/raw/`, `docs/` (장비 현황) |

실험 담당 3명은 코드를 직접 건드릴 필요가 없다. **총괄 앱(웹 링크)에 접속해서 입력 폼만 쓰면
자동으로 `data/processed/samples_log.csv`에 기록**되도록 설계했다 (`docs/app_guide.md` 참고).

## 폴더별 소유권

- `data/raw/` — 실험 담당이 원자료를 넣는 곳. **한 번 커밋되면 수정 금지**, 새 행 추가만.
- `data/processed/` — 앱이 자동 생성하거나, `scripts/data_preprocessing.py`가 raw로부터 생성.
  손으로 편집하지 않는다.
- `docs/` — 계획서, 실험 가이드, 세특 자료. 팀 전원이 수정 가능하지만 되도록 PR로 올린다.
- `models/` — 학습된 모델(`.pkl`)이 저장되는 곳. **git에는 안 올라간다** (`.gitignore` 참고).
  누구든 `python scripts/build_final_model.py`를 실행하면 로컬에 재생성된다.
- `scripts/` — 재현 가능한 파이프라인 스크립트. 실행 즉시 커밋 (`docs/git_workflow.md` 참고).
- `src/` — 총괄 앱(Streamlit) 소스.

## 병렬 작업 시 충돌 방지

1. 실험 담당 3명은 **앱을 통해서만** 데이터를 넣는다. Excel이나 CSV를 로컬에서 따로 만들어
   나중에 합치지 않는다 — 합치는 과정에서 값이 미묘하게 바뀌는 사고(10.5757 vs 10.7214류)가
   또 발생할 수 있다.
2. 최준혁은 `scripts/`, `src/`를 브랜치 나눠서 작업하고 PR로 합친다.
3. `docs/research_master.md`는 "합의된 확정 사항"만 적는다. 아직 결정 안 된 것은
   PENDING으로 표시하고 이슈로 남긴다.
