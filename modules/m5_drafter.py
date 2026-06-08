"""M5. 단락 초안 작성소 — 핵심 무결성 장치.

도구는 절의 '초안'과 논점 체크리스트를 준다(참고용, 복붙 금지).
사용자는 옆 칸에 '자기 문장'으로 작성한다. 최종 .docx 에는 사용자 작성분만 나간다.
초안과 사용자 글의 유사도가 높으면 경고/내보내기 차단 플래그를 세운다.
"""
from __future__ import annotations

from difflib import SequenceMatcher

from core import citation, llm

SIMILARITY_BLOCK = 0.80  # 이 이상이면 사실상 복붙 → 차단 경고
SIMILARITY_WARN = 0.60


def similarity(a: str, b: str) -> float:
    a, b = (a or "").strip(), (b or "").strip()
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def draft_template(section: dict, rq: str) -> str:
    """LLM 없이 쓰는 골격 초안(논점 가이드). 그대로 옮기면 안 되는 안내문."""
    pts = section.get("checklist", [])
    body = "\n".join(f"- {p}: (여기에 본인 분석을 쓰세요)" for p in pts) or "- (논점을 먼저 정하세요)"
    return (
        f"[{section['title']}] 작성 가이드\n"
        f"이 절의 목적: {section.get('purpose','')}\n"
        f"연구질문과의 연결: {rq}\n\n"
        f"다뤄야 할 논점:\n{body}\n\n"
        f"※ 이 가이드는 참고용입니다. 위 논점을 본인 문장으로 풀어 쓰세요."
    )


_SYS = (
    "당신은 국제통상 학부 논문 작성을 돕는 조교입니다. 학생이 '참고'할 단락 초안을 "
    "씁니다. 학생이 반드시 자기 문장으로 다시 쓸 것을 전제로, 핵심 논점과 흐름만 "
    "제시합니다. 과장·허위 통계는 쓰지 않습니다."
)


def draft_llm(section: dict, rq: str, sources: list[dict], cfg: llm.LLMConfig) -> str:
    src_txt = "\n".join(f"[{s['id']}] {citation.footnote(s)}" for s in sources[:8])
    prompt = (
        f"논문 연구질문: {rq}\n"
        f"절 제목: {section['title']}\n"
        f"절 목적: {section.get('purpose','')}\n"
        f"다뤄야 할 논점: {', '.join(section.get('checklist', []))}\n"
        f"인용 가능 출처:\n{src_txt or '(없음)'}\n\n"
        "이 절의 참고용 초안 단락(4~6문장)을 쓰세요. 차용 논점에는 (참고: [출처ID]) 를 표시하세요."
    )
    return llm.complete(prompt, _SYS, cfg)


def render(project, cfg):
    import streamlit as st
    from core import project as P
    from modules.m3_outline import ensure_outline

    st.header("⑤ 단락 초안 작성소")
    st.error(
        "⚠️ 왼쪽 초안은 **참고용입니다. 복사 금지.** 오른쪽 칸에 본인 문장으로 작성하세요. "
        "최종 논문에는 **오른쪽(본인 작성)만** 들어갑니다. 초안 텍스트는 내보내지지 않습니다."
    )

    outline = ensure_outline(project)
    rq = project["topic"].get("rq", "")
    sources = project["sources"]

    titles = [f"{i+1}. {s['title']}" for i, s in enumerate(outline)]
    sel = st.selectbox("작성할 절 선택", range(len(outline)), format_func=lambda i: titles[i])
    section = outline[sel]
    sid = section["id"]

    para = project["paragraphs"].setdefault(sid, {"draft": "", "user_text": "", "cite_ids": []})

    if st.button("이 절 초안 생성/갱신"):
        with st.spinner("초안 생성 중..."):
            if llm.is_enabled(cfg):
                try:
                    para["draft"] = draft_llm(section, rq, sources, cfg)
                except llm.LLMError as e:
                    st.warning(f"LLM 실패, 템플릿 초안 사용: {e}")
                    para["draft"] = draft_template(section, rq)
            else:
                para["draft"] = draft_template(section, rq)
        P.save(project)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**📖 초안 (참고용 — 복붙 금지, 내보내기 제외)**")
        st.text_area("초안", value=para.get("draft", ""), height=320, disabled=True, key=f"draft_{sid}")
    with col2:
        st.markdown("**✍️ 본인 작성 (이것만 논문에 들어감)**")
        user_text = st.text_area("본인 문장", value=para.get("user_text", ""), height=320, key=f"user_{sid}")

    # 인용 연결
    if sources:
        opts = [s["id"] for s in sources]
        labels = {s["id"]: f"[{s['id']}] {s.get('title','')[:30]}" for s in sources}
        para["cite_ids"] = st.multiselect(
            "이 절에서 인용할 출처 (각주로 삽입됨)",
            opts, default=[c for c in para.get("cite_ids", []) if c in opts],
            format_func=lambda x: labels.get(x, x),
        )

    sim = similarity(para.get("draft", ""), user_text)
    if user_text.strip():
        if sim >= SIMILARITY_BLOCK:
            st.error(f"🚫 초안과 유사도 {sim*100:.0f}% — 사실상 복붙입니다. 본인 문장으로 다시 쓰세요. (내보내기 차단)")
        elif sim >= SIMILARITY_WARN:
            st.warning(f"⚠️ 초안과 유사도 {sim*100:.0f}% — 더 본인 문장으로 바꾸길 권합니다.")
        else:
            st.success(f"✅ 초안과 유사도 {sim*100:.0f}% — 본인 글로 충분히 재작성됨.")

    if st.button("이 절 저장", type="primary"):
        para["user_text"] = user_text
        P.save(project)
        st.success("저장됨")

    # 진행 현황
    st.divider()
    done = sum(1 for s in outline if project["paragraphs"].get(s["id"], {}).get("user_text", "").strip())
    st.caption(f"작성 완료 절: {done}/{len(outline)} · 본문 추정 {P.estimate_pages(project)}쪽 / 20쪽")
