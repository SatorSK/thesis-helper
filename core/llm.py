"""Provider-agnostic LLM 어댑터.

특정 회사에 묶지 않는다. 하나의 함수 complete(prompt, system, cfg) 로 통일하고
백엔드만 갈아끼운다. 모든 호출은 requests 기반 REST 라 SDK 의존성이 없다.

지원 백엔드:
  - "template" : LLM 미사용. 키 없이 동작(기본값). complete() 호출 시 예외.
  - "openai"   : OpenAI / Codex / OpenAI 호환 (base_url 변경 가능)
  - "anthropic": Claude
  - "gemini"   : Google Gemini
  - "local"    : OpenAI 호환 로컬 서버(Ollama, LM Studio 등)

API 키는 호출 시점에만 전달받고 어디에도 저장하지 않는다.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import requests

BACKENDS = ["template", "openai", "anthropic", "gemini", "local"]

DEFAULTS = {
    "openai": {"base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
    "anthropic": {"base_url": "https://api.anthropic.com", "model": "claude-3-5-sonnet-20241022"},
    "gemini": {"base_url": "https://generativelanguage.googleapis.com/v1beta", "model": "gemini-1.5-flash"},
    "local": {"base_url": "http://localhost:11434/v1", "model": "llama3.1"},
}

TIMEOUT = 90


@dataclass
class LLMConfig:
    backend: str = "template"
    api_key: str = ""
    model: str = ""
    base_url: str = ""

    def resolved_model(self) -> str:
        return self.model or DEFAULTS.get(self.backend, {}).get("model", "")

    def resolved_base(self) -> str:
        return self.base_url or DEFAULTS.get(self.backend, {}).get("base_url", "")


def is_enabled(cfg: LLMConfig) -> bool:
    """실제 LLM 호출이 가능한 상태인가? (local 은 키 불필요)"""
    if cfg.backend == "template":
        return False
    if cfg.backend == "local":
        return True
    return bool(cfg.api_key)


class LLMError(RuntimeError):
    pass


def complete(prompt: str, system: str, cfg: LLMConfig) -> str:
    if not is_enabled(cfg):
        raise LLMError("LLM 백엔드가 설정되지 않았습니다(템플릿 모드).")
    try:
        if cfg.backend in ("openai", "local"):
            return _openai_chat(prompt, system, cfg)
        if cfg.backend == "anthropic":
            return _anthropic(prompt, system, cfg)
        if cfg.backend == "gemini":
            return _gemini(prompt, system, cfg)
    except requests.RequestException as e:
        raise LLMError(f"네트워크/요청 오류: {e}") from e
    raise LLMError(f"알 수 없는 백엔드: {cfg.backend}")


def _openai_chat(prompt: str, system: str, cfg: LLMConfig) -> str:
    url = cfg.resolved_base().rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if cfg.api_key:
        headers["Authorization"] = f"Bearer {cfg.api_key}"
    body = {
        "model": cfg.resolved_model(),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
    }
    r = requests.post(url, headers=headers, json=body, timeout=TIMEOUT)
    if r.status_code >= 400:
        raise LLMError(f"OpenAI({r.status_code}): {r.text[:300]}")
    return r.json()["choices"][0]["message"]["content"]


def _anthropic(prompt: str, system: str, cfg: LLMConfig) -> str:
    url = cfg.resolved_base().rstrip("/") + "/v1/messages"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": cfg.api_key,
        "anthropic-version": "2023-06-01",
    }
    body = {
        "model": cfg.resolved_model(),
        "max_tokens": 2000,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
    }
    r = requests.post(url, headers=headers, json=body, timeout=TIMEOUT)
    if r.status_code >= 400:
        raise LLMError(f"Anthropic({r.status_code}): {r.text[:300]}")
    parts = r.json().get("content", [])
    return "".join(p.get("text", "") for p in parts)


def _gemini(prompt: str, system: str, cfg: LLMConfig) -> str:
    base = cfg.resolved_base().rstrip("/")
    model = cfg.resolved_model()
    url = f"{base}/models/{model}:generateContent?key={cfg.api_key}"
    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"parts": [{"text": prompt}]}],
    }
    r = requests.post(url, json=body, timeout=TIMEOUT)
    if r.status_code >= 400:
        raise LLMError(f"Gemini({r.status_code}): {r.text[:300]}")
    cands = r.json().get("candidates", [])
    if not cands:
        raise LLMError("Gemini 응답이 비었습니다.")
    return "".join(p.get("text", "") for p in cands[0]["content"]["parts"])


def complete_json(prompt: str, system: str, cfg: LLMConfig):
    """JSON 응답을 기대하는 호출. 코드블록/잡텍스트를 벗겨 파싱한다."""
    raw = complete(prompt + "\n\n반드시 유효한 JSON만 출력하세요.", system, cfg)
    return _extract_json(raw)


def _extract_json(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()
    # 첫 { 또는 [ 부터 마지막 } 또는 ] 까지
    start = min([i for i in (text.find("{"), text.find("[")) if i >= 0], default=-1)
    end = max(text.rfind("}"), text.rfind("]"))
    if start >= 0 and end > start:
        text = text[start:end + 1]
    return json.loads(text)
