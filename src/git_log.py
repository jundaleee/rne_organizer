"""데이터 입력 로그 기록 + (선택) 실행 즉시 자동 커밋.

마스터 문서의 "실행 즉시 git commit" 규칙을 데이터 입력에도 적용한 것.
자동 커밋은 어디까지나 best-effort다: 로컬에서 앱을 돌리거나, git push 권한이 있는
환경에서만 조용히 동작하고, Streamlit Community Cloud처럼 push 권한이 없는 배포
환경에서는 실패해도 앱 동작에 영향을 주지 않는다 (CSV 기록 자체는 항상 성공한다).
"""

import csv
import subprocess
from pathlib import Path


def append_row(csv_path: Path, columns: list, row: dict):
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not csv_path.exists() or csv_path.stat().st_size == 0
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        if is_new:
            writer.writeheader()
        writer.writerow({c: row.get(c, "") for c in columns})


def try_git_commit(repo_root: Path, paths: list, message: str):
    """성공하면 커밋 해시(str)를, 실패하면(권한 없음/git 미설치 등) None을 반환한다."""
    try:
        subprocess.run(
            ["git", "add", *[str(p) for p in paths]],
            cwd=repo_root, check=True, capture_output=True, timeout=15,
        )
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=repo_root, check=True, capture_output=True, timeout=15,
        )
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_root, check=True, capture_output=True, text=True, timeout=15,
        )
        commit_hash = result.stdout.strip()
        subprocess.run(
            ["git", "push"], cwd=repo_root, check=False, capture_output=True, timeout=30,
        )
        return commit_hash
    except Exception:
        return None


def recent_commits(repo_root: Path, n: int = 10):
    try:
        result = subprocess.run(
            ["git", "log", f"-{n}", "--pretty=format:%h|%ad|%s", "--date=short"],
            cwd=repo_root, check=True, capture_output=True, text=True, timeout=15,
        )
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        commits = []
        for line in lines:
            parts = line.split("|", 2)
            if len(parts) == 3:
                commits.append({"hash": parts[0], "date": parts[1], "message": parts[2]})
        return commits
    except Exception:
        return []
