"""GitHub REST API로 데이터 파일을 직접 커밋한다 (로컬 git 자격증명 불필요).

Streamlit Cloud 컨테이너는 저장소를 읽기 전용으로 clone해오기 때문에 로컬
`git push`가 되지 않는다. 대신 Contents API로 파일을 업데이트하면 별도 git
설정 없이도, '⚙️ 설정'에서 입력한 Personal Access Token만으로 커밋이 생긴다.

토큰이 설정되지 않았으면 이 모듈의 모든 함수는 실패를 반환하고, 앱의 나머지
기능(로컬 CSV 저장)에는 영향을 주지 않는다 — GitHub 백업은 어디까지나 선택 기능이다.
"""

import base64
from pathlib import Path

import requests

import runtime_config

API_BASE = "https://api.github.com"


def is_configured() -> bool:
    return runtime_config.is_set("GITHUB_TOKEN") and bool(_repo())


def _repo() -> str:
    return runtime_config.get("GITHUB_REPO", "") or ""


def _branch() -> str:
    return runtime_config.get("GITHUB_BRANCH", "main") or "main"


def _headers():
    return {
        "Authorization": f"Bearer {runtime_config.get('GITHUB_TOKEN')}",
        "Accept": "application/vnd.github+json",
    }


def push_file(path_in_repo: str, local_path: Path, message: str):
    """local_path의 현재 내용으로 GitHub 저장소의 path_in_repo 파일을 업데이트(또는 생성)한다.
    반환: (성공 여부, 짧은 커밋 해시 또는 에러 메시지)"""
    if not is_configured():
        return False, "GitHub 연동이 설정되지 않음"

    url = f"{API_BASE}/repos/{_repo()}/contents/{path_in_repo}"

    try:
        content_b64 = base64.b64encode(local_path.read_bytes()).decode("ascii")

        sha = None
        get_resp = requests.get(url, headers=_headers(), params={"ref": _branch()}, timeout=15)
        if get_resp.status_code == 200:
            sha = get_resp.json().get("sha")

        payload = {"message": message, "content": content_b64, "branch": _branch()}
        if sha:
            payload["sha"] = sha

        put_resp = requests.put(url, headers=_headers(), json=payload, timeout=15)
        if put_resp.status_code in (200, 201):
            commit_sha = put_resp.json().get("commit", {}).get("sha", "")
            return True, (commit_sha[:7] if commit_sha else "ok")
        return False, f"GitHub API 오류 {put_resp.status_code}: {put_resp.text[:200]}"
    except Exception as e:
        return False, str(e)


def list_recent_commits(path_in_repo: str = None, n: int = 15):
    if not is_configured():
        return []
    url = f"{API_BASE}/repos/{_repo()}/commits"
    params = {"sha": _branch(), "per_page": n}
    if path_in_repo:
        params["path"] = path_in_repo
    try:
        resp = requests.get(url, headers=_headers(), params=params, timeout=15)
        if resp.status_code != 200:
            return []
        return [
            {
                "hash": item["sha"][:7],
                "date": item["commit"]["author"]["date"][:10],
                "message": item["commit"]["message"].splitlines()[0],
            }
            for item in resp.json()
        ]
    except Exception:
        return []
