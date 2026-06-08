"""Thesis Helper — 국제통상 졸업논문 작성 지원 도구 (동국대 양식).

실행:  streamlit run app.py

원칙: 표절·AI탐지 '우회' 도구가 아니라, 정공법으로 원본성을 높이는 도구.
도구 = 골격·자료·단락초안·인용 / 사용자 = 모든 본문 최종 문장 + 마무리.
"""
from __future__ import annotations

import streamlit as st

from core import llm
from core import project as P
from modules import (
    m1_topic, m2_sources, m3_outline, m4_data, m5_drafter, m6_check, m7_export,
)

st.set_page_config(page_title="졸업논문 작성 도우미", page_icon="🎓", layout="wide")

MODULES = {
    "① 주제 발굴": m1_topic,
    "② 자료·인용관리": m2_sources,
    "③ 골격 빌더": m3_outline,
    "④ 데이터 분석": m4_data,
    "⑤ 단락 작성소": m5_drafter,
    "⑥ 자가 점검": m6_check,
    "⑦ 내보내기": m7_export,
}


def get_cfg() -> llm.LLMConfig:
    s = st.session_state
    return llm.LLMConfig(
        backend=s.get("llm_backend", "template"),
        api_key=s.get("llm_key", ""),
        model=s.get("llm_model", ""),
        base_url=s.get("llm_base", ""),
    )


def sidebar_project():
    st.sidebar.title("🎓 졸업논문 도우미")

    # --- 접속 코드 (간단한 프로젝트 분리) ---
    code = st.sidebar.text_input(
        "접속 코드", value=st.session_state.get("access_code", ""), type="password",
        help="본인만 아는 코드를 정하세요. 같은 코드를 쓰는 사람끼리만 프로젝트가 공유됩니다(진짜 로그인은 아님).",
    )
    st.session_state.access_code = code
    space = P.space_id(code)
    if not code:
        st.sidebar.warning("접속 코드를 입력해야 프로젝트가 본인 공간에 저장됩니다.")

    # 코드가 바뀌면 현재 프로젝트 비우기
    if st.session_state.get("_space") != space:
        st.session_state._space = space
        st.session_state.pop("project", None)

    # --- 프로젝트 선택/생성 ---
    existing = P.list_projects(space)
    mode = st.sidebar.radio("프로젝트", ["기존 열기", "새로 만들기"], horizontal=True)
    if mode == "새로 만들기":
        name = st.sidebar.text_input("새 프로젝트 이름", value="my-thesis")
        if st.sidebar.button("생성"):
            st.session_state.project = P.new_project(name, space)
            st.rerun()
    else:
        if existing:
            chosen = st.sidebar.selectbox("프로젝트 선택", existing)
            if st.sidebar.button("열기"):
                st.session_state.project = P.load(chosen, space)
                st.rerun()
        else:
            st.sidebar.info("이 코드로 저장된 프로젝트가 없습니다. '새로 만들기'를 선택하세요.")

    if "project" not in st.session_state:
        st.session_state.project = P.new_project("my-thesis", space)

    st.sidebar.caption(f"현재: **{st.session_state.project['name']}**")
    st.sidebar.divider()

    # --- LLM 백엔드 (교체 가능) ---
    st.sidebar.subheader("LLM 백엔드 (선택)")
    st.session_state.llm_backend = st.sidebar.selectbox(
        "백엔드", llm.BACKENDS,
        index=llm.BACKENDS.index(st.session_state.get("llm_backend", "template")),
        help="template = 키 없이 동작(기본). 키는 세션에만 보관, 저장 안 됨.",
    )
    be = st.session_state.llm_backend
    if be != "template":
        d = llm.DEFAULTS.get(be, {})
        if be != "local":
            st.session_state.llm_key = st.sidebar.text_input(
                "API Key", type="password", value=st.session_state.get("llm_key", ""))
        st.session_state.llm_model = st.sidebar.text_input(
            "모델", value=st.session_state.get("llm_model", "") or d.get("model", ""))
        st.session_state.llm_base = st.sidebar.text_input(
            "Base URL", value=st.session_state.get("llm_base", "") or d.get("base_url", ""))
    cfg = get_cfg()
    st.sidebar.caption("🟢 LLM 사용" if llm.is_enabled(cfg) else "⚪ 템플릿 모드(LLM 미사용)")
    st.sidebar.divider()

    return st.sidebar.radio("모듈", list(MODULES.keys()))


def main():
    page = sidebar_project()
    project = st.session_state.project
    cfg = get_cfg()

    st.caption(
        "⚖️ 이 도구는 표절·AI탐지 **우회 도구가 아닙니다.** 초안은 참고용이며, "
        "본문은 반드시 본인 문장으로 작성하세요. (동국대 국제통상학과 양식 기준)"
    )
    st.caption(
        "💾 온라인 배포본은 저장공간이 **임시**입니다(서버 재시작 시 초기화 가능). "
        "중요한 작업은 ⑦에서 **.docx로 내려받아 보관**하세요."
    )
    MODULES[page].render(project, cfg)


if __name__ == "__main__":
    main()
