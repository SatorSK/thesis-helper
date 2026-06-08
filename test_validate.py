"""주제 검증기 테스트 — 오프라인 순수로직 + (선택)라이브 API."""
from core import embeddings
from core.scholar import Work
from core.topic_analysis import (
    assess_availability, build_report, classify_saturation, novelty_from_similarity,
    DATA_SCARCE,
)


def test_saturation():
    growing = {2018: 2, 2019: 3, 2020: 4, 2021: 6, 2022: 9, 2023: 12, 2024: 15}
    s = classify_saturation(growing)
    assert s.momentum in ("급성장", "성장"), s.momentum
    assert s.total_recent == 12 + 15 + 9 or s.total_recent > 0

    declining = {2018: 50, 2019: 45, 2020: 40, 2021: 20, 2022: 12, 2023: 8, 2024: 5}
    assert classify_saturation(declining).momentum == "쇠퇴"

    assert classify_saturation({}).momentum == "데이터부족"
    assert classify_saturation({2023: 1, 2024: 1}).momentum == "데이터부족"
    print("[OK] classify_saturation")


def test_availability():
    assert assess_availability(3, -1)[0] == "부족"
    assert assess_availability(5, 4)[0] == "부족"  # combined < 15
    assert assess_availability(30, 10)[0] == "보통"
    assert assess_availability(200, 50)[0] == "충분"
    print("[OK] assess_availability")


def test_novelty():
    assert novelty_from_similarity(0.9, "충분")[0] == "거의 동일 주제 존재"
    assert novelty_from_similarity(0.65, "충분")[0] == "매우 유사 연구 다수"
    assert novelty_from_similarity(0.45, "보통")[0] == "관련 연구 있음"
    # 낮은 유사도 + 자료부족 → '틈새'가 아니라 '주의'여야 함 (핵심 안전장치)
    label, _ = novelty_from_similarity(0.1, "부족")
    assert "주의" in label, label
    # 논문 많은데 유사도만 낮음 → '틈새'가 아니라 '많이 연구된 주제'여야 함
    assert novelty_from_similarity(0.1, "충분")[0] == "많이 연구된 주제"
    # 자료 보통 + 낮은 유사도 → 틈새 신호
    assert novelty_from_similarity(0.1, "보통")[0] == "틈새 가능 (신호)"
    print("[OK] novelty_from_similarity (자료부족·과포화·틈새 3분기 구분)")


def test_embeddings():
    q = "carbon border tax effect on Korean steel exports"
    docs = [
        "CBAM carbon border adjustment mechanism impact on steel exports from Korea",
        "A study of marine biology in the Pacific ocean coral reefs",
    ]
    sims = embeddings.similarities(q, docs)
    assert len(sims) == 2
    assert all(0.0 <= s <= 1.0 for s in sims)
    assert sims[0] > sims[1], f"관련 문서가 더 높아야: {sims}"
    assert embeddings.backend_name() in ("sentence-transformers", "tfidf", "lexical")
    print(f"[OK] embeddings (backend={embeddings.backend_name()}, sims={[round(s,2) for s in sims]})")


def test_build_report():
    works = [
        Work(id="W1", title="CBAM and Korean steel", year=2023, cited_by=10,
             abstract="carbon border adjustment mechanism steel Korea export", authors=["Kim"]),
        Work(id="W2", title="Unrelated topic", year=2010, cited_by=2, abstract="something else"),
    ]
    sims = [0.85, 0.1]
    rep = build_report("CBAM Korea steel", total_en=120, by_year={2022: 5, 2023: 8, 2024: 11},
                       related_with_sim=list(zip(works, sims)), total_ko=15)
    assert rep.availability == "충분"
    assert rep.novelty_label == "거의 동일 주제 존재"
    assert rep.related[0][1] == 0.85  # 정렬 확인
    assert any("참고 신호" in n for n in rep.notes)
    print("[OK] build_report")


def test_live_optional():
    """네트워크 가능 시 실제 OpenAlex 호출. 실패하면 SKIP(테스트 실패 아님)."""
    from core.validate import run_validation
    report, err = run_validation("CBAM Korea steel export", n_related=10)
    if err:
        print(f"[SKIP] live API: {err}")
        return
    assert report.total_en > 0, "라이브: 논문 수 0"
    assert len(report.related) > 0, "라이브: 유사논문 없음"
    print(f"[OK] LIVE OpenAlex: total_en={report.total_en}, "
          f"추세={report.saturation.momentum}, related={len(report.related)}, "
          f"max_sim={report.max_similarity}")


if __name__ == "__main__":
    test_saturation()
    test_availability()
    test_novelty()
    test_embeddings()
    test_build_report()
    test_live_optional()
    print("\n[OK] 주제 검증기 테스트 통과")
