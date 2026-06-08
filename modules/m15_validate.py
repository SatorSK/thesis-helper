"""M1.5 주제 검증기 (Topic Validator).

사용자가 고른 주제를 OpenAlex(+선택 KCI)로 조회해:
  - 자료 확보 가능성(핵심) · 연도별 포화/추세 · 유사 선행연구 · 참신성 신호
를 보여준다. 판정은 *신호*이며 단정하지 않는다(리서치 결론 반영).
유사 논문을 ②자료·인용관리로 바로 보낼 수 있다.
"""
from __future__ import annotations

from core.validate import run_validation


def _avail_color(level: str) -> str:
    return {"충분": "🟢", "보통": "🟡", "부족": "🔴"}.get(level, "⚪")


def render(project, cfg):
    import streamlit as st
    import pandas as pd
    from core import project as P

    st.header("①.5 주제 검증기")
    st.caption(
        "고른 주제가 ⓐ쓸 자료가 있는지 ⓑ얼마나 연구됐는지(포화도) ⓒ유사 선행연구를 확인합니다. "
        "OpenAlex(무료, 키 불필요) 기반. 판정은 참고 신호이며, 흔한 주제가 곧 나쁜 건 아닙니다."
    )

    default_q = project["topic"].get("selected") or project["topic"].get("rq") or ""
    query = st.text_input("검증할 주제/연구질문", value=default_q,
                          placeholder="예: CBAM이 한국 철강 수출에 미치는 영향")

    with st.expander("고급 설정 (선택)"):
        mailto = st.text_input(
            "이메일(OpenAlex polite pool용)", value=st.session_state.get("oa_mailto", ""),
            help="넣으면 OpenAlex가 더 빠르고 안정적으로 응답합니다. 비워도 동작합니다.",
        )
        st.session_state.oa_mailto = mailto
        kci_key = st.text_input(
            "KCI Open API 키(국문 논문 수 조회용, 선택)", type="password",
            value=st.session_state.get("kci_key", ""),
            help="data.go.kr에서 무료 발급. 없으면 영문(OpenAlex)만 집계합니다.",
        )
        st.session_state.kci_key = kci_key

    run = st.button("주제 검증 실행", type="primary")

    # 영문 키워드 권장 안내(OpenAlex는 영문 색인이 강함)
    if query and not any("a" <= c.lower() <= "z" for c in query):
        st.info("팁: OpenAlex는 영문 색인이 강합니다. 핵심어를 영문으로 넣으면 더 정확합니다 (예: 'CBAM Korea steel export').")

    if not run:
        return

    @st.cache_data(show_spinner=False, ttl=3600)
    def _cached(q, m, k):
        return run_validation(q, mailto=m, kci_key=k)

    with st.spinner("학술 DB 조회 + 유사도 분석 중... (첫 실행은 모델 로딩으로 느릴 수 있음)"):
        report, err = _cached(query, mailto, kci_key)

    if err:
        st.error(f"❌ {err}")
        st.caption("네트워크 또는 검색어 문제일 수 있습니다. 잠시 후 다시 시도하거나 검색어를 영문으로 바꿔보세요.")
        return

    # ---- 요약 지표 ----
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("자료 확보", f"{_avail_color(report.availability)} {report.availability}")
    c2.metric("최근 3년 논문수", report.saturation.total_recent)
    c3.metric("추세", report.saturation.momentum,
              delta=f"{report.saturation.growth*100:+.0f}%" if report.saturation.momentum != "데이터부족" else None)
    c4.metric("최대 유사도", f"{report.max_similarity*100:.0f}%")

    # ---- 자료 확보 (핵심) ----
    box = {"충분": st.success, "보통": st.info, "부족": st.error}.get(report.availability, st.info)
    box(f"**자료 확보 — {report.availability}.** {report.availability_msg}")

    # ---- 포화/추세 차트 ----
    if report.saturation.by_year:
        st.subheader("연도별 논문 수 (포화도/추세)")
        df = pd.DataFrame(
            sorted(report.saturation.by_year.items()), columns=["연도", "논문수"]
        ).set_index("연도")
        st.bar_chart(df)

    # ---- 참신성 신호 ----
    st.subheader(f"참신성 신호 — {report.novelty_label}")
    st.write(report.novelty_msg)

    # ---- 유사 선행연구 ----
    st.subheader(f"유사 선행연구 상위 {len(report.related)}편")
    src_ids = {s["id"] for s in project["sources"]}
    for i, (w, sim) in enumerate(report.related):
        with st.expander(f"{sim*100:.0f}% · {w.title}  ({w.year or '?'}, 피인용 {w.cited_by})"):
            if w.authors:
                st.caption("저자: " + ", ".join(w.authors) + (" 외" if len(w.authors) >= 5 else ""))
            if w.venue:
                st.caption("출처: " + w.venue)
            if w.abstract:
                st.write(w.abstract[:400] + ("…" if len(w.abstract) > 400 else ""))
            st.markdown(f"[원문 링크]({w.url})")
            if st.button("② 출처로 추가", key=f"add_src_{i}"):
                from modules.m2_sources import make_id
                cid = make_id(w.authors[0] if w.authors else "ref", str(w.year or ""), src_ids)
                project["sources"].append({
                    "id": cid, "type": "article",
                    "authors": ", ".join(w.authors), "year": str(w.year or ""),
                    "title": w.title, "container": w.venue, "volume": "", "issue": "",
                    "pages": "", "publisher": "", "url": w.url, "doi": w.doi, "accessed": "",
                })
                P.save(project)
                st.success(f"②에 추가됨 · [{cid}]")

    # ---- 한계 노트 ----
    st.divider()
    for n in report.notes:
        st.caption("· " + n)
