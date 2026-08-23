"""R&E 총괄 대시보드 — Streamlit 앱.

기존 dshs-organizer(바닐라 JS SPA)의 사이드바 nav 패턴(NAV_ITEMS 배열 + state.view
문자열 하나로 라우팅, section 6의 pill 서브탭 패턴)을 Streamlit으로 옮긴 것.
탭을 늘릴 땐 state.py의 NAV_ITEMS에 항목 하나 추가하고, 아래 main()의 분기에
한 줄만 추가하면 된다.

실행:
    streamlit run src/app.py
"""

import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import streamlit as st

import auditor
import github_sync
import local_log
import paths
import predict as predict_mod
import runtime_config
from state import (
    LOG_COLUMNS,
    MARINADE_KEY,
    MARINADE_OPTIONS,
    NAV_ITEMS,
    SAMPLE_PLAN,
    TOTAL_TARGET,
    UNDETERMINED_CT,
    go_view,
    init_state,
)


# ---------- 공용 유틸 ----------

def load_log() -> pd.DataFrame:
    if not paths.SAMPLES_LOG_CSV.exists() or paths.SAMPLES_LOG_CSV.stat().st_size == 0:
        return pd.DataFrame(columns=LOG_COLUMNS)
    return pd.read_csv(paths.SAMPLES_LOG_CSV)


def load_training_df_for_range_check(metadata: dict):
    source = metadata.get("data_source")
    if not source:
        return None
    p = paths.REPO_ROOT / source
    if not p.exists():
        return None
    try:
        return pd.read_csv(p)
    except Exception:
        return None


def render_synthetic_banner():
    metadata = predict_mod.load_metadata(paths.MODEL_METADATA_JSON)
    if metadata.get("is_synthetic"):
        st.warning(
            "⚠️ 현재 예측 모델은 **시뮬레이션(합성) 데이터**로 학습되었습니다. "
            "여기서 보이는 MAE·예측값은 연구 성과가 아니라 파이프라인 검증용입니다. "
            "실측 데이터가 모이면 `python scripts/build_final_model.py`를 다시 실행하세요."
        )


# ---------- 사이드바 ----------

def render_sidebar():
    st.sidebar.markdown("### 🧬 닭가슴살 DDI 연구")
    st.sidebar.caption("R&E 총괄 대시보드")
    for item in NAV_ITEMS:
        active = st.session_state.view == item["view"]
        if st.sidebar.button(
            f"{item['icon']}  {item['label']}",
            key=f"nav_{item['view']}",
            use_container_width=True,
            type="primary" if active else "secondary",
        ):
            go_view(item["view"])
            st.rerun()

    st.sidebar.divider()
    settings_active = st.session_state.view == "settings"
    if st.sidebar.button(
        "⚙️  설정",
        key="nav_settings",
        use_container_width=True,
        type="primary" if settings_active else "secondary",
    ):
        go_view("settings")
        st.rerun()

    if auditor.is_configured():
        st.sidebar.success("🔎 AI 감사관 켜짐")
    else:
        st.sidebar.caption("🔎 AI 감사관 꺼짐")
    if github_sync.is_configured():
        st.sidebar.success("🔗 GitHub 백업 켜짐")
    else:
        st.sidebar.caption("🔗 GitHub 백업 꺼짐")


# ---------- 홈 ----------

def render_home():
    render_synthetic_banner()
    st.title("🏠 진행현황")

    log_df = load_log()
    total_done = len(log_df)

    st.subheader(f"전체 시료 {total_done} / {TOTAL_TARGET}")
    st.progress(min(total_done / TOTAL_TARGET, 1.0) if TOTAL_TARGET else 0.0)

    cols = st.columns(len(SAMPLE_PLAN))
    for col, (group, target) in zip(cols, SAMPLE_PLAN.items()):
        done = int((log_df["group"] == group).sum()) if not log_df.empty else 0
        with col:
            st.metric(group, f"{done} / {target}")
            st.progress(min(done / target, 1.0) if target else 0.0)

    st.divider()
    st.subheader("최근 입력 기록")
    if log_df.empty:
        st.info("아직 입력된 데이터가 없다. 왼쪽 '데이터 입력' 탭에서 첫 시료를 등록해보자.")
    else:
        recent = log_df.sort_values("entered_at", ascending=False).head(15)
        st.dataframe(recent, use_container_width=True, hide_index=True)


# ---------- 데이터 입력 ----------

