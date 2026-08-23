# 닭가슴살 DDI 연구 — R&E 총괄 대시보드

머신러닝 기반 DNA 붕괴 패턴을 활용한 식품 가공 이력 추적 모델 개발 (대구과학고 R&E)

Wet-Lab(실험)과 Dry-Lab(ML 파이프라인)을 하나의 저장소·하나의 앱에서 연동한다.
실험 담당 팀원은 **링크 하나**로 접속해 데이터를 입력하고 진행 상황을 확인하며,
Claude API 기반 "AI 감사관"이 입력값을 실시간으로 검토한다.

전체 연구 배경은 [`docs/research_master.md`](docs/research_master.md) 참고.

## 팀 구성

| 이름 | 역할 |
|---|---|
| 최준혁 | 총괄 · AI/ML |
| 실험 담당 3인 | Wet-Lab (열처리·추출·qPCR) |

자세한 역할·폴더 소유권은 [`docs/team_roles.md`](docs/team_roles.md).

## 폴더 구조

```
rne_organizer/
├── data/
│   ├── raw/            # 실험실 원자료 (수정 금지, 새 행만 추가)
│   └── processed/       # 전처리 결과물 + 앱이 쌓는 samples_log.csv
├── docs/                 # 연구계획서, 팀 가이드, 앱 사용법
├── models/               # 학습된 모델 (.pkl, git에는 안 올라감 — 스크립트로 재생성)
├── scripts/              # 데이터 전처리 · 합성 데이터 생성 · 모델 학습
├── src/                  # 총괄 앱(Streamlit) 소스
├── requirements.txt
└── .gitignore
```

## 실험 담당 팀원 — 여기부터 읽기

코드나 git을 몰라도 된다. **배포된 앱 링크만 열면 된다.**
사용법은 [`docs/app_guide.md`](docs/app_guide.md) 참고 (진행현황 확인, 데이터 입력, 예측 화면 사용법).

## 로컬에서 앱 실행하기 (최준혁 / 개발용)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

cp .env.example .env        # ANTHROPIC_API_KEY 채워넣기 (AI 감사관 기능용, 없어도 앱은 동작함)

streamlit run src/app.py
```

## 파이프라인 실행 순서

```bash
# 1. (실측 데이터가 있으면) raw → processed 변환
python scripts/data_preprocessing.py

# 2. (파이프라인 테스트용 가상 데이터가 필요하면)
python scripts/generate_synthetic_data.py

# 3. 최종 모델 학습 — 실측이 충분치 않으면 자동으로 합성 데이터로 대체하고 경고를 남긴다
python scripts/build_final_model.py
```

`build_final_model.py`는 학습에 쓴 데이터 출처와 당시 git 커밋 해시를
`models/model_metadata.json`에 함께 기록한다. 합성 데이터로 학습된 경우
`is_synthetic: true`가 남고, 앱 화면 상단에 경고 배너가 뜬다.

## 배포 (학생들이 링크로 접속하도록)

[Streamlit Community Cloud](https://streamlit.io/cloud)에 이 저장소를 연결하면 무료로 공개
링크가 생성된다 (노트북에서 별도 설치 없이 브라우저만 있으면 접속 가능).

1. share.streamlit.io에서 GitHub 계정으로 로그인 → 이 저장소 선택 → Main file path:
   `src/app.py`
2. **Settings → Secrets**에 `.streamlit/secrets.toml.example` 내용을 참고해 실제 값을 붙여넣는다
   (`ANTHROPIC_API_KEY` 등). 이 값은 GitHub에 올라가지 않고 Streamlit Cloud에만 저장된다.
3. 배포되면 생기는 `https://xxxx.streamlit.app` 링크를 팀 단톡방에 공유한다.

> Claude API 키가 아직 없어도 앱 자체는 정상 동작한다(AI 감사관 기능만 꺼진 채로 표시됨).

## 중요: 현재 상태

- 파이프라인은 작동하고 방법론은 검증됐지만(시뮬레이션 데이터 기준),
  **실제 온도 예측 모델은 아직 없다.** 9월 실측 qPCR 데이터가 들어가야 진짜 1차 모델이다.
- 지금 보이는 MAE·예측값은 전부 합성(가상) 데이터 기준이며, 앱이 그 사실을 배너로 표시한다.

자세한 배경은 [`docs/research_master.md`](docs/research_master.md) 16절 참고.

## Git 사용 규칙

`.pkl` 모델·API 키는 절대 커밋하지 않는다. 분석 스크립트는 실행 전에 커밋한다
(재현성 위기를 반복하지 않기 위한 규칙). 자세한 내용은 [`docs/git_workflow.md`](docs/git_workflow.md).
