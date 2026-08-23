# Git 사용 가이드 (팀용)

> 이 문서는 R&E 연구 문서에 없는 일반적인 소프트웨어 엔지니어링 지식이다.
> 실제 명령어는 팀 환경(Windows/PowerShell)에서 한 번씩 직접 검증해볼 것.

## 왜 이렇게까지 엄격하게 하는가

`docs/research_master.md` 13절의 재현성 위기(같은 조건인데 MAE가 10.5757 vs 10.7214로 갈렸던
사건) 원인 중 하나가 "분석에 쓴 원본 `.py`를 저장해두지 않아서, 나중에 설명만 보고 다시 짠 코드가
미묘하게 달랐던 것"이었다. 아래 규칙은 이걸 다시 겪지 않기 위한 최소한의 장치다.

## 기본 규칙

1. **분석/학습 스크립트는 실행하기 전에 커밋한다.** 코드를 고치고 → 커밋하고 → 실행한다
   (실행하고 나서 커밋하지 않는다). 이러면 "이 결과가 어떤 커밋의 코드로 나온 결과인지"가
   항상 명확해진다.
2. **커밋 메시지에 무엇을, 왜 바꿨는지 한 줄로 남긴다.** ("수정함", "업데이트" 금지)
3. **`main` 브랜치에 바로 커밋하지 않는다.** 작업은 `feature/이름-내용` 형태 브랜치에서 하고,
   완료되면 Pull Request로 합친다.
4. **`.pkl` 모델 파일, API 키, `.env`는 절대 커밋하지 않는다.** `.gitignore`에 이미 등록되어
   있지만, `git add -A`로 몰아서 올리기 전에 `git status`로 뭐가 올라가는지 한 번 확인한다.

## 처음 한 번만 하는 설정 (팀원 각자)

```powershell
git clone https://github.com/jundaleee/rne_organizer.git
cd rne_organizer
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # 이후 .env 파일에 실제 Claude API 키 입력
```

## 매번 작업할 때

```powershell
git checkout main
git pull origin main
git checkout -b feature/내이름-오늘작업내용

# ... 코드 수정 ...

git add 수정한파일1 수정한파일2   # git add . 대신 파일을 지정해서, 실수로 다른 게 딸려가지 않게
git commit -m "무엇을 왜 바꿨는지 한 줄"
git push -u origin feature/내이름-오늘작업내용
```

이후 GitHub에서 Pull Request를 열고, 최준혁(또는 팀원)이 확인한 뒤 `main`에 merge한다.

## 스크립트를 실행할 때 (재현성 규칙)

```powershell
git status          # 워킹 트리가 깨끗한지(커밋 안 된 변경이 없는지) 확인
git add scripts/build_final_model.py
git commit -m "build_final_model: XGBoost max_depth 4로 조정"
python scripts/build_final_model.py
```

`models/`에 저장되는 모델과 함께 `models/model_metadata.json`에 학습 당시 git 커밋 해시가
자동으로 기록된다 (`scripts/build_final_model.py` 참고). 나중에 "이 pkl이 어떤 코드로
만들어졌는지" 확인하고 싶으면 그 해시로 `git show`를 보면 된다.

## 충돌(conflict)이 났을 때

같은 파일(특히 `data/processed/samples_log.csv`)을 여러 명이 동시에 고치면 충돌이 날 수 있다.
이 파일은 원칙적으로 **사람이 직접 git으로 고치지 않고 총괄 앱을 통해서만 값을 추가**하도록
설계했다 (`docs/app_guide.md`). 그래도 충돌이 나면 최준혁에게 먼저 알리고 임의로
`git checkout --theirs`/`--ours`로 덮어쓰지 않는다 — 실험 데이터는 한쪽을 버리면 안 되는
데이터이기 때문이다.
