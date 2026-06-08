"""주제↔논문 의미 유사도 백엔드 (우아한 단계적 강등).

프로덕션/배포 환경에 따라 무거운 의존성이 없을 수 있으므로 3단계로 강등한다:
  1) sentence-transformers (설치돼 있으면) — 진짜 의미 임베딩, 최상
  2) scikit-learn TF-IDF (requirements 포함) — 가볍고 안정적, 기본값
  3) 어휘 기반 Jaccard (아무것도 없을 때) — 최후 폴백, 의존성 0

모든 백엔드는 query 하나와 docs 리스트를 받아 0~1 유사도 리스트를 돌려준다.
"""
from __future__ import annotations

import math
import re
from functools import lru_cache

_ST_MODEL = None
_ST_TRIED = False


def backend_name() -> str:
    if _load_st() is not None:
        return "sentence-transformers"
    if _has_sklearn():
        return "tfidf"
    return "lexical"


def _load_st():
    """sentence-transformers 모델 로드 시도(1회). 없으면 None."""
    global _ST_MODEL, _ST_TRIED
    if _ST_TRIED:
        return _ST_MODEL
    _ST_TRIED = True
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        _ST_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        _ST_MODEL = None
    return _ST_MODEL


@lru_cache(maxsize=1)
def _has_sklearn() -> bool:
    try:
        import sklearn  # noqa: F401
        return True
    except Exception:
        return False


def similarities(query: str, docs: list[str]) -> list[float]:
    """query와 각 doc의 유사도(0~1). 백엔드는 자동 선택."""
    docs = [d or "" for d in docs]
    if not docs:
        return []
    model = _load_st()
    if model is not None:
        return _st_similarities(model, query, docs)
    if _has_sklearn():
        return _tfidf_similarities(query, docs)
    return [_jaccard(query, d) for d in docs]


def _st_similarities(model, query, docs):
    try:
        import numpy as np  # noqa
        emb = model.encode([query] + docs, normalize_embeddings=True)
        q = emb[0]
        return [float(max(0.0, (q * emb[i + 1]).sum())) for i in range(len(docs))]
    except Exception:
        return [_jaccard(query, d) for d in docs]


def _tfidf_similarities(query, docs):
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        vec = TfidfVectorizer(stop_words="english", max_features=20000)
        mat = vec.fit_transform([query] + docs)
        sims = cosine_similarity(mat[0:1], mat[1:]).ravel()
        return [float(max(0.0, s)) for s in sims]
    except Exception:
        return [_jaccard(query, d) for d in docs]


_TOKEN = re.compile(r"[A-Za-z가-힣0-9]+")


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN.findall(text or "") if len(t) > 1}


def _jaccard(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0
