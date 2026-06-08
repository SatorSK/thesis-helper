"""M1. 주제 발굴.

템플릿 모드: 큐레이션된 2026 국제통상 주제 풀에서 키워드 매칭 + 점수화.
LLM 모드: 키워드 기반으로 새 후보 생성.
점수 = 참신성 / 데이터확보 용이성 / 선행연구 충분성 (각 1~5).
"""
from __future__ import annotations

from core import llm

# 2026 시점 국제통상 학부논문 주제 풀.
# data: 데이터 확보 용이성, novelty: 참신성, lit: 선행연구 충분성 (1~5, 높을수록 좋음)
TOPIC_POOL = [
    {
        "title": "EU 탄소국경조정제도(CBAM)가 한국 철강 수출에 미치는 영향",
        "keywords": ["cbam", "탄소", "철강", "eu", "환경", "탄소국경"],
        "novelty": 4, "data": 5, "lit": 4,
        "rq": "CBAM 본격 시행이 한국 철강(HS72) 대EU 수출단가·물량에 미친 영향은?",
        "sources": ["UN Comtrade(HS72)", "EU CBAM 규정문", "한국철강협회", "KITA"],
    },
    {
        "title": "미국 IRA가 한국 이차전지 공급망에 미친 영향",
        "keywords": ["ira", "이차전지", "배터리", "미국", "보조금", "공급망"],
        "novelty": 4, "data": 4, "lit": 4,
        "rq": "IRA 시행 전후 한국 이차전지·소재의 대미 수출과 현지투자 변화는?",
        "sources": ["UN Comtrade(HS8507)", "산업부 보도", "KOTRA 보고서", "기업 공시"],
    },
    {
        "title": "미·중 디커플링과 한국 중간재 무역의 재편",
        "keywords": ["미중", "디커플링", "중간재", "공급망", "리쇼어링", "디리스킹"],
        "novelty": 4, "data": 4, "lit": 3,
        "rq": "미중 갈등 심화기(2018~2024) 한국 중간재 수출의 대상국 구조는 어떻게 변했나?",
        "sources": ["UN Comtrade(BEC 중간재)", "WITS", "KIEP 보고서"],
    },
    {
        "title": "디지털무역협정(DEPA)과 데이터 현지화 규제의 무역효과",
        "keywords": ["디지털무역", "depa", "데이터", "현지화", "디지털", "ecommerce"],
        "novelty": 5, "data": 3, "lit": 3,
        "rq": "데이터 현지화 규제 강도가 디지털 서비스 무역에 미치는 영향은?",
        "sources": ["OECD Digital STRI", "WTO 서비스무역", "DEPA 협정문"],
    },
    {
        "title": "공급망 프렌드쇼어링이 한·베트남 무역구조에 미친 영향",
        "keywords": ["베트남", "프렌드쇼어링", "공급망", "fdi", "리쇼어링", "아세안"],
        "novelty": 4, "data": 5, "lit": 3,
        "rq": "프렌드쇼어링 흐름 속 한국의 대베트남 수출·투자는 어떻게 변했나?",
        "sources": ["UN Comtrade", "한국수출입은행 해외투자통계", "KOTRA"],
    },
    {
        "title": "RCEP 발효가 역내 원산지 규정과 한국 수출에 미친 영향",
        "keywords": ["rcep", "fta", "원산지", "아세안", "관세", "역내"],
        "novelty": 3, "data": 4, "lit": 4,
        "rq": "RCEP 발효 후 한국의 대역내 수출 품목·단가에 유의미한 변화가 있었나?",
        "sources": ["KITA FTA 활용통계", "관세청", "UN Comtrade"],
    },
    {
        "title": "환율 변동이 한국 중소수출기업 가격경쟁력에 미치는 영향",
        "keywords": ["환율", "중소기업", "가격경쟁력", "수출", "원화", "exchange"],
        "novelty": 3, "data": 5, "lit": 5,
        "rq": "원/달러 환율 변동이 중소기업 수출단가·물량에 미치는 탄력성은?",
        "sources": ["한국은행 ECOS(환율)", "중소벤처기업부", "KITA"],
    },
    {
        "title": "ESG·공급망실사법(CSDDD)이 한국 수출기업에 주는 무역장벽 효과",
        "keywords": ["esg", "실사", "csddd", "공급망실사", "지속가능", "비관세"],
        "novelty": 5, "data": 3, "lit": 2,
        "rq": "EU 공급망실사법이 한국 수출기업의 비관세 부담으로 작동하는 메커니즘은?",
        "sources": ["EU CSDDD 지침", "KOTRA", "산업연구원(KIET)"],
    },
    {
        "title": "반도체 수출통제가 한국 반도체 무역에 미친 영향",
        "keywords": ["반도체", "수출통제", "미국", "중국", "장비", "semiconductor"],
        "novelty": 4, "data": 4, "lit": 3,
        "rq": "대중 반도체 수출통제 강화가 한국의 반도체·장비 수출 구조에 미친 영향은?",
        "sources": ["UN Comtrade(HS8541/8542)", "BIS 규정", "산업부"],
    },
    {
        "title": "K-콘텐츠 수출과 소비재 수출 간의 동반 효과(한류 무역효과)",
        "keywords": ["한류", "k-콘텐츠", "소비재", "문화", "수출", "브랜드"],
        "novelty": 5, "data": 3, "lit": 3,
        "rq": "K-콘텐츠 확산이 화장품·식품 등 소비재 수출에 미치는 동반효과가 있는가?",
        "sources": ["KOFICE 한류실태조사", "UN Comtrade", "관세청 수출입"],
    },
]


