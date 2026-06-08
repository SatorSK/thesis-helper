# 기여 가이드

## 개발 환경

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 변경 전 확인

PR 전에 스모크 테스트를 통과시켜 주세요:

```bash
python smoke_test.py
```

## 구조 원칙

- **모듈 = 기능 단위.** 각 모듈(`modules/m*.py`)은 `render(project, cfg)` 하나를 노출하고, 공유 상태 `project`(dict)를 읽고/씁니다.
- **상태 저장은 `core/project.py`만** 담당합니다. 모듈에서 직접 파일 IO 하지 마세요.
- **LLM 호출은 `core/llm.py`의 `complete()` / `complete_json()`만** 사용합니다. 특정 벤더 SDK를 모듈에 직접 import 하지 마세요.
- **무결성 원칙을 깨지 마세요.** 초안 텍스트는 절대 최종 `.docx`로 내보내지지 않아야 하고, 유사도 차단 로직(⑤·⑦)을 우회하는 기능은 받지 않습니다.

## 커밋 메시지

간결한 한 줄 요약 + 필요 시 본문. 예: `M4: CSV cp949 인코딩 폴백 추가`

## 이슈

버그 리포트에는 재현 절차와 `python smoke_test.py` 결과를 함께 적어주세요.
