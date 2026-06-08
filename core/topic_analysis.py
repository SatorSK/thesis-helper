"""주제 검증 분석 — 순수 로직(네트워크/임베딩 결과를 주입받아 판정).

리서치 결론 반영:
  - 핵심 효용 = "참신성 경찰"이 아니라 "자료 확보 가능성 점검".
  - 참신성/관심도는 *신호*로만. 단정 라벨 금지, 시차·편향 한계를 문구에 내장.
모든 함수는 순수(네트워크 의존 없음)라 오프라인 단위테스트가 가능하다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from core.scholar import Work

# 임계값은 학부 졸업논문 기준 휴리스틱(감). 근거가 약하므로 조정 가능하게 상수로 분리.
DATA_SCARCE = 15      # 이하: 자료 부족
DATA_OK = 80          # 이상: 자료 충분 (사이는 '보통')
SIM_DUP = 0.80        # 이상: 거의 동일 주제 존재
SIM_DENSE = 0.60      # 이상: 매우 유사 연구 다수
SIM_RELATED = 0.40    # 이상: 관련 연구 있음


@dataclass
class Saturation:
    total_recent: int            # 최근 3년 논문 수
    growth: float                # 최근3년 vs 직전3년 증가율(-1~..)
    momentum: str                # 급성장 | 성장 | 정체/포화 | 쇠퇴 | 데이터부족
    by_year: dict                # {year: count} (차트용)


@dataclass
class TopicReport:
    query: str
    total_en: int
    total_ko: int                # KCI 등 국문(없으면 -1 = 미조회)
    availability: str            # 충분 | 보통 | 부족
    availability_msg: str
    saturation: Saturation
    novelty_label: str
    novelty_msg: str
    max_similarity: float
    related: list = field(default_factory=list)  # [(Work, sim)]
    notes: list = field(default_factory=list)


# ---------------------------------------------------------------- 포화/추세
def classify_saturation(by_year: dict) -> Saturation:
    by_year = {int(k): int(v) for k, v in (by_year or {}).items() if v is not None}
    if not by_year:
        return Saturation(0, 0.0, "데이터부족", {})
    max_y = max(by_year)
    recent = sum(by_year.get(y, 0) for y in range(max_y - 2, max_y + 1))
    prior = sum(by_year.get(y, 0) for y in range(max_y - 5, max_y - 2))
    total = sum(by_year.values())

    if total < 5:
        momentum = "데이터부족"
        growth = 0.0
    elif prior == 0:
        momentum = "급성장" if recent > 0 else "데이터부족"
        growth = 1.0 if recent > 0 else 0.0
    else:
        growth = (recent - prior) / prior
        if growth >= 0.5:
            momentum = "급성장"
        elif growth >= 0.15:
            momentum = "성장"
        elif growth >= -0.15:
            momentum = "정체/포화"
        else:
            momentum = "쇠퇴"
    return Saturation(recent, round(growth, 3), momentum, by_year)


# ---------------------------------------------------------------- 자료 확보
def assess_availability(total_en: int, total_ko: int) -> tuple[str, str]:
    ko = max(total_ko, 0)
    combined = total_en + ko
    if combined < DATA_SCARCE:
        return "부족", (
            f"검색되는 선행연구가 매우 적습니다(영문 {total_en}편"
            + (f", 국문 {ko}편" if total_ko >= 0 else "") +
            "). 자료를 못 구해 논문 작성이 막힐 위험이 큽니다. 주제를 넓히거나 재고하세요."
        )
    if combined >= DATA_OK:
        return "충분", (
            f"선행연구가 풍부합니다(영문 {total_en}편"
            + (f", 국문 {ko}편" if total_ko >= 0 else "") +
            "). 자료 확보 측면은 안전합니다."
        )
    return "보통", (
        f"선행연구가 적당합니다(영문 {total_en}편"
        + (f", 국문 {ko}편" if total_ko >= 0 else "") +
        "). 작성에 무리는 없으나 핵심 자료를 일찍 확보하세요."
    )


# ---------------------------------------------------------------- 참신성 신호
def novelty_from_similarity(max_sim: float, availability: str) -> tuple[str, str]:
    if max_sim >= SIM_DUP:
        return "거의 동일 주제 존재", (
            "사용자 주제와 거의 같은 선행연구가 있습니다. 차별점(대상·기간·방법)을 분명히 하세요."
        )
    if max_sim >= SIM_DENSE:
        return "매우 유사 연구 다수", "비슷한 연구가 많습니다. 본인만의 각도(데이터·사례)가 필요합니다."
    if max_sim >= SIM_RELATED:
        return "관련 연구 있음", "관련 연구가 있어 참고하기 좋고, 차별화 여지도 있습니다(적정)."
    # 유사도 낮음 → 틈새/자료부족/엔진한계 중 무엇인지 '논문 수'로 구분(핵심).
    if availability == "부족":
        return "직접 유사 연구 적음 (주의)", (
            "직접적으로 유사한 연구가 적지만, 자료 자체도 부족합니다. '틈새'가 아니라 '자료 없는 주제'일 수 있어 위험합니다."
        )
    if availability == "충분":
        # 논문이 많은데 유사도만 낮음 → 틈새가 아니라 검색어/유사도엔진 한계일 가능성이 큼.
        return "많이 연구된 주제", (
            "관련 논문이 많습니다. 유사도 점수가 낮은 것은 검색어 또는 경량 유사도엔진의 한계일 수 있으니, "
            "유사 선행연구 목록을 직접 확인하세요. 차별점(대상·기간·방법)이 필요합니다."
        )
    return "틈새 가능 (신호)", (
        "직접 유사 연구가 적습니다. 차별화 기회일 수 있으나, 인용 시차·검색 한계 탓일 수도 있으니 지도교수와 확인하세요."
    )


# ---------------------------------------------------------------- 종합
def build_report(
    query: str,
    total_en: int,
    by_year: dict,
    related_with_sim: list,   # [(Work, sim)]
    total_ko: int = -1,
) -> TopicReport:
    sat = classify_saturation(by_year)
    availability, avail_msg = assess_availability(total_en, total_ko)
    max_sim = max((s for _, s in related_with_sim), default=0.0)
    nov_label, nov_msg = novelty_from_similarity(max_sim, availability)

    notes = [
        "참신성·포화도는 *참고 신호*입니다. 인용은 보통 2~4년 시차가 있어, 최신·신생 주제는 과소평가될 수 있습니다.",
        "흔한 주제가 곧 나쁜 주제는 아닙니다(학부 논문은 학습이 목적). 정작 위험한 건 '자료가 없는 주제'입니다.",
    ]
    if sat.momentum == "데이터부족":
        notes.append("연도별 데이터가 적어 추세 판정을 신뢰하기 어렵습니다.")

    return TopicReport(
        query=query,
        total_en=total_en,
        total_ko=total_ko,
        availability=availability,
        availability_msg=avail_msg,
        saturation=sat,
        novelty_label=nov_label,
        novelty_msg=nov_msg,
        max_similarity=round(max_sim, 3),
        related=sorted(related_with_sim, key=lambda x: x[1], reverse=True),
        notes=notes,
    )
