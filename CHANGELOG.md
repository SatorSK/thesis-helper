# Changelog

이 프로젝트의 주요 변경 사항을 기록합니다. 형식은 [Keep a Changelog](https://keepachangelog.com/)를 따릅니다.

## [0.2.0] - 2026-06-08

### Added
- **주제 검증기(①.5)** — OpenAlex API 실연동(키 불필요, polite pool). 자료 확보 가능성 점검, 연도별 포화도/추세, 유사 선행연구 + 유사도, 참신성 신호.
- `core/scholar.py` — OpenAlex/KCI 클라이언트 (requests 세션 재사용, 지수백오프 재시도, 타임아웃, on-disk 캐시 TTL).
- `core/embeddings.py` — 유사도 백엔드 3단계 강등 (sentence-transformers → scikit-learn TF-IDF → lexical Jaccard).
- `core/topic_analysis.py` (순수 로직) + `core/validate.py` (조립). 부분 실패 우아하게 처리.
- 찾은 논문을 ② 자료·인용관리로 바로 추가하는 버튼.
- `test_validate.py` — 오프라인 순수로직 + 라이브 OpenAlex 테스트.

### Notes
- 참신성/포화도는 *참고 신호*로만 표기(인용 시차·검색 한계 명시). 핵심 효용은 "자료 확보 가능성" 점검.
- requirements에 `scikit-learn` 추가. sentence-transformers는 선택(런타임 감지).

## [0.1.0] - 2026-06-08

### Added
- 7개 모듈 MVP: 주제 발굴 · 자료/인용관리 · 골격 빌더 · 데이터 분석 · 단락 작성소 · 자가 점검 · `.docx` 내보내기
- 동국대 국제통상학과 양식 자동 적용 (여백·폰트·줄간격·표지·파일명)
- 실제 OOXML 각주(footnote) 주입 엔진 + APA 7th 참고문헌
- provider-agnostic LLM 백엔드 (OpenAI/Codex · Anthropic · Gemini · 로컬 · 템플릿)
- 접속코드 기반 프로젝트 분리
- 무결성 가드: 초안-본인글 유사도 차단, 초안 텍스트 내보내기 제외
- `smoke_test.py` (로직 + `.docx` + 격리 검증)
