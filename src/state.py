"""사이드바 nav와 세션 상태 정의.

기존 dshs-organizer(바닐라 JS SPA)의 패턴을 그대로 옮긴 것:
탭 하나 = {view, label, icon, color} 객체 하나, state.view 문자열 하나로 라우팅.
새 탭을 추가할 땐 NAV_ITEMS에 한 줄 추가하고 app.py의 분기에 한 줄만 추가하면 된다.
"""

import streamlit as st

NAV_ITEMS = [
    {"view": "home", "label": "진행현황", "icon": "🏠", "color": "#0A84FF"},
    {"view": "entry", "label": "데이터 입력", "icon": "🧪", "color": "#30D158"},
    {"view": "predict", "label": "예측 (Dry-Lab)", "icon": "🔮", "color": "#BF5AF2"},
    {"view": "docs", "label": "문서", "icon": "📄", "color": "#5E5CE6"},
    {"view": "team", "label": "팀 활동", "icon": "👥", "color": "#FF375F"},
]

# 실험 설계(docs/research_master.md 8절) 목표 시료 수.
# ⚠️ 원문 자체에 126 vs 63(7수준×3수준×반복3) 불일치가 있어, 팀에서 반복 횟수를
#    확정하면 아래 숫자를 맞춰서 고칠 것.
SAMPLE_PLAN = {
    "열처리군": 126,
    "양념 교란군": 27,
    "대조군·검증군": 9,
}
TOTAL_TARGET = sum(SAMPLE_PLAN.values())

MARINADE_OPTIONS = ["없음(무양념)", "간장", "고추장"]
MARINADE_KEY = {"없음(무양념)": "none", "간장": "soy", "고추장": "gochujang"}

LOG_COLUMNS = [
    "sample_id", "date", "member", "group", "marinade",
    "temp_c", "time_min",
    "Ct_100", "Ct_600", "DDI",
    "DNA_conc", "DNA_purity_260280", "DNA_purity_260230",
    "marinade_pH", "qc_flag", "auditor_note", "entered_at",
]

# qPCR에서 Undetermined(미검출)일 때 대입하는 상수 (마스터 문서 아이디어 B)
UNDETERMINED_CT = 40.0


def init_state():
    if "view" not in st.session_state:
        st.session_state.view = "home"


def go_view(view: str):
    st.session_state.view = view
