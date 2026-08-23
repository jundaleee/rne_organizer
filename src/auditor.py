"""Claude API 기반 'AI 감사관'.

브레인스토밍 아이디어 3종을 그대로 구현한다:
  A. 실시간 데이터 무결성 감시관 (NanoDrop/qPCR 입력값 판정)
  B. 600bp 미검출 예외 가이드 + Plan B(예비 프라이머) 가동 판정
  C. 디버깅/통계 검정 반증 도구

API 키가 설정되지 않았으면 모든 함수가 None을 반환한다 — 앱의 나머지 기능은
Claude API 없이도 정상 동작해야 하므로(키가 없다고 데이터 입력이 막히면 안 됨),
호출부에서 None을 "감사관 기능 꺼짐"으로 처리한다.
"""

import os

import streamlit as st

MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = """당신은 고등학생 R&E 연구팀의 '데이터 무결성 감사관'이다.
연구 주제: 닭가슴살 DNA 붕괴 패턴(DDI = Ct(600bp) - Ct(100bp))으로 가공 온도를 역추적하는 모델.
실험 담당 학생(생물학 비전공)이 입력한 NanoDrop/qPCR 수치를 보고 짧게 판정한다.

원칙:
- 확신 없는 판단은 절대 단정하지 말고 "재측정 권장" 수준으로만 말한다.
- 형식적으로 통과시키지 말고, 이상해 보이면 이상하다고 솔직히 말한다.
- 고등학생이 이해할 수 있는 쉬운 말로 4문장 이내로 답한다.
- 반드시 아래 형식을 지킨다:
[판정: 정상/의심/재측정 권장] 한 줄 이유. 권장 조치 한 줄.
"""


def _get_client():
    try:
        import anthropic
    except ImportError:
        return None

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets.get("ANTHROPIC_API_KEY")
        except Exception:
            api_key = None
    if not api_key:
        return None

    return anthropic.Anthropic(api_key=api_key)


def is_configured() -> bool:
    return _get_client() is not None


def _ask(user_msg: str, max_tokens: int = 300):
    client = _get_client()
    if client is None:
        return None
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        return resp.content[0].text
    except Exception as e:
        return f"[감사관 호출 실패: {e}]"


def audit_nanodrop(sample_id, marinade, conc, purity_260280, purity_260230):
    """아이디어 A: NanoDrop 값이 매트릭스 간섭(잔류 염분/당분)이나 오염을 의심할 수준인지 판정."""
    user_msg = (
        f"시료 {sample_id} (양념: {marinade})의 NanoDrop 측정값:\n"
        f"- DNA 농도: {conc} ng/uL\n"
        f"- A260/280: {purity_260280}\n"
        f"- A260/230: {purity_260230}\n\n"
        "일반적으로 A260/280은 1.8 전후, A260/230은 2.0~2.2 전후가 순수한 DNA로 여겨진다. "
        "이 수치가 정상 범위인지, 매트릭스 간섭(잔류 염분/당분)이나 단백질 오염이 의심되는지 판정해줘."
    )
    return _ask(user_msg)


def audit_ct_saturation(group_label, total, undetermined_count):
    """아이디어 B: 미검출 비율이 높아 데이터 포화가 우려되는지, Plan B(예비 프라이머) 가동 시점인지 판정."""
    user_msg = (
        f"{group_label} 처리군 {total}개 중 {undetermined_count}개에서 Ct_600(600bp 앰플리콘)이 "
        "미검출(Undetermined)로 나왔다. 이 정도 미검출 비율이면 데이터 클리핑(포화)으로 처리 시간 간 "
        "역추적 성능이 떨어지는지, 지금 200bp/400bp 예비 프라이머(Plan B)를 가동해야 하는지 판단해줘."
    )
    return _ask(user_msg)


def debug_with_context(error_log: str, code_snippet: str):
    """아이디어 C: 에러 로그 + 코드에서 numpy NaN 함정, 다중공선성 등 통계적 함정을 짚어준다."""
    user_msg = (
        "아래 에러 로그와 코드에서 numpy NaN 비교 함정(array_equal의 equal_nan 기본값 문제), "
        "다중공선성, 또는 다른 통계적/재현성 함정이 있는지 짚어줘. "
        "확실하지 않으면 확실하지 않다고 말하고, 다음에 확인해볼 것을 제안해줘.\n\n"
        f"[에러 로그]\n{error_log}\n\n[코드]\n{code_snippet}"
    )
    return _ask(user_msg, max_tokens=500)
