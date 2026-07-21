# -*- coding: utf-8 -*-
"""공통 계보(lineage) 유틸 (v2.4)
파일 '바이트 전체'의 SHA-256을 사용 — 특정 컬럼만 해싱하던 v2.3의 구멍
(rating·tokens·source_type 변조 미탐지)을 파일 단위로 봉인.

체인 구조:
  metadata.json        run_id, raw_csv_hash
  preprocess_meta.json run_id, raw_csv_hash, clean_csv_hash
  painpoints_meta.json run_id, clean_csv_hash, painpoints_csv_hash
각 단계는 이전 단계 메타의 run_id·해시를 검증한 뒤에만 진행한다.
"""
import hashlib
import json
from pathlib import Path


def file_sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, obj) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def require_meta(path: Path, what: str) -> dict:
    """메타 파일 부재/손상 시 명확히 중단 — 계보 없는 산출물은 신뢰하지 않음"""
    if not path.exists():
        raise FileNotFoundError(
            f"{path.name} 없음 — {what}의 출처와 실행 계보를 확인할 수 없습니다. "
            f"이전 단계를 다시 실행하세요.")
    try:
        return load_json(path)
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"{path.name} 손상({type(e).__name__}) — 이전 단계를 다시 실행하세요.") from e


def verify_hash(actual_file: Path, expected_hash: str, what: str) -> None:
    actual = file_sha256(actual_file)
    if actual != expected_hash:
        raise ValueError(
            f"{actual_file.name} 이 계보 기록과 불일치 — {what}. "
            f"이전 실행의 잔존물일 수 있으니 파이프라인을 처음부터 다시 실행하세요.")
