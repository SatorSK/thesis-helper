<div align="center">

# 🎓 Thesis Helper · 졸업논문 작성 도우미

**국제통상 졸업논문을 학과 양식에 맞춰 정직하게 쓰도록 돕는 로컬/웹 도구**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![Streamlit](https://img.shields.io/badge/Built%20with-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-active-success.svg)](#로드맵)

주제 발굴 · 인용 관리 · 골격 · 데이터 분석 · 단락 작성 · 자가 점검 · **동국대 양식 .docx 내보내기**

</div>

> [!IMPORTANT]
> **이 도구는 표절·AI 탐지 "우회" 도구가 아닙니다.**
> 초안·자료·인용은 도구가 돕고, **모든 본문 문장은 사용자가 직접 작성**합니다.
> 표절률을 낮추는 정공법은 ① 정확한 인용과 ② 본인의 독창적 분석입니다. 이 도구는 그 두 가지를 돕습니다.

---

## ✨ 주요 기능

| 모듈 | 기능 |
|------|------|
| ① **주제 발굴** | 2026 국제통상 이슈 기반 주제 후보 + 참신성·데이터확보·선행연구 점수화 |
| ①.5 **주제 검증기** | OpenAlex(무료) 실연동 — **자료 확보 가능성** 점검 + 연도별 포화도/추세 + 유사 선행연구·유사도. 찾은 논문을 ②로 바로 추가 |
| ② **자료·인용관리** | 출처 입력 → **각주(학과 규정) + APA 참고문헌** 자동 생성, 인용 ID 부여 |
| ③ **골격 빌더** | 혼합형(정성+데이터) 학부논문 표준 골격, 본문 분량(20쪽) 게이지 |
| ④ **데이터 분석** | CSV 업로드 → 추세/비교 그래프 + "데이터가 말하는 사실" 요약 |
| ⑤ **단락 작성소** | 초안은 *참고용(복붙 금지·내보내기 제외)*, 본인 작성분만 논문에 반영. 유사도 경고/차단 |
| ⑥ **자가 점검** | 인용 누락·AI 일반론·복붙 위험을 **할 일 목록**으로 표시 |
| ⑦ **내보내기** | 학과 양식 `.docx` (여백·폰트·줄간격·**실제 각주**·표지·파일명 자동) |

### 핵심 설계 — 무결성 가드
- ⑤단락작성소: 초안과 본인 글의 **유사도가 80% 이상이면 ⑦내보내기를 차단**합니다. "초안 복붙"을 코드가 막습니다.
- 최종 `.docx`에는 **본인이 작성한 문장만** 들어갑니다. 초안 텍스트는 절대 내보내지지 않습니다.

---

## 🚀 빠른 시작

```bash
git clone https://github.com/<your-id>/thesis-helper.git
cd thesis-helper
pip install -r requirements.txt
streamlit run app.py
```

브라우저가 자동으로 열립니다. 좌측 사이드바에서 **접속 코드 입력 → 프로젝트 생성 → ①~⑦ 순서대로** 진행하세요.
**API 키 없이도** 기본 템플릿 모드로 바로 작동합니다.

### 온라인 배포 (Streamlit Community Cloud)
1. 이 저장소를 본인 GitHub로 push
2. [share.streamlit.io](https://share.streamlit.io) → Sign in with GitHub → **Create app**
3. Repository / Branch `main` / **Main file path `app.py`** → Deploy
4. 발급된 `https://....streamlit.app` URL을 공유

> 💡 배포본 저장공간은 임시입니다(서버 재시작 시 초기화). 중요한 작업은 ⑦에서 `.docx`로 내려받아 보관하세요.

---

## 🔌 LLM 백엔드 (선택 · provider-agnostic)

특정 회사에 묶지 않습니다. 사이드바에서 백엔드를 교체하세요. 기본은 **키 없이 동작하는 템플릿 모드**입니다.

| 백엔드 | 필요한 것 |
|--------|-----------|
| `template` | 없음 (기본값) |
| `openai` | OpenAI / Codex API Key (Base URL 변경 가능) |
| `anthropic` | Anthropic API Key |
| `gemini` | Google API Key |
| `local` | Ollama·LM Studio 등 OpenAI 호환 로컬 서버 (키 불필요) |

> 🔒 API 키는 **세션에만 보관**하며 디스크에 저장하지 않습니다.
> 논문 원고 전체를 외부로 전송하지 않고, 해당 단락의 논점·인용만 전송합니다.

---

## 🏗️ 아키텍처

```
thesis-helper/
├─ app.py                  # Streamlit 진입점 (사이드바 = 모듈 라우터)
├─ core/
│  ├─ project.py           # project.json 상태 저장/불러오기 + 접속코드 분리
│  ├─ llm.py               # provider-agnostic LLM 어댑터 (REST 기반, SDK 무의존)
│  ├─ citation.py          # 각주 + APA 7th 포맷터
│  ├─ docx_footnotes.py    # 실제 OOXML 각주(footnote) 주입 엔진
│  ├─ scholar.py           # OpenAlex/KCI 클라이언트 (재시도·캐시·polite pool)
│  ├─ embeddings.py        # 유사도 백엔드 (sentence-transformers→TF-IDF→lexical 강등)
│  ├─ topic_analysis.py    # 포화도·자료확보·참신성 판정 (순수 로직)
│  └─ validate.py          # 주제 검증 실행기 (조립)
├─ modules/
│  └─ m1_topic … m7_export # 7개 기능 모듈 (각자 render(project, cfg))
├─ projects/<space>/<name> # 프로젝트별 상태·그림 (gitignore, 접속코드로 격리)
├─ smoke_test.py           # 로직 + .docx 생성 검증
└─ requirements.txt
```

**모듈 흐름**

```
① 주제발굴 → ② 자료·인용 → ③ 골격 → ④ 데이터분석
    → ⑤ 단락작성 → ⑥ 자가점검 → ⑦ .docx 내보내기
                                   (공유 상태: project.json)
```

---

## 📐 동국대 국제통상학과 규정 (반영됨)

| 항목 | 규정 |
|------|------|
| 용지·여백 | A4 / 상하좌우 30mm, 머리말·꼬리말 15mm |
| 글자·줄간격 | 본문 11pt, 주석 9pt, 줄간격 160% |
| 분량 | 본문 20장 이상 (표지·목차·참고문헌 제외) |
| 인용 | 각주 필수, 참고문헌은 목록으로 |
| 표절검사 | 카피킬러 유사도 30% 이하, 결과보고서 첨부 |
| 제출 | itrade@dongguk.edu, 파일명 `(국제통상학과)학번_이름` |

> ⚠️ 위 규정은 2024학년도 공지 기준입니다. **최신 졸업논문 공지를 학과에 재확인**하세요.

---

## 🧪 테스트

```bash
python smoke_test.py
```
7개 모듈 로직 + 각주 `.docx` 생성 + 접속코드 격리를 검증합니다.

---

## 🗺️ 로드맵

- [x] 7개 모듈 MVP + 동국대 양식 `.docx` 내보내기
- [x] provider-agnostic LLM 백엔드
- [x] 접속코드 기반 프로젝트 분리
- [x] 주제 검증기 — OpenAlex 실연동(포화도·유사도·자료확보 점검)
- [ ] KCI/RISS 국문 논문 연동 강화
- [ ] 출처 자동 수집(UN Comtrade / KITA 공개 API)
- [ ] `.hwp` 내보내기
- [ ] 인용 중복·교차참조 자동 점검

---

## 🤝 기여

[CONTRIBUTING.md](CONTRIBUTING.md)를 참고하세요. 이슈·PR 환영합니다.

## 📄 라이선스

[MIT](LICENSE)

## ⚖️ 면책

학술 무결성을 지키기 위한 도구입니다. 모든 본문은 사용자 본인이 작성해야 하며, 제출 전 소속 기관의 표절·연구윤리 규정과 표절검사 결과를 반드시 확인하세요. 본 도구 사용으로 인한 결과의 책임은 사용자에게 있습니다.
