"""주제 검증 실행기 — scholar(네트워크) + embeddings + topic_analysis 조립.

UI는 run_validation() 하나만 호출한다. 부분 실패는 가능한 만큼 채워서 돌려준다.
"""
from __future__ import annotations

from core import embeddings, scholar
from core.scholar import ScholarError
from core.topic_analysis import TopicReport, build_report


def run_validation(
    query: str,
    mailto: str = "",
    api_key: str = "",
    kci_key: str = "",
    n_related: int = 20,
) -> tuple[TopicReport | None, str | None]:
    """성공 시 (TopicReport, None), 완전 실패 시 (None, 에러메시지)."""
    query = (query or "").strip()
    if not query:
        return None, "주제를 입력하세요."

    counts = scholar.counts_by_year(query, mailto, api_key)
    works = scholar.top_works(query, n_related, mailto, api_key)

    counts_ok = not isinstance(counts, ScholarError)
    works_ok = not isinstance(works, ScholarError)

    if not counts_ok and not works_ok:
        # 둘 다 실패 → 네트워크/키 문제
        return None, f"학술 DB 조회 실패: {counts.message}"

    by_year = counts if counts_ok else {}
    work_list = works if works_ok else []
    total_en = sum(by_year.values()) if counts_ok else len(work_list)

    # 유사도 계산
    docs = [f"{w.title}. {w.abstract}" for w in work_list]
    sims = embeddings.similarities(query, docs) if docs else []
    related_with_sim = list(zip(work_list, sims)) if sims else [(w, 0.0) for w in work_list]

    # KCI(선택)
    total_ko = -1
    if kci_key:
        ko = scholar.kci_total_count(query, kci_key)
        total_ko = ko if not isinstance(ko, ScholarError) else -1

    report = build_report(query, total_en, by_year, related_with_sim, total_ko)

    # 부분 실패 노트
    if not counts_ok:
        report.notes.append("연도별 추세 데이터를 못 받아 포화도 판정이 제한적입니다.")
    if not works_ok:
        report.notes.append("유사 논문 목록을 못 받아 유사도 판정이 제한적입니다.")
    report.notes.append(f"유사도 엔진: {embeddings.backend_name()}")
    return report, None