def score_total(t: dict) -> int:
    return t["novelty"] + t["data"] + t["lit"]


def suggest_template(keywords: list[str], top_n: int = 10) -> list[dict]:
    """키워드 매칭 점수를 더해 정렬. 키워드 없으면 종합점수순."""
    kws = [k.strip().lower() for k in keywords if k.strip()]
    ranked = []
    for t in TOPIC_POOL:
        match = sum(1 for k in kws if any(k in kw or kw in k for kw in t["keywords"]))
        ranked.append((match, score_total(t), t))
    ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
    out = []
    for _, _, t in ranked[:top_n]:
        c = dict(t)
        c["total"] = score_total(t)
        out.append(c)
    return out


_SYS = (
    "당신은 국제통상 학부 졸업논문 지도조교입니다. 데이터로 검증 가능한 참신한 "
    "주제를 제안합니다. 표절 위험이 낮고 학부 수준에서 실증 가능한 주제를 우선합니다."
)


def suggest_llm(keywords: list[str], cfg: llm.LLMConfig, top_n: int = 10) -> list[dict]:
    kw = ", ".join(keywords) if keywords else "(자유)"
    prompt = (
        f"관심 키워드: {kw}\n"
        f"국제통상 학부 졸업논문 주제 후보 {top_n}개를 JSON 배열로 제안하세요. "
        "각 원소 필드: title(주제), rq(핵심 연구질문 1문장), "
        "novelty/data/lit(각 1~5 정수: 참신성/데이터확보용이성/선행연구충분성), "
        "sources(추천 데이터·자료 출처 문자열 배열). "
        "2024~2026 최신 통상 이슈(CBAM, IRA, 디커플링, 디지털무역, ESG실사 등)를 반영하세요."
    )
    data = llm.complete_json(prompt, _SYS, cfg)
    if isinstance(data, dict):
        data = data.get("topics") or data.get("candidates") or []
    out = []
    for t in data[:top_n]:
        t.setdefault("novelty", 3)
        t.setdefault("data", 3)
        t.setdefault("lit", 3)
        t.setdefault("sources", [])
        t["total"] = int(t["novelty"]) + int(t["data"]) + int(t["lit"])
        out.append(t)
    return out


def suggest(keywords: list[str], cfg: llm.LLMConfig, top_n: int = 10) -> list[dict]:
    if llm.is_enabled(cfg):
        try:
            res = suggest_llm(keywords, cfg, top_n)
            if res:
                return res
        except llm.LLMError:
            pass  # 실패 시 템플릿으로 폴백
    return suggest_template(keywords, top_n)


# ---------------------------------------------------------------- UI
def render(project, cfg):
    import streamlit as st
    from core import project as P

    st.header("① 주제 발굴")
    st.caption("데이터로 검증 가능한 참신한 주제를 제안합니다. 후보는 초안일 뿐, 최종 확정·수정은 본인이 합니다.")

    kw_raw = st.text_input("관심 키워드 (쉼표로 구분)", placeholder="예: CBAM, 철강, 공급망")
    if st.button("주제 후보 생성", type="primary"):
        kws = [k for k in kw_raw.split(",")]
        with st.spinner("후보 생성 중..."):
            project["topic"]["candidates"] = suggest(kws, cfg)
        P.save(project)

    cands = project["topic"].get("candidates", [])
    if cands:
        st.subheader(f"후보 {len(cands)}개 (점수 높을수록 추천)")
        for i, t in enumerate(cands):
            total = t.get("total", t.get("novelty", 0) + t.get("data", 0) + t.get("lit", 0))
            with st.expander(f"{i+1}. {t['title']}  ·  종합 {total}/15"):
                st.markdown(f"**연구질문(RQ):** {t.get('rq','')}")
                st.markdown(
                    f"참신성 {t.get('novelty','?')}/5 · 데이터확보 {t.get('data','?')}/5 · 선행연구 {t.get('lit','?')}/5"
                )
                srcs = t.get("sources", [])
                if srcs:
                    st.markdown("**추천 자료:** " + ", ".join(srcs))
                if st.button("이 주제로 확정", key=f"pick_{i}"):
                    project["topic"]["selected"] = t["title"]
                    project["topic"]["rq"] = t.get("rq", "")
                    if not project["meta"].get("title"):
                        project["meta"]["title"] = t["title"]
                    P.save(project)
                    st.success(f"확정: {t['title']}")

    st.divider()
    st.subheader("확정 주제")
    sel = st.text_input("주제(제목)", value=project["topic"].get("selected", ""))
    rq = st.text_area("핵심 연구질문(RQ)", value=project["topic"].get("rq", ""), height=80)
    if st.button("주제 저장"):
        project["topic"]["selected"] = sel
        project["topic"]["rq"] = rq
        if sel and not project["meta"].get("title"):
            project["meta"]["title"] = sel
        P.save(project)
        st.success("저장됨")
