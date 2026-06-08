"""프로젝트 상태 모델 + 로컬 저장/불러오기.

논문 한 편 = 프로젝트 하나. 모든 모듈이 공유하는 단일 상태 dict를
project.json 에 저장한다. API 키 등 민감정보는 절대 저장하지 않는다.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import date

# 프로젝트들이 저장되는 루트 (앱 실행 폴더 기준)
PROJECTS_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "projects")


def space_id(code: str) -> str:
    """접속코드 → 폴더-안전 네임스페이스 해시. 코드 자체는 저장하지 않는다.

    공개 배포 시 같은 코드를 쓰는 사람끼리만 프로젝트를 공유/조회한다.
    진짜 인증이 아니라 '간단한 분리'다(코드를 아는 사람은 접근 가능).
    """
    code = (code or "").strip()
    if not code:
        return "_default"
    return "u_" + hashlib.sha256(code.encode("utf-8")).hexdigest()[:12]


def _empty_project(name: str, space: str = "_default") -> dict:
    return {
        "name": name,
        "space": space,
        "meta": {
            "title": "",
            "author": "",
            "student_id": "",
            "advisor": "",
            "dept": "국제통상학과",
            "date": date.today().isoformat(),
        },
        "topic": {
            "selected": "",   # 확정된 주제 제목
            "rq": "",         # 연구질문
            "candidates": [],  # M1이 생성한 후보 [{title, novelty, data, lit, rq, sources}]
        },
        # 참고문헌: [{id, type, authors, year, title, container, volume, issue,
        #            pages, publisher, place, url, doi, accessed}]
        "sources": [],
        # 목차: [{id, level, title, purpose, checklist:[str]}]
        "outline": [],
        # 데이터 메모: [{title, caption, figure_file, summary}]
        "data_notes": [],
        # 단락: { section_id: {draft, user_text, cite_ids:[str]} }
        "paragraphs": {},
        # 백엔드 선택만 저장(키는 저장 안 함)
        "settings": {"llm_backend": "template", "model": "", "base_url": ""},
    }


def slugify(name: str) -> str:
    s = re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", name.strip())
    return s.strip("_") or "untitled"


def project_dir(name: str, space: str = "_default") -> str:
    return os.path.join(PROJECTS_ROOT, slugify(space), slugify(name))


def figures_dir(name: str, space: str = "_default") -> str:
    d = os.path.join(project_dir(name, space), "figures")
    os.makedirs(d, exist_ok=True)
    return d


def list_projects(space: str = "_default") -> list[str]:
    base = os.path.join(PROJECTS_ROOT, slugify(space))
    if not os.path.isdir(base):
        return []
    out = []
    for d in sorted(os.listdir(base)):
        if os.path.isfile(os.path.join(base, d, "project.json")):
            out.append(d)
    return out


def load(name: str, space: str = "_default") -> dict:
    path = os.path.join(project_dir(name, space), "project.json")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return _migrate(data, space)
    return _empty_project(name, space)


def save(project: dict) -> str:
    space = project.get("space", "_default")
    d = project_dir(project["name"], space)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "project.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(project, f, ensure_ascii=False, indent=2)
    return path


def new_project(name: str, space: str = "_default") -> dict:
    p = _empty_project(name, space)
    save(p)
    return p


def _migrate(data: dict, space: str = "_default") -> dict:
    """예전 버전 project.json 에 빠진 키를 채워 호환성 유지."""
    data.setdefault("space", space)
    base = _empty_project(data.get("name", "untitled"), space)
    for k, v in base.items():
        if k not in data:
            data[k] = v
        elif isinstance(v, dict):
            for kk, vv in v.items():
                data[k].setdefault(kk, vv)
    return data


# ----- 분량 추정 (학과 규정: 본문 20장 이상) ------------------------------
# 한글 논문 11pt·160% 줄간격 A4 1페이지 ≈ 약 700자(공백 포함) 기준 추정치.
CHARS_PER_PAGE = 700


def estimate_pages(project: dict) -> float:
    total = 0
    for sec in project.get("paragraphs", {}).values():
        total += len(sec.get("user_text", "") or "")
    return round(total / CHARS_PER_PAGE, 1)