def render_saturation_checker():
    st.subheader("🌡️ 미검출(Undetermined) 비율 체크 · Plan B 판정")
    st.caption(
        "한 그룹 전체에서 Ct_600 미검출이 몇 개나 나왔는지 입력하면, "
        "예비 프라이머(200bp/400bp) 카드를 가동할 시점인지 AI 감사관이 판단해준다."
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        group_label = st.text_input("그룹 설명", value="100°C 처리군", key="sat_group")
    with c2:
        total = st.number_input("전체 시료 수", min_value=1, value=9, step=1, key="sat_total")
    with c3:
        undetermined_n = st.number_input("미검출 개수", min_value=0, value=8, step=1, key="sat_undet")

    if st.button("AI 감사관에게 판정 요청", key="sat_button"):
        if not auditor.is_configured():
            st.warning("Claude API 키가 설정되지 않아 이 기능을 쓸 수 없다.")
        else:
            with st.spinner("판정 중..."):
                result = auditor.audit_ct_saturation(group_label, total, undetermined_n)
            st.info(result)


def render_entry():
    st.title("🧪 데이터 입력")
    st.caption("측정한 NanoDrop·qPCR 수치를 입력하면 DDI가 자동 계산되고 AI 감사관이 즉시 판정한다.")

    if not auditor.is_configured():
        st.warning("Claude API 키가 설정되지 않아 AI 감사관 기능이 꺼져 있다. 데이터 입력 자체는 정상 동작한다.")

    with st.form("entry_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            sample_id = st.text_input("시료 ID *", placeholder="예: HT_090C_30M_R2")
            member = st.text_input("담당자 *")
            entry_date = st.date_input("측정일", value=date.today())
        with c2:
            group = st.selectbox("그룹 *", list(SAMPLE_PLAN.keys()))
            marinade_label = st.selectbox("양념", MARINADE_OPTIONS)
            temp_c = st.number_input("처리 온도 (°C)", min_value=0.0, max_value=130.0, value=75.0, step=1.0)
        with c3:
            time_min = st.number_input("처리 시간 (분)", min_value=0.0, max_value=180.0, value=30.0, step=1.0)
            marinade_pH = st.number_input("marinade pH (무양념이면 7.0)", min_value=0.0, max_value=14.0, value=7.0, step=0.1)

        st.markdown("**NanoDrop**")
        n1, n2, n3 = st.columns(3)
        with n1:
            conc = st.number_input("DNA 농도 (ng/uL) *", min_value=0.0, value=50.0, step=0.1)
        with n2:
            purity_280 = st.number_input("A260/280 *", min_value=0.0, value=1.85, step=0.01)
        with n3:
            purity_230 = st.number_input("A260/230 *", min_value=0.0, value=2.1, step=0.01)

        st.markdown("**qPCR**")
        q1, q2, q3 = st.columns(3)
        with q1:
            ct_100 = st.number_input("Ct_100 *", min_value=0.0, max_value=45.0, value=18.0, step=0.01)
        with q2:
            undetermined = st.checkbox("Ct_600 미검출(Undetermined)")
        with q3:
            ct_600 = st.number_input(
                "Ct_600", min_value=0.0, max_value=45.0, value=18.5, step=0.01, disabled=undetermined
            )

        submitted = st.form_submit_button("제출", use_container_width=True)

    if submitted:
        if not sample_id or not member:
            st.error("시료 ID와 담당자는 필수다.")
            return

        actual_ct600 = UNDETERMINED_CT if undetermined else ct_600
        ddi = round(actual_ct600 - ct_100, 3)
        qc_flag = "undetermined" if undetermined else "ok"

        row = {
            "sample_id": sample_id,
            "date": str(entry_date),
            "member": member,
            "group": group,
            "marinade": MARINADE_KEY[marinade_label],
            "temp_c": temp_c,
            "time_min": time_min,
            "Ct_100": ct_100,
            "Ct_600": actual_ct600,
            "DDI": ddi,
            "DNA_conc": conc,
            "DNA_purity_260280": purity_280,
            "DNA_purity_260230": purity_230,
            "marinade_pH": marinade_pH,
            "qc_flag": qc_flag,
            "auditor_note": "",
            "entered_at": datetime.now().isoformat(timespec="seconds"),
        }

        auditor_note = None
        if auditor.is_configured():
            with st.spinner("AI 감사관이 확인하는 중..."):
                auditor_note = auditor.audit_nanodrop(sample_id, marinade_label, conc, purity_280, purity_230)
            if auditor_note:
                row["auditor_note"] = auditor_note

        local_log.append_row(paths.SAMPLES_LOG_CSV, LOG_COLUMNS, row)

        backup_note = None
        if github_sync.is_configured():
            ok, info = github_sync.push_file(
                "data/processed/samples_log.csv",
                paths.SAMPLES_LOG_CSV,
                f"data: {sample_id} 입력 ({member})",
            )
            backup_note = f"GitHub 백업 완료 (commit {info})" if ok else f"GitHub 백업 실패: {info}"

        msg = f"{sample_id} 저장 완료 (DDI = {ddi})"
        st.success(msg)
        if backup_note:
            (st.caption if backup_note.startswith("GitHub 백업 완료") else st.warning)(backup_note)
        if auditor_note:
            st.info(f"🔎 AI 감사관: {auditor_note}")

    st.divider()
    render_saturation_checker()


# ---------- 예측 (Dry-Lab) ----------

def render_predict():
    render_synthetic_banner()
    st.title("🔮 예측 (Dry-Lab)")

    model = predict_mod.load_model(paths.MODEL_PKL)
    metadata = predict_mod.load_metadata(paths.MODEL_METADATA_JSON)

    if model is None:
        st.warning("아직 학습된 모델이 없다. 터미널에서 `python scripts/build_final_model.py`를 먼저 실행할 것.")
        return

    st.caption(
        f"데이터 출처: `{metadata.get('data_source', '?')}` · "
        f"학습 시각: {metadata.get('trained_at', '?')} · "
        f"git {metadata.get('git_commit', '?')} · "
        f"샘플 수: {metadata.get('n_samples', '?')}"
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        ddi = st.number_input("DDI", value=1.0, step=0.01)
        ct_100 = st.number_input("Ct_100", value=18.0, step=0.01)
    with c2:
        conc = st.number_input("DNA_conc", value=50.0, step=0.1)
        purity_280 = st.number_input("DNA_purity_260280", value=1.85, step=0.01)
    with c3:
        purity_230 = st.number_input("DNA_purity_260230", value=2.1, step=0.01)
        marinade_pH = st.number_input("marinade_pH", value=7.0, step=0.1)

    if st.button("예측하기", type="primary"):
        inputs = {
            "DDI": ddi,
            "Ct_100": ct_100,
            "DNA_conc": conc,
            "DNA_purity_260280": purity_280,
            "DNA_purity_260230": purity_230,
            "marinade_pH": marinade_pH,
        }
        pred = predict_mod.predict_temperature(model, inputs)
        st.metric("예측 가공 온도", f"{pred:.1f} °C")

        train_df = load_training_df_for_range_check(metadata)
        if train_df is not None:
            flags = predict_mod.range_check(train_df, inputs)
            out_of_range = [f for f, v in flags.items() if not v["in_range"]]
            if out_of_range:
                st.warning(
                    f"⚠️ 학습 데이터 범위를 벗어난 입력값: {', '.join(out_of_range)} — "
                    "외삽(extrapolation)이라 이 예측은 신뢰하기 어렵다."
                )
            else:
                st.caption("모든 입력값이 학습 데이터 범위 안에 있다.")


# ---------- 문서 ----------

def render_docs():
    st.title("📄 문서")
    if not paths.DOCS_DIR.exists():
        st.info("docs 폴더가 없다.")
        return

    md_files = sorted(paths.DOCS_DIR.glob("*.md"))
    if not md_files:
        st.info("문서가 아직 없다.")
        return

    names = [f.stem for f in md_files]
    choice = st.selectbox("문서 선택", names)
    chosen = paths.DOCS_DIR / f"{choice}.md"
    text = chosen.read_text(encoding="utf-8")

    st.download_button("다운로드", text, file_name=chosen.name, mime="text/markdown")
    st.divider()
    st.markdown(text)


# ---------- 팀 활동 ----------

def render_debug_helper():
    with st.expander("🔧 디버깅 도우미 — 에러 로그·코드에서 통계적 함정 확인"):
        if not auditor.is_configured():
            st.warning("Claude API 키가 설정되지 않아 이 기능을 쓸 수 없다.")
            return
        error_log = st.text_area("에러 로그 / 이상해 보이는 결과", height=120, key="dbg_error")
        code_snippet = st.text_area("관련 코드", height=160, key="dbg_code")
        if st.button("감사관에게 물어보기", key="dbg_button"):
            if not error_log and not code_snippet:
                st.error("에러 로그나 코드 중 하나는 입력해야 한다.")
            else:
                with st.spinner("분석 중..."):
                    result = auditor.debug_with_context(error_log, code_snippet)
                st.markdown(result)


def render_team():
    st.title("👥 팀 활동")

    log_df = load_log()
    if log_df.empty:
        st.info("아직 활동 기록이 없다.")
    else:
        counts = log_df.groupby("member").size().reset_index(name="입력 개수")
        st.dataframe(counts, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("최근 GitHub 백업 기록")
    if github_sync.is_configured():
        commits = github_sync.list_recent_commits("data/processed/samples_log.csv", n=15)
        if commits:
            st.dataframe(pd.DataFrame(commits), use_container_width=True, hide_index=True)
        else:
            st.caption("아직 백업 기록이 없다.")
    else:
        st.caption("GitHub 연동이 설정되지 않았다. '⚙️ 설정'에서 켤 수 있다 (선택 사항, 없어도 앱은 정상 동작).")

    st.divider()
    render_debug_helper()


# ---------- 설정 ----------

def render_settings():
    st.title("⚙️ 설정")
    st.caption(
        "여기서 저장한 값은 이 앱을 쓰는 팀원 전체가 공유해서 쓴다. "
        "⚠️ 이 앱엔 로그인이 없어서 링크를 아는 사람은 누구나 이 값을 바꿀 수 있다 — 팀 내부에서만 링크를 공유할 것."
    )

    st.subheader("Claude API 키")
    st.caption("AI 감사관(데이터 무결성 판정, 디버깅 도우미) 기능에 필요하다. console.anthropic.com 에서 발급.")
    st.write("✅ 설정됨" if auditor.is_configured() else "❌ 미설정 — AI 감사관 기능이 꺼져 있다")
    c1, c2 = st.columns([3, 1])
    with c1:
        new_claude_key = st.text_input("Claude API Key 입력/변경", type="password", key="settings_claude_key")
    with c2:
        st.write("")
        st.write("")
        if st.button("삭제", key="clear_claude_key", use_container_width=True):
            runtime_config.clear("ANTHROPIC_API_KEY")
            st.rerun()
    if st.button("Claude API 키 저장", type="primary"):
        if new_claude_key:
            runtime_config.save({"ANTHROPIC_API_KEY": new_claude_key})
            st.success("저장 완료.")
            st.rerun()
        else:
            st.error("빈 값은 저장할 수 없다.")

    st.divider()
    st.subheader("GitHub 자동 백업 (선택)")
    st.caption(
        "설정하면 데이터를 입력할 때마다 GitHub 저장소에도 자동으로 커밋된다. "
        "없어도 앱은 정상 동작하지만, 앱이 재배포되면 그 사이 입력한 데이터가 사라질 수 있다."
    )
    st.write("✅ 설정됨" if github_sync.is_configured() else "❌ 미설정")

    repo_value = st.text_input(
        "GitHub 저장소 (owner/repo)", value=runtime_config.get("GITHUB_REPO", "jundaleee/rne_organizer") or ""
    )
    branch_value = st.text_input("브랜치", value=runtime_config.get("GITHUB_BRANCH", "main") or "")
    c3, c4 = st.columns([3, 1])
    with c3:
        new_token = st.text_input(
            "GitHub Personal Access Token 입력/변경",
            type="password",
            key="settings_gh_token",
            help="github.com/settings/tokens 에서 'repo' 권한(또는 이 저장소에 대한 Contents 읽기/쓰기 권한)으로 발급",
        )
    with c4:
        st.write("")
        st.write("")
        if st.button("삭제", key="clear_gh_token", use_container_width=True):
            runtime_config.clear("GITHUB_TOKEN")
            st.rerun()

    if st.button("GitHub 연동 저장", type="primary"):
        values = {"GITHUB_REPO": repo_value, "GITHUB_BRANCH": branch_value}
        if new_token:
            values["GITHUB_TOKEN"] = new_token
        runtime_config.save(values)
        st.success("저장 완료.")
        st.rerun()


# ---------- 라우터 ----------

def main():
    st.set_page_config(page_title="R&E 총괄 대시보드", page_icon="🧬", layout="wide")
    init_state()
    render_sidebar()

    view = st.session_state.view
    if view == "home":
        render_home()
    elif view == "entry":
        render_entry()
    elif view == "predict":
        render_predict()
    elif view == "docs":
        render_docs()
    elif view == "team":
        render_team()
    elif view == "settings":
        render_settings()


if __name__ == "__main__":
    main()
