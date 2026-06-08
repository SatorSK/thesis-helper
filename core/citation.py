"""인용 형식 생성.

동국대 국제통상학과 규정: 본문 인용은 **각주(footnote)**.
참고문헌 목록은 APA 7th 스타일로 정리(사용자 선호 절충).

각 source dict 필드:
  id, type(article|book|report|web|news|working_paper|thesis),
  authors, year, title, container(학술지/출판사명), volume, issue,
  pages, publisher, place, url, doi, accessed
"""
from __future__ import annotations

SOURCE_TYPES = {
    "article": "학술지 논문",
    "book": "단행본",
    "report": "보고서",
    "working_paper": "워킹페이퍼",
    "thesis": "학위논문",
    "news": "기사/보도자료",
    "web": "웹자료",
}


def _g(s: dict, k: str) -> str:
    return (s.get(k) or "").strip()


def footnote(s: dict, page: str = "") -> str:
    """본문 각주용 한 줄 인용. page 가 있으면 쪽수 명시."""
    a = _g(s, "authors")
    y = _g(s, "year")
    t = _g(s, "title")
    c = _g(s, "container")
    vol = _g(s, "volume")
    iss = _g(s, "issue")
    pg = (page or _g(s, "pages")).strip()
    typ = _g(s, "type")

    head = f"{a}({y})" if a and y else (a or y)
    pg_part = f", {pg}쪽" if pg else ""

    if typ == "article":
        vi = ""
        if c:
            vi = f"「{t}」, {c}"
            if vol:
                vi += f" {vol}권"
            if iss:
                vi += f" {iss}호"
        else:
            vi = f"「{t}」"
        return f"{head}, {vi}{pg_part}.".replace(" ,", ",")
    if typ in ("book", "thesis"):
        pub = _g(s, "publisher")
        tail = f"『{t}』" + (f", {pub}" if pub else "")
        return f"{head}, {tail}{pg_part}."
    if typ in ("report", "working_paper"):
        pub = _g(s, "publisher")
        tail = f"『{t}』" + (f", {pub}" if pub else "")
        return f"{head}, {tail}{pg_part}."
    if typ in ("news", "web"):
        url = _g(s, "url")
        acc = _g(s, "accessed")
        tail = f"「{t}」" + (f", {c}" if c else "")
        if url:
            tail += f", {url}"
        if acc:
            tail += f" (접속: {acc})"
        return f"{head}, {tail}."
    # fallback
    return f"{head}, {t}{pg_part}.".strip(", ")


def apa_reference(s: dict) -> str:
    """참고문헌 목록용 APA 7th 항목."""
    a = _g(s, "authors")
    y = _g(s, "year")
    t = _g(s, "title")
    c = _g(s, "container")
    vol = _g(s, "volume")
    iss = _g(s, "issue")
    pg = _g(s, "pages")
    typ = _g(s, "type")
    yr = f"({y})." if y else "(n.d.)."

    if typ == "article":
        vi = c
        if vol:
            vi += f", {vol}"
        if iss:
            vi += f"({iss})"
        if pg:
            vi += f", {pg}"
        return f"{a} {yr} {t}. {vi}.".replace("  ", " ")
    if typ in ("book",):
        pub = _g(s, "publisher")
        return f"{a} {yr} {t}. {pub}.".replace("  ", " ")
    if typ in ("report", "working_paper", "thesis"):
        pub = _g(s, "publisher")
        return f"{a} {yr} {t}. {pub}.".replace("  ", " ")
    if typ in ("news", "web"):
        url = _g(s, "url")
        tail = f"{c}." if c else ""
        if url:
            tail += f" {url}"
        return f"{a} {yr} {t}. {tail}".strip()
    return f"{a} {yr} {t}.".replace("  ", " ")


def reference_list(sources: list[dict]) -> list[str]:
    """저자명 가나다/알파벳 정렬된 APA 참고문헌 목록."""
    items = [apa_reference(s) for s in sources]
    return sorted(items)


def validate_source(s: dict) -> list[str]:
    """필수 필드 누락 점검. 부족하면 경고 메시지 리스트 반환."""
    warns = []
    if not _g(s, "authors"):
        warns.append("저자 누락")
    if not _g(s, "year"):
        warns.append("연도 누락")
    if not _g(s, "title"):
        warns.append("제목 누락")
    if s.get("type") == "article" and not _g(s, "container"):
        warns.append("학술지명(container) 누락")
    return warns
