# -*- coding: utf-8 -*-
"""Epic 5 경계 강제 — 처방 트랙은 DB를 영원히 모른다 (Story 5.1, 회의 §7).

1.3의 AST 검사기 계보(2.1 전송 라이브러리 감시 재사용) — 토큰만 DB 계열로 교체.
"서버가 원본을 갖지 않는다"(FR7)와 "우리는 DB를 쓴다, 단 이 데이터에만"이
공존할 수 있는 근거가 이 테스트다: 경계가 말이 아니라 코드로 강제된다.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# DB 계열 모듈 토큰 — 처방 트랙에 하나라도 나타나면 실패
DB_TOKENS = ("psycopg", "psycopg2", "sqlalchemy", "asyncpg", "pg8000",
             "sqlite3", "pymysql", "mysql")

# 처방 트랙 + 데모(발표 표면) — DB 무지(無知) 대상
PRESCRIPTION_DIRS = ("home_profile", "appliance_sim")


def _imports_of(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                yield a.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module.split(".")[0]


def _py_files(dirname):
    return sorted((ROOT / dirname).rglob("*.py"))


def test_prescription_track_never_imports_db():
    """home_profile/·appliance_sim/ 어디에도 DB 드라이버 import가 없다."""
    offenders = []
    for d in PRESCRIPTION_DIRS:
        for f in _py_files(d):
            for mod in _imports_of(f):
                if mod in DB_TOKENS:
                    offenders.append(f"{f.relative_to(ROOT)}: {mod}")
    assert offenders == [], f"처방 트랙에 DB import 발견: {offenders}"


def test_demo_scripts_never_import_db():
    """발표 표면(demo_*.py·demo_ui.py)도 DB를 모른다."""
    offenders = []
    for f in sorted(ROOT.glob("demo_*.py")):
        for mod in _imports_of(f):
            if mod in DB_TOKENS:
                offenders.append(f"{f.name}: {mod}")
    assert offenders == [], f"데모 표면에 DB import 발견: {offenders}"


def test_db_loader_never_imports_prescription():
    """역방향 — 발견 트랙 적재기는 처방 트랙을 import하지 않는다 (기존 트랙 분리 규약)."""
    offenders = []
    db_dir = ROOT / "db"
    if not db_dir.exists():
        return
    for f in sorted(db_dir.rglob("*.py")):
        for mod in _imports_of(f):
            if mod in ("home_profile", "appliance_sim"):
                offenders.append(f"{f.relative_to(ROOT)}: {mod}")
    assert offenders == [], f"발견 트랙이 처방 트랙을 import: {offenders}"


def test_schema_has_synthetic_flag():
    """mart.segments에 is_synthetic NOT NULL — 합성 패널 표기(NFR6)는 자료구조에 산다."""
    schema = (ROOT / "db" / "schema.sql").read_text(encoding="utf-8")
    assert "is_synthetic" in schema
    assert "boolean NOT NULL" in schema


def test_gate_contract_in_schema():
    """ops.runs는 passed만 허용 — '실패 run을 넣고 거르지 않는다'가 CHECK로 존재."""
    schema = (ROOT / "db" / "schema.sql").read_text(encoding="utf-8")
    assert "CHECK (gate_status = 'passed')" in schema
