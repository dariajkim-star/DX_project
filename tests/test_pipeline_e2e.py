# -*- coding: utf-8 -*-
"""파이프라인 E2E 회귀 — 데모 모드 01→05를 임시 폴더 사본에서 실행.
저장소의 data/를 건드리지 않고, 계보 체인·가드가 실제 실행에서 유지되는지 본다.
(느림: sklearn 로드 포함 수십 초 — `pytest -m "not slow"` 로 제외 가능)"""
import json
import os
import shutil
import subprocess
import sys

import pytest

from conftest import PIPELINE_DIR

pytestmark = pytest.mark.slow

SCRIPTS = ["01_collect.py", "02_preprocess.py", "03_embedding.py", "05_painpoint.py"]


@pytest.fixture
def workdir(tmp_path):
    for f in list(PIPELINE_DIR.glob("0*.py")) + [PIPELINE_DIR / "lineage.py",
                                                 PIPELINE_DIR / "model_config.py"]:
        shutil.copy(f, tmp_path / f.name)
    return tmp_path


def run(workdir, script, *args, expect_fail=False):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([sys.executable, script, *args], cwd=workdir,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env, timeout=300)
    if expect_fail:
        assert r.returncode != 0, f"{script} 실패했어야 함:\n{r.stdout}"
    else:
        assert r.returncode == 0, f"{script} 실패:\n{r.stdout}\n{r.stderr}"
    return (r.stdout or "") + (r.stderr or "")


def test_demo_pipeline_and_lineage_chain(workdir):
    run(workdir, "01_collect.py", "--demo")
    run(workdir, "02_preprocess.py")
    run(workdir, "03_embedding.py")
    run(workdir, "05_painpoint.py")

    data = workdir / "data"
    meta = json.loads((data / "metadata.json").read_text(encoding="utf-8"))
    prep = json.loads((data / "preprocess_meta.json").read_text(encoding="utf-8"))
    ppm = json.loads((data / "painpoints_meta.json").read_text(encoding="utf-8"))

    # 계보 체인 정합
    assert meta["status"] == "ok" and meta["source_type"] == "synthetic_demo"
    assert meta["run_id"] == prep["run_id"] == ppm["run_id"]
    assert meta["raw_csv_hash"] == prep["raw_csv_hash"]
    assert prep["clean_csv_hash"] == ppm["clean_csv_hash"]
    # 산출물 스키마
    head = (data / "painpoints.csv").read_text(encoding="utf-8-sig").splitlines()[0]
    assert "대표리뷰" in head
    assert (data / "strengths.csv").exists()
    assert ppm["sentiment_method"] in ("deep_learning", "rating_fallback")


def test_stale_clean_rejected_after_new_collect(workdir):
    """위험 시나리오(3차): 과거 clean 잔존 + 새 01만 실행 → 05가 거부"""
    run(workdir, "01_collect.py", "--demo")
    run(workdir, "02_preprocess.py")
    run(workdir, "01_collect.py", "--demo")  # 새 run_id — 02 재실행 안 함
    out = run(workdir, "05_painpoint.py", expect_fail=True)
    assert "run_id 불일치" in out


def test_02_rejects_when_metadata_missing(workdir):
    run(workdir, "01_collect.py", "--demo")
    (workdir / "data" / "metadata.json").unlink()
    out = run(workdir, "02_preprocess.py", expect_fail=True)
    assert "계보" in out
