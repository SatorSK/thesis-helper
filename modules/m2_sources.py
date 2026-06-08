"""M2. 자료수집 · 인용관리.

출처를 입력하면 인용 ID 부여 + 각주 텍스트(학과 규정) + APA 참고문헌을 생성.
모든 차용 아이디어에 ID를 달아두면 M5에서 본문 각주로 자동 삽입 → 인용 누락 방지.
"""
from __future__ import annotations

import re

from core import citation


def make_id(authors: str, year: str, existing: set[str]) -> str:
    first = re.split(r"[ ,;·]", authors.strip())[0] if authors.strip() else "ref"
    first = re.sub(r"[^0-9A-Za-z가-힣]", "", first) or "ref"
    base = f"{first}{year}".strip() or "ref"
    cid = base
    n = 1
    while cid in existing:
        n += 1
        cid = f"{base}_{n}"
    return cid


def render(project, cfg):
    import streamlit as st
    from core import project as P

    st.header("② 자료수집 · 인용관리")
    st.caption("학과 규정: 본문 인용은 각주. 참고문헌 목록은 APA 형식으로 정리합니다.")

    with st.form("add_source", clear_on_submit=True):
        st.subheader("출처 추가")
        c1, c2 = st.columns(2)
        with c1:
            typ = st.selectbox(
                "유형", list(citation.SOURCE_TYPES.keys()),
                format_func=lambda k: f"{k} · {citation.SOURCE_TYPES[k]}",
            )
            authors = st.text_input("저자 (예: 홍길동·김철수)")
            year = st.text_input("연도")
            title = st.text_input("제목")
            container = st.text_input("학술지/출판사/매체명 (container)")
        with c2:
            volume = st.text_input("권(volume)")
            issue = st.text_input("호(issue)")
            pages = st.text_input("쪽수 (예: 30-45)")
            publisher = st.text_input("발행처(출판사/기관)")
            url = st.text_input("URL")
        doi = st.text_input("DOI")
        if st.form_submit_button("추가", type="primary"):
            if not (authors or title):
                st.error("저자나 제목 중 하나는 입력하세요.")
            else:
                existing = {s["id"] for s in project["sources"]}
                s = {
                    "id": make_id(authors, year, existing),
                    "type": typ, "authors": authors, "year": year, "title": title,
                    "container": container, "volume": volume, "issue": issue,
                    "pages": pages, "publisher": publisher, "url": url, "doi": doi,
                    "accessed": "",
                }
                project["sources"].append(s)
                P.save(project)
                st.success(f"추가됨 · 인용 ID: [{s['id']}]")

    sources = project["sources"]
    if not sources:
        st.info("아직 출처가 없습니다. 위에서 추가하세요.")
        return

    st.subheader(f"등록된 출처 {len(sources)}개")
    for i, s in enumerate(sources):
        warns = citation.validate_source(s)
        flag = "⚠️" if warns else "✅"
        with st.expander(f"{flag} [{s['id']}] {s.get('title','(제목없음)')}"):
            st.markdown(f"**각주:** {citation.footnote(s)}")
            st.markdown(f"**APA 참고문헌:** {citation.apa_reference(s)}")
            if warns:
                st.warning("누락: " + ", ".join(warns))
            if st.button("삭제", key=f"del_src_{i}"):
                project["sources"].pop(i)
                P.save(project)
                st.rerun()

    st.divider()
    st.subheader("참고문헌 목록 (APA, 정렬)")
    for ref in citation.reference_list(sources):
        st.markdown(f"- {ref}")
