# -*- coding: utf-8 -*-
"""Epic 5 Story 5.2 — 게이트 통과분만 적재.

    python db/load_mart.py [--run-dir out_moa/<타임스탬프>]

"검증을 통과하지 못한 데이터는 DB에 존재하지 않는다" — run_manifest.json의
gate_status가 'passed'가 아니면 이 스크립트는 아무것도 적재하지 않고 실패한다.
test_gate.py 22개는 불변이며, DB는 그 게이트의 하류다(회의 §8.2).

의존성 원칙: Python DB 드라이버를 쓰지 않는다 — 변환된 CSV를 컨테이너의
psql \\copy로 흘린다. 경계 테스트(test_db_boundary)가 지키는 "발견 트랙도
처방 트랙을 모른다"에 더해, 이 파일은 표준 라이브러리만 쓴다.
"""
import argparse
import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ["docker", "compose", "-f", str(ROOT / "db" / "compose.yml")]
DATA = ROOT / "dx_pipeline_v2.2" / "data"
OUT = ROOT / "dx_pipeline_v2.2" / "out"


def _psql(sql: str, stdin_path: Path = None) -> subprocess.CompletedProcess:
    cmd = COMPOSE + ["exec", "-T", "db",
                     "psql", "-U", "analyst", "-d", "discovery",
                     "-v", "ON_ERROR_STOP=1", "-c", sql]
    stdin = open(stdin_path, "rb") if stdin_path else None
    try:
        return subprocess.run(cmd, stdin=stdin, capture_output=True, text=True)
    finally:
        if stdin:
            stdin.close()


def _copy(table: str, cols: list, rows: list) -> int:
    """행 목록 → 임시 CSV → \\copy. 반환 적재 행수."""
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="",
                                     suffix=".csv", delete=False) as tf:
        w = csv.writer(tf)
        w.writerows(rows)
        tmp = Path(tf.name)
    try:
        r = _psql(f"\\copy {table} ({', '.join(cols)}) FROM STDIN "
                  f"WITH (FORMAT csv)", stdin_path=tmp)
        if r.returncode != 0:
            print(f"[FAIL] {table}: {r.stderr.strip()[:300]}")
            return -1
        return len(rows)
    finally:
        tmp.unlink(missing_ok=True)


