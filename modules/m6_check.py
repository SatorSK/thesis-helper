"""M6. 자가 점검 (Integrity Self-Check).

점수가 아니라 '할 일 목록'을 준다.
  - 인용 누락: 수치·주장이 있는데 그 절에 연결된 출처가 없음
  - AI 작성 의심: 단조로운 일반론 문장 → 구체화 권고
  - 자기표절: 사용자 체크리스트
  - 복붙 위험: M5 초안과 유사도 높은 절
"""
from __future__ import annotations

import re

from modules.m5_drafter import similarity, SIMILARITY_BLOCK, SIMILARITY_WARN

# AI/일반론 티가 나는 상투 표현(있으면 구체화 권고)
GENERIC_PHRASES = [
    "매우 중요하다", "중요한 역할을 한다", "다양한 요인", "급변하는", "날로 증가",
    "최근 들어", "주목받고 있다", "필수적이다", "큰 영향을 미친다", "활발히 논의",
    "이러한 측면에서", "결론적으로 말하면", "오늘날", "현대 사회에서",
]

NUM_PAT = re.compile(r"\d+(?:\.\d+)?\s*(?:%|퍼센트|억|조|만|달러|원|배|건|명|위)")


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.。!?])\s+|(?<=다)\.\s*|\n+", text or "")
    return [p.strip() for p in parts if p.strip()]


def check_section(section: dict, para: dict) -> dict:
    user_text = para.get("user_text", "") or ""
    cite_ids = para.get("cite_ids", [])
    sentences = split_sentences(user_text)

    issues = []

    # 1) 인용 누락: 수치·주장 문장이 있는데 출처 연결 0
    num_sents = [s for s in sentences if NUM_PAT.search(s)]
    if num_sents and not cite_ids:
        issues.append({
            "kind": "인용누락",
            "msg": f"수치/주장 {len(num_sents)}문장이 있으나 연결된 출처가 없음. 각주 인용을 추가하세요.",
            "detail": num_sents[:3],
        })

    # 2) AI/일반론 의심
    hits = [g for g in GENERIC_PHRASES if g in user_text]
    if hits:
        issues.append({
            "kind": "AI의심",
            "msg": f"상투적 일반론 표현 {len(hits)}개 — 구체적 사실·데이터로 바꾸세요.",
            "detail": hits,
        })

    # 3) 복붙 위험
    sim = similarity(para.get("draft", ""), user_text)
    if user_text.strip() and sim >= SIMILARITY_WARN:
        lvl = "차단" if sim >= SIMILARITY_BLOCK else "주의"
        issues.append({
            "kind": f"복붙위험({lvl})",
            "msg": f"M5 초안과 유사도 {sim*100:.0f}%. 본인 문장으로 다시 쓰세요.",
            "detail": [],
        })

    # 4) 미작성
    if not user_text.strip():
        issues.append({"kind": "미작성", "msg": "아직 본인 작성분이 없습니다.", "detail": []})

    return {"section": section["title"], "issues": issues}


def render(project, cfg):
    import streamlit as st
    from modules.m3_outline import ensure_outline

    st.header("⑥ 자가 점검")
    st.caption("탐지기 점수 예측이 아니라, 더 본인 글로 만들기 위한 '할 일 목록'입니다.")

    outline = ensure_outline(project)
    reports = [check_section(s, project["paragraphs"].get(s["id"], {})) for s in outline]

    total = sum(len(r["issues"]) for r in reports)
    blocked = any(i["kind"].startswith("복붙위험(차단") for r in reports for i in r["issues"])
    if blocked:
        st.error("🚫 복붙 차단 항목이 있습니다. 내보내기 전에 반드시 재작성하세요.")
    st.metric("보강 필요 항목", total)

    for r in reports:
        if not r["issues"]:
            st.success(f"✅ {r['section']} — 이상 없음")
            continue
        with st.expander(f"⚠️ {r['section']} — {len(r['issues'])}건"):
            for it in r["issues"]:
                st.markdown(f"**[{it['kind']}]** {it['msg']}")
                for d in it.get("detail", []):
                    st.caption(f"· {d}")

    st.divider()
    st.subheader("자기표절 체크리스트 (직접 확인)")
    st.checkbox("이전 과제/리포트의 문장을 그대로 재사용하지 않았다")
    st.checkbox("타인의 표·그림을 출처표기 없이 가져오지 않았다")
    st.checkbox("모든 직접인용에 따옴표와 각주를 달았다")
    st.checkbox("카피킬러 결과보고서(30% 이하)를 확인했다")
