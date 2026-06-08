"""모듈 로직 + .docx 내보내기 검증 (Streamlit UI 없이)."""
import io
import zipfile

from core import citation, llm
from core import project as P
from modules import m1_topic, m3_outline, m5_drafter, m6_check, m7_export


def main():
    # --- 프로젝트 생성 ---
    proj = P._empty_project("smoke-test")
    proj["meta"].update({"title": "CBAM이 한국 철강 수출에 미치는 영향",
                         "author": "홍길동", "student_id": "2020123456",
                         "advisor": "김교수", "date": "2026-06-08"})

    # --- M1: 템플릿 주제 추천 ---
    cands = m1_topic.suggest_template(["CBAM", "철강"], top_n=5)
    assert cands and "철강" in cands[0]["title"], "M1 키워드 매칭 실패"
    proj["topic"]["selected"] = cands[0]["title"]
    proj["topic"]["rq"] = cands[0]["rq"]
    print(f"[M1] 1순위 주제: {cands[0]['title']} (종합 {cands[0]['total']}/15)")

    # --- M2: 인용 ---
    src = {"id": "kim2024", "type": "article", "authors": "김철수", "year": "2024",
           "title": "탄소국경조정의 무역효과", "container": "국제통상연구", "volume": "29",
           "issue": "2", "pages": "1-30", "publisher": "", "url": "", "doi": "", "accessed": ""}
    proj["sources"].append(src)
    print(f"[M2] 각주: {citation.footnote(src)}")
    print(f"[M2] APA : {citation.apa_reference(src)}")
    assert citation.validate_source(src) == [], "M2 유효성 오탐"

    # --- M3: 골격 ---
    m3_outline.ensure_outline(proj)
    assert len(proj["outline"]) == 7, "M3 표준 골격 7절 아님"
    print(f"[M3] 절 개수: {len(proj['outline'])}")

    # --- M5: 단락 + 유사도 ---
    sid = proj["outline"][0]["id"]
    proj["paragraphs"][sid] = {
        "draft": "CBAM은 매우 중요하다. 큰 영향을 미친다.",
        "user_text": ("본 연구는 EU CBAM 도입이 한국 철강 수출단가에 미친 영향을 "
                      "2018~2024년 HS72 무역데이터로 분석한다. 분석 결과 2023년 이후 "
                      "대EU 단가가 12% 상승한 것으로 나타났다."),
        "cite_ids": ["kim2024"],
    }
    sim = m5_drafter.similarity(proj["paragraphs"][sid]["draft"],
                                proj["paragraphs"][sid]["user_text"])
    print(f"[M5] 초안-본인글 유사도: {sim*100:.0f}%")
    assert sim < m5_drafter.SIMILARITY_WARN, "M5 유사도 비정상(재작성 글인데 높음)"

    # --- M6: 자가점검 ---
    rep = m6_check.check_section(proj["outline"][0], proj["paragraphs"][sid])
    kinds = [i["kind"] for i in rep["issues"]]
    print(f"[M6] 1절 점검 이슈: {kinds or '없음'}")
    # 수치 있으나 cite 있음 → 인용누락 없어야
    assert "인용누락" not in kinds, "M6 인용누락 오탐"

    # 인용 없는 케이스
    rep2 = m6_check.check_section(
        {"title": "테스트", "checklist": []},
        {"draft": "", "user_text": "수출이 30% 증가했다.", "cite_ids": []})
    assert any(i["kind"] == "인용누락" for i in rep2["issues"]), "M6 인용누락 미탐"
    print("[M6] 인용누락 탐지 OK")

    # --- M7: docx 내보내기 (각주 포함) ---
    blocked = m7_export.blocked_sections(proj)
    assert blocked == [], f"M7 차단 오탐: {blocked}"
    data = m7_export.build_docx(proj, use_footnotes=True)
    assert data[:2] == b"PK", "docx 가 zip 이 아님"
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
        assert "word/footnotes.xml" in names, "footnotes.xml 미생성"
        fx = z.read("word/footnotes.xml").decode("utf-8")
        assert "탄소국경조정의 무역효과" in fx, "각주 텍스트 누락"
        doc_xml = z.read("word/document.xml").decode("utf-8")
        assert "footnoteReference" in doc_xml, "본문 각주 참조 누락"
        # 초안이 절대 안 들어갔는지
        assert "매우 중요하다" not in doc_xml, "초안이 문서에 유출됨!"
        assert "12% 상승" in doc_xml, "본인 작성분 누락"
    print(f"[M7] docx 생성 OK ({len(data):,} bytes), footnotes.xml + 본인글만 포함 확인")

    # 재오픈 검증
    from docx import Document
    Document(io.BytesIO(data))
    print("[M7] python-docx 재오픈 OK")

    # 파일명
    fn = m7_export.filename(proj)
    assert fn == "(국제통상학과)2020123456_홍길동.docx", fn
    print(f"[M7] 파일명: {fn}")

    # --- 폴백 경로도 검증 ---
    data2 = m7_export.build_docx(proj, use_footnotes=False)
    Document(io.BytesIO(data2))
    print("[M7] 각주 폴백 경로도 valid docx 생성 OK")

    # --- LLM 어댑터: 템플릿 모드 동작 ---
    cfg = llm.LLMConfig(backend="template")
    assert not llm.is_enabled(cfg)
    try:
        llm.complete("x", "y", cfg)
        raise AssertionError("템플릿 모드인데 호출이 통과됨")
    except llm.LLMError:
        pass
    print("[LLM] 템플릿 모드 가드 OK")

    # --- 접속코드(space) 분리 검증 ---
    import shutil
    shutil.rmtree(P.PROJECTS_ROOT, ignore_errors=True)
    sa = P.space_id("alice-1234")
    sb = P.space_id("bob-5678")
    assert sa != sb and sa.startswith("u_"), "space 해시 이상"
    assert P.space_id("") == "_default"
    P.new_project("thesis-a", sa)
    P.new_project("thesis-b", sb)
    assert P.list_projects(sa) == ["thesis-a"], P.list_projects(sa)
    assert P.list_projects(sb) == ["thesis-b"], P.list_projects(sb)
    # 다른 코드면 서로 안 보임
    assert "thesis-b" not in P.list_projects(sa), "space 격리 실패"
    # 저장 후 다시 로드해도 space 유지
    pa = P.load("thesis-a", sa)
    pa["meta"]["author"] = "앨리스"
    P.save(pa)
    assert P.load("thesis-a", sa)["meta"]["author"] == "앨리스"
    shutil.rmtree(P.PROJECTS_ROOT, ignore_errors=True)
    print("[SPACE] 접속코드 기반 프로젝트 격리 OK")

    print("\n[OK] 모든 스모크 테스트 통과")


if __name__ == "__main__":
    main()