def _read(path: Path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _latest_passed_run() -> Path:
    """가장 최근의 gate passed run 폴더. 없으면 None."""
    runs = sorted((ROOT / "out_moa").glob("*/run_manifest.json"), reverse=True)
    for m in runs:
        mf = json.loads(m.read_text(encoding="utf-8"))
        if mf.get("gate_status") == "passed":
            return m.parent
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="게이트 통과분만 적재 (Epic 5)")
    ap.add_argument("--run-dir", help="out_moa/<타임스탬프> (기본: 최신 passed)")
    args = ap.parse_args(argv)

    run_dir = Path(args.run_dir) if args.run_dir else _latest_passed_run()
    if run_dir is None or not (run_dir / "run_manifest.json").exists():
        print("[FAIL] gate passed인 run을 찾지 못함 — 아무것도 적재하지 않는다")
        return 1
    mf = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    if mf.get("gate_status") != "passed":
        print(f"[FAIL] run {mf.get('run_id')}: gate_status="
              f"{mf.get('gate_status')!r} — 게이트 하류 계약 위반, 적재 거부")
        return 1
    run_id = mf["run_id"]

    # ops.runs — FK 부모 먼저. 재실행 대비 멱등(이미 있으면 성공 처리).
    r = _psql("INSERT INTO ops.runs "
              "(run_id, created_at, data_mode, source_type, gate_status, agent_results) "
              f"VALUES ('{run_id}', '{mf['created_at']}', '{mf['data_mode']}', "
              f"'{mf['source_type']}', '{mf['gate_status'].replace('passed','passed')}', "
              f"'{json.dumps(mf.get('agents', {}), ensure_ascii=False).replace(chr(39), chr(39)*2)}'::jsonb) "
              "ON CONFLICT (run_id) DO NOTHING")
    if r.returncode != 0:
        print(f"[FAIL] ops.runs: {r.stderr.strip()[:300]}")
        return 1
    print(f"ops.runs        <- run {run_id} (gate passed)")

    loaded = {}

    rows = [[run_id, x["review"], x["rating"] or None, x["date"] or None,
             x["likes"] or None, x["source_type"], x["tokens"]]
            for x in _read(DATA / "reviews_clean.csv")]
    loaded["mart.reviews"] = _copy(
        "mart.reviews",
        ["run_id", "review", "rating", "review_date", "likes", "source_type", "tokens"],
        rows)

    rows = [[run_id, x["PainPoint(토픽)"], x["빈도"], x["평균평점"],
             x["언급률_전체부정기준(%)"], x["언급률_배정기준(%)"], x["대표리뷰"]]
            for x in _read(DATA / "painpoints.csv")]
    loaded["mart.painpoints"] = _copy(
        "mart.painpoints",
        ["run_id", "topic", "freq", "avg_rating", "mention_all_neg",
         "mention_assigned", "rep_review"], rows)

    s_path = DATA / "strengths.csv"
    if s_path.exists():
        srows = _read(s_path)
        if srows:
            cols = list(srows[0].keys())
            rows = [[run_id, x.get(cols[0], ""), x.get("빈도") or None,
                     x.get("평균평점") or None, x.get("대표리뷰", "")]
                    for x in srows]
            loaded["mart.strengths"] = _copy(
                "mart.strengths",
                ["run_id", "topic", "freq", "avg_rating", "rep_review"], rows)

    c_path = DATA / "crawl_playstore_smartthings.csv"
    if c_path.exists():
        rows = [[run_id, x.get("review", ""), x.get("rating") or None,
                 x.get("date") or None, "smartthings"]
                for x in _read(c_path)]
        loaded["mart.competitor_reviews"] = _copy(
            "mart.competitor_reviews",
            ["run_id", "review", "rating", "review_date", "app"], rows)

    seg_path = OUT / "seg_members.csv"
    if seg_path.exists():
        rows = [[run_id, x["응답번호"], x["LG가전수"], x["앱사용빈도"], x["연령대"],
                 x["자녀유무"], x["점유형태_전월세"], x["이사계획"], x["구매계기_혼수"],
                 x["P1경험"], x["P2경험"], x["P3부담"], x["워치보유"], x["야간사용"],
                 x["온바디수용도"], x["지불의사"], x["segment"],
                 "true"]   # ⚠️ NFR6: 현재 세그먼트는 전부 합성 패널 — 실설문 도착 시 갱신
                for x in _read(seg_path)]
        loaded["mart.segments"] = _copy(
            "mart.segments",
            ["run_id", "respondent_id", "lg_devices", "app_freq", "age_band",
             "has_child", "is_renter", "move_plan", "bought_wedding", "p1_exp",
             "p2_exp", "p3_burden", "has_watch", "night_use", "onbody_intent",
             "pay_intent", "segment", "is_synthetic"], rows)

    n_path = DATA / "naver_testimony.csv"
    if n_path.exists():
        nrows = _read(n_path)
        if nrows:
            first_col = list(nrows[0].keys())[0]
            rows = [[run_id, x[first_col]] for x in nrows]
            loaded["mart.naver_testimony"] = _copy(
                "mart.naver_testimony", ["run_id", "testimony"], rows)

    print()
    fails = [t for t, n in loaded.items() if n < 0]
    for t, n in loaded.items():
        print(f"  {t:28s} {'FAIL' if n < 0 else f'{n:,}행'}")
    if fails:
        print(f"\n[FAIL] {len(fails)}개 테이블 적재 실패")
        return 1
    print("\n적재 완료 — 전부 gate passed run의 하류다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
