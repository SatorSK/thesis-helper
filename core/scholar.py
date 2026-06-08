"""학술 DB 클라이언트 (OpenAlex + 선택적 KCI).

프로덕션 지향: 커넥션 재사용, 자동 재시도(지수백오프), 타임아웃, polite pool,
on-disk 캐시(TTL). 네트워크 실패는 예외가 아니라 구조화된 결과로 돌려준다.

OpenAlex는 API 키 없이 동작한다(polite pool용 mailto만 권장). KCI는 키가 있을 때만.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Optional

import requests
from requests.adapters import HTTPAdapter

try:  # urllib3 v1/v2 호환
    from urllib3.util.retry import Retry
except Exception:  # pragma: no cover
    from requests.packages.urllib3.util.retry import Retry  # type: ignore

OPENALEX = "https://api.openalex.org"
USER_AGENT = "thesis-helper/1.0 (https://github.com/SatorSK/thesis-helper)"
TIMEOUT = 20
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cache", "scholar")
CACHE_TTL = 7 * 24 * 3600  # 7일


# ---------------------------------------------------------------- 데이터 모델
@dataclass
class Work:
    id: str
    title: str
    year: Optional[int]
    cited_by: int
    abstract: str
    authors: list[str] = field(default_factory=list)
    venue: str = ""
    doi: str = ""
    source: str = "openalex"  # openalex | kci

    @property
    def url(self) -> str:
        if self.doi:
            return f"https://doi.org/{self.doi}"
        return self.id


@dataclass
class ScholarError:
    message: str
    kind: str = "network"  # network | http | empty


# ---------------------------------------------------------------- HTTP 세션
_session: Optional[requests.Session] = None


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.8,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET"]),
            respect_retry_after_header=True,
        )
        s.mount("https://", HTTPAdapter(max_retries=retry))
        s.headers.update({"User-Agent": USER_AGENT})
        _session = s
    return _session


# ---------------------------------------------------------------- 캐시
def _cache_path(key: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return os.path.join(CACHE_DIR, f"{h}.json")


def _cache_get(key: str):
    path = _cache_path(key)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            blob = json.load(f)
        if time.time() - blob.get("_ts", 0) > CACHE_TTL:
            return None
        return blob.get("data")
    except Exception:
        return None


def _cache_put(key: str, data) -> None:
    try:
        with open(_cache_path(key), "w", encoding="utf-8") as f:
            json.dump({"_ts": time.time(), "data": data}, f, ensure_ascii=False)
    except Exception:
        pass  # 캐시는 best-effort


def _request(url: str, params: dict, cache_key: str):
    """GET + 캐시. 성공 시 dict, 실패 시 ScholarError."""
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    try:
        r = _get_session().get(url, params=params, timeout=TIMEOUT)
    except requests.RequestException as e:
        return ScholarError(f"네트워크 오류: {e}", "network")
    if r.status_code >= 400:
        return ScholarError(f"HTTP {r.status_code}: {r.text[:200]}", "http")
    try:
        data = r.json()
    except ValueError:
        return ScholarError("응답 JSON 파싱 실패", "http")
    _cache_put(cache_key, data)
    return data


# ---------------------------------------------------------------- 유틸
def _abstract_from_inverted(inv: Optional[dict]) -> str:
    if not inv:
        return ""
    positions: list[tuple[int, str]] = []
    for word, idxs in inv.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort()
    return " ".join(w for _, w in positions)


def _polite_params(mailto: str) -> dict:
    return {"mailto": mailto} if mailto else {}


# ---------------------------------------------------------------- OpenAlex API
def counts_by_year(query: str, mailto: str = "", api_key: str = ""):
    """주제의 연도별 논문 수. 성공 시 {year:int -> count:int}, 실패 시 ScholarError."""
    params = {
        "search": query,
        "group_by": "publication_year",
        "per_page": 1,
    }
    params.update(_polite_params(mailto))
    if api_key:
        params["api_key"] = api_key
    data = _request(f"{OPENALEX}/works", params, f"counts::{query}")
    if isinstance(data, ScholarError):
        return data
    out: dict[int, int] = {}
    for g in data.get("group_by", []):
        key = g.get("key")
        try:
            out[int(key)] = int(g.get("count", 0))
        except (TypeError, ValueError):
            continue
    return out


def total_count(query: str, mailto: str = "", api_key: str = ""):
    params = {"search": query, "per_page": 1}
    params.update(_polite_params(mailto))
    if api_key:
        params["api_key"] = api_key
    data = _request(f"{OPENALEX}/works", params, f"total::{query}")
    if isinstance(data, ScholarError):
        return data
    return int(data.get("meta", {}).get("count", 0))


def top_works(query: str, n: int = 25, mailto: str = "", api_key: str = ""):
    """관련도 상위 논문. 성공 시 list[Work], 실패 시 ScholarError."""
    params = {
        "search": query,
        "per_page": max(1, min(n, 50)),
        "sort": "relevance_score:desc",
        "select": "id,title,publication_year,cited_by_count,abstract_inverted_index,authorships,primary_location,doi",
    }
    params.update(_polite_params(mailto))
    if api_key:
        params["api_key"] = api_key
    data = _request(f"{OPENALEX}/works", params, f"top::{n}::{query}")
    if isinstance(data, ScholarError):
        return data
    works = []
    for w in data.get("results", []):
        authors = [
            (a.get("author") or {}).get("display_name", "")
            for a in (w.get("authorships") or [])
        ][:5]
        venue = ((w.get("primary_location") or {}).get("source") or {}).get("display_name", "") or ""
        doi = (w.get("doi") or "").replace("https://doi.org/", "")
        works.append(Work(
            id=w.get("id", ""),
            title=w.get("title") or "(제목 없음)",
            year=w.get("publication_year"),
            cited_by=int(w.get("cited_by_count", 0)),
            abstract=_abstract_from_inverted(w.get("abstract_inverted_index")),
            authors=[a for a in authors if a],
            venue=venue,
            doi=doi,
            source="openalex",
        ))
    return works


# ---------------------------------------------------------------- KCI (선택)
KCI_BASE = "https://open.kci.go.kr/po/openapi/openApiSearch.kci"


def kci_total_count(query: str, kci_key: str):
    """KCI 국문 논문 수(키 필요). 성공 시 int, 실패/무키 시 ScholarError.

    KCI Open API 스펙은 기관별 발급 키에 따라 다를 수 있어 best-effort로 처리한다.
    """
    if not kci_key:
        return ScholarError("KCI 키 없음", "empty")
    params = {
        "apiCode": "articleSearch",
        "key": kci_key,
        "title": query,
        "displayCount": 1,
    }
    data = _request(KCI_BASE, params, f"kci::{query}")
    if isinstance(data, ScholarError):
        return data
    # KCI는 XML을 주는 경우가 많아 JSON 파싱이 실패할 수 있음 → 호출부에서 ScholarError 처리
    try:
        return int(data.get("outputData", {}).get("total", 0))
    except Exception:
        return ScholarError("KCI 응답 형식 해석 실패(키/스펙 확인 필요)", "http")
