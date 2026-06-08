"""M3. 골격 빌더.

혼합형(정성+보조데이터) 학부논문 표준 골격을 제공하고, 사용자가
절을 추가/삭제/이동한다. 각 절에는 목적 1줄 + 자료 체크리스트.
"""
from __future__ import annotations

DEFAULT_OUTLINE = [
    {"level": 1, "title": "서론", "purpose": "연구 배경·목적·연구질문·논문 구성", "checklist": ["연구 배경", "연구 질문(RQ)", "연구 방법 개요"]},
    {"level": 1, "title": "선행연구 검토", "purpose": "기존 연구 정리와 본 연구의 차별점", "checklist": ["국내 연구", "해외 연구", "연구 공백(gap)"]},
    {"level": 1, "title": "분석틀 및 연구방법", "purpose": "분석 개념틀·데이터·방법 설명", "checklist": ["분석 개념틀", "데이터 출처/기간", "분석 방법"]},
    {"level": 1, "title": "정성 분석 (사례·정책)", "purpose": "핵심 사례·정책의 정성적 분석", "checklist": ["사례/정책 개요", "메커니즘 분석", "쟁점"]},
    {"level": 1, "title": "보조 데이터 분석", "purpose": "무역지표로 정성분석 뒷받침", "checklist": ["기초 통계/추세", "비교 분석", "그래프/표 해석"]},
    {"level": 1, "title": "논의", "purpose": "결과 종합·해석·함의", "checklist": ["결과 요약", "이론/정책 함의", "한계"]},
    {"level": 1, "title": "결론 및 시사점", "purpose": "요약·정책 제언·향후 과제", "checklist": ["핵심 결론", "정책 시사점", "향후 연구"]},
]


def ensure_outline(project):
    if not project.get("outline"):
        out = []
        for i, sec in enumerate(DEFAULT_OUTLINE):
            s = dict(sec)
            s["id"] = f"sec{i+1}"
            out.append(s)
        project["outline"] = out
    return project["outline"]


def render(project, cfg):
    import streamlit as st
    from core import project as P

    st.header("③ 골격 빌더")
    st.caption("혼합형 학부논문 표준 골격입니다. 절을 추가/삭제/이동하세요. 학과 규정: 본문 20장 이상.")

    outline = ensure_outline(project)

    pages = P.estimate_pages(project)
    st.metric("현재 본문 분량(추정)", f"{pages} 쪽 / 20쪽", delta=f"{round(pages-20,1)} 쪽")
    st.progress(min(pages / 20.0, 1.0))

    if st.button("표준 골격으로 초기화"):
        project["outline"] = []
        ensure_outline(project)
        P.save(project)
        st.rerun()

    st.divider()
    for i, sec in enumerate(outline):
        with st.expander(f"{i+1}. {'　'*(sec.get('level',1)-1)}{sec['title']}"):
            sec["title"] = st.text_input("절 제목", value=sec["title"], key=f"ot_{sec['id']}")
            sec["level"] = st.selectbox("수준", [1, 2, 3], index=sec.get("level", 1) - 1, key=f"ol_{sec['id']}")
            sec["purpose"] = st.text_input("목적(1줄)", value=sec.get("purpose", ""), key=f"op_{sec['id']}")
            sec["checklist"] = [
                c.strip() for c in st.text_area(
                    "자료 체크리스트 (줄바꿈 구분)",
                    value="\n".join(sec.get("checklist", [])), key=f"oc_{sec['id']}",
                ).split("\n") if c.strip()
            ]
            c1, c2, c3 = st.columns(3)
            if c1.button("▲ 위로", key=f"up_{sec['id']}") and i > 0:
                outline[i - 1], outline[i] = outline[i], outline[i - 1]
                P.save(project); st.rerun()
            if c2.button("▼ 아래로", key=f"dn_{sec['id']}") and i < len(outline) - 1:
                outline[i + 1], outline[i] = outline[i], outline[i + 1]
                P.save(project); st.rerun()
            if c3.button("🗑 삭제", key=f"rm_{sec['id']}"):
                outline.pop(i)
                P.save(project); st.rerun()

    st.divider()
    new_title = st.text_input("새 절 추가", key="new_sec_title")
    if st.button("절 추가") and new_title.strip():
        ids = [int(s["id"][3:]) for s in outline if s["id"].startswith("sec") and s["id"][3:].isdigit()]
        nid = f"sec{(max(ids)+1) if ids else 1}"
        outline.append({"id": nid, "level": 1, "title": new_title.strip(), "purpose": "", "checklist": []})
        P.save(project); st.rerun()

    if st.button("골격 저장", type="primary"):
        P.save(project)
        st.success("저장됨")
