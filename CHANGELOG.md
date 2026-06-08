# Changelog

이 프로젝트의 주요 변경 사항을 기록합니다. 형식은 [Keep a Changelog](https://keepachangelog.com/)를 따릅니다.

## [0.1.0] - 2026-06-08

### Added
- 7개 모듈 MVP: 주제 발굴 · 자료/인용관리 · 골격 빌더 · 데이터 분석 · 단락 작성소 · 자가 점검 · `.docx` 내보내기
- 동국대 국제통상학과 양식 자동 적용 (여백·폰트·줄간격·표지·파일명)
- 실제 OOXML 각주(footnote) 주입 엔진 + APA 7th 참고문헌
- provider-agnostic LLM 백엔드 (OpenAI/Codex · Anthropic · Gemini · 로컬 · 템플릿)
- 접속코드 기반 프로젝트 분리
- 무결성 가드: 초안-본인글 유사도 차단, 초안 텍스트 내보내기 제외
- `smoke_test.py` (로직 + `.docx` + 격리 검증)
