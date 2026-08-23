"""앱 안 '⚙️ 설정' 화면에서 입력한 API 키 등을 저장하는 곳.

우선순위: 이 파일(.local_secrets.json, git에는 안 올라감) > 환경변수 > st.secrets.
'설정' 화면에서 입력한 값이 최우선이라, Streamlit Cloud의 Secrets 패널을 따로
건드리지 않아도 앱 안에서 바로 키를 넣고 쓸 수 있다.

⚠️ 이 앱에는 로그인이 없다. 링크를 아는 사람은 누구나 '설정' 화면에서 키를
새로 입력(덮어쓰기)할 수 있다. 팀 내부에서만 링크를 공유할 것.
"""

import json
import os
import stat

import streamlit as st

from paths import REPO_ROOT

RUNTIME_SECRETS_PATH = REPO_ROOT / ".local_secrets.json"


def _load_file() -> dict:
    if not RUNTIME_SECRETS_PATH.exists():
        return {}
    try:
        with open(RUNTIME_SECRETS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save(values: dict):
    """값이 있는(빈 문자열이 아닌) 키만 덮어써서 저장한다."""
    current = _load_file()
    for k, v in values.items():
        if v:
            current[k] = v
    with open(RUNTIME_SECRETS_PATH, "w", encoding="utf-8") as f:
        json.dump(current, f)
    try:
        os.chmod(RUNTIME_SECRETS_PATH, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass


def clear(key: str):
    current = _load_file()
    if key in current:
        del current[key]
        with open(RUNTIME_SECRETS_PATH, "w", encoding="utf-8") as f:
            json.dump(current, f)


def get(key: str, default=None):
    current = _load_file()
    if current.get(key):
        return current[key]
    if os.environ.get(key):
        return os.environ.get(key)
    try:
        value = st.secrets.get(key)
        if value:
            return value
    except Exception:
        pass
    return default


def is_set(key: str) -> bool:
    return bool(get(key))
