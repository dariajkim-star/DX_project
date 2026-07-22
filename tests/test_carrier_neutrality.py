# -*- coding: utf-8 -*-
"""캐리어 중립 추상화 회귀 테스트 (Story 1.3).

고정하는 것:
  1. 경계 위반 탐지 (AC2) — 코어 모듈 AST에 벤더 import가 없다.
     검사기 자체의 스텁 판별: 벤더 import를 주입한 가짜 소스에서 실제로 실패한다.
  2. 어댑터 계약 (AC1·AC3) — 예외 금지, 한계 실제 강제, 왕복 무손실.
  3. 미구현 정직 표기 (AC4) — UNIMPLEMENTED 어댑터는 모든 연산이 실패하고
     데이터를 반환하는 경로가 없다. 미확인 capability는 None이며 False로 붕괴하지 않는다.

Story 1.1 리뷰 교훈 적용: '단어 언급' 단언 금지 원칙이되, AC4의 문면이
"오류 문구에 '미구현' 포함"을 요구하는 지점만 예외적으로 문구를 단언한다
(그 단언 대상 자체가 표기 규약이기 때문).
"""
import ast
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import home_profile  # noqa: E402
from home_profile import serialize, deserialize, validate_profile  # noqa: E402
from home_profile import storage as st  # noqa: E402
from home_profile.carrier import (  # noqa: E402
    Carrier,
    CarrierCapabilities,
    CarrierStatus,
    CapabilityValue,
    MemoryCarrier,
)
from home_profile.carriers.garmin import GarminConnectIQCarrier  # noqa: E402

# ---------- 1. 경계 위반 탐지 (AC2) ----------

# 코어 모듈: 벤더 import 금지 대상. 어댑터 모듈(home_profile/carriers/)은
# 이 검사에서 **면제**다 — 벤더 의존이 그 안에만 있는 것이 경계의 정의다.
CORE_MODULES = (
    ROOT / "home_profile" / "schema.py",
    ROOT / "home_profile" / "storage.py",
    ROOT / "home_profile" / "carrier.py",
    ROOT / "home_profile" / "__init__.py",
)
VENDOR_TOKENS = frozenset({
    "garmin", "connectiq", "monkeyc", "toybox",
    "apple", "healthkit", "watchconnectivity",
    "xiaomi", "mifit", "zepp", "samsung", "tizen", "wearable",
})


def _imported_modules(source: str) -> set:
    """AST 기반 import **모듈 경로 세그먼트** 수집. 문자열 grep이 아니다 —
    주석·docstring의 'Garmin' 언급은 위반이 아니다.

    리뷰 P3 반영:
    - 동적 import도 잡는다: importlib.import_module("…")·__import__("…")의
      문자열 리터럴 인자를 모듈 경로로 수집
    - 심볼 이름(from mylib import apple의 'apple')은 수집하지 않는다 —
      벤더 모듈에서 가져오면 module 문자열로 이미 잡히고, 심볼명 대조는
      오탐만 만든다(v1의 오탐 경로)
    """
    segments = set()

    def _add(path: str):
        segments.update(path.lower().split("."))

    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                _add(node.module)
        elif isinstance(node, ast.Call):
            fn = node.func
            is_dynamic = (
                (isinstance(fn, ast.Name) and fn.id == "__import__")
                or (isinstance(fn, ast.Attribute) and fn.attr == "import_module")
                or (isinstance(fn, ast.Name) and fn.id == "import_module")
            )
            if is_dynamic:
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        _add(arg.value)
    return segments


def _vendor_violations(source: str) -> set:
    """모듈 세그먼트에 벤더 토큰이 **부분 문자열로** 포함되면 위반.
    리뷰 P3: 정확 일치만 보던 v1은 garminconnect·garmin_sdk·pygarmin을
    전부 통과시켰다. 코어 모듈의 정당한 import는 전부 표준 라이브러리라
    부분일치 오탐은 실질적으로 없다(있다면 그게 조사 대상이다)."""
    hits = set()
    for seg in _imported_modules(source):
        for tok in VENDOR_TOKENS:
            if tok in seg:
                hits.add(tok)
    return hits


def test_core_modules_have_no_vendor_imports():
    for path in CORE_MODULES:
        assert path.exists(), f"코어 모듈 실종: {path.name}"
        violations = _vendor_violations(path.read_text(encoding="utf-8"))
        assert violations == set(), f"{path.name}: 벤더 import 발견 {violations}"


def test_checker_detects_injected_vendor_import():
    """검사기 스텁 판별 — 아무것도 안 하는 검사기도 '위반 없음'을 낸다.
    벤더 import를 주입한 가짜 소스에서 검사기가 실제로 실패함을 고정한다."""
    fake = "import garmin.connectiq\nfrom toybox import Application\n"
    assert _vendor_violations(fake) == {"garmin", "connectiq", "toybox"}
    fake2 = "from apple.watchconnectivity import WCSession\n"
    assert _vendor_violations(fake2) == {"apple", "watchconnectivity"}


def test_checker_detects_evasion_paths():
    """리뷰 P3 회귀 고정: v1이 통과시키던 회피 3종을 잡는다."""
    # 1) 동적 import
    assert "garmin" in _vendor_violations(
        'import importlib\nimportlib.import_module("garmin")\n')
    assert "garmin" in _vendor_violations('__import__("garmin.connectiq")\n')
    # 2) 부분일치 — 실제 PyPI 가민 패키지 이름들
    assert "garmin" in _vendor_violations("import garminconnect\n")
    assert "garmin" in _vendor_violations("from garmin_sdk import x\n")
    assert "garmin" in _vendor_violations("import pygarmin\n")


def test_checker_does_not_flag_symbol_names():
    """리뷰 P3 오탐 제거 고정: 심볼 이름은 대조하지 않는다 —
    from mylib import apple은 위반이 아니다(mylib이 벤더가 아니므로)."""
    assert _vendor_violations("from mylib import apple\n") == set()
    assert _vendor_violations("from utils import wearable_helper\n") == set()


def test_checker_ignores_docstring_and_comment_mentions():
    """docstring·주석의 벤더 언급은 위반이 아니다 (1.1·1.2 docstring에 실재)."""
    src = '"""Garmin Connect IQ 한계는 포럼발이다."""\n# samsung tizen\nimport json\n'
    assert _vendor_violations(src) == set()


def test_adapter_modules_are_exempt_and_exist():
    """어댑터 디렉터리는 검사 면제 대상이며 실재한다 — 경계가 디렉터리로 보인다."""
    carriers_dir = ROOT / "home_profile" / "carriers"
    assert carriers_dir.is_dir()
    assert (carriers_dir / "garmin.py").exists()
    assert not any(
        p.stem in ("apple", "xiaomi") for p in carriers_dir.glob("*.py")
    ), "빈 스텁 어댑터 금지 (Task 4) — 애플·샤오미는 문서로만 제시한다"


# ---------- 2. Capabilities 값 객체 ----------

def test_capability_value_carries_source_label():
    cv = CapabilityValue(4096, "설계보수값(포럼 8KB의 절반, 미확인)")
    assert cv.value == 4096
    assert cv.source == "설계보수값(포럼 8KB의 절반, 미확인)"


def test_garmin_capabilities_sources_are_not_official():
    """Connect IQ 한계값은 포럼발이다 — source에 '측정'/'벤더문서'로 세탁 금지."""
    caps = GarminConnectIQCarrier().capabilities()
    assert isinstance(caps, CarrierCapabilities)
    for cv in (caps.max_record_bytes, caps.max_total_bytes, caps.transfer_mtu):
        assert cv.source not in ("측정", "벤더문서")
        assert cv.source  # 라벨 자체는 반드시 존재
    # 가민 어댑터가 신고하는 값 = storage.py의 가민 상수와 정확히 일치 (이관의 정의)
    assert caps.max_record_bytes.value == st.BUDGET_PER_KEY
    assert caps.max_total_bytes.value == st.BUDGET_STORAGE_TOTAL
    assert caps.transfer_mtu.value == st.BLE_MTU


def test_unknown_capability_is_none_not_false():
    """미확인은 None이다 — False로 적으면 하지 않은 조사를 한 척하는 것."""
    caps = GarminConnectIQCarrier().capabilities()
    assert caps.supports_decompression is None
    assert caps.supports_decompression is not False


# ---------- 3. 참조 어댑터 (AC1·AC3) ----------

@pytest.fixture
def mem():
    return MemoryCarrier()


def test_memory_carrier_is_honest_about_not_being_a_device(mem):
    assert mem.status is CarrierStatus.SUPPORTED
    assert mem.is_device is False
    assert mem.label == "참조 어댑터 — 실기기 아님"
    # 리뷰 P4: 참조 어댑터의 압축 해제 신고는 True(호스트 파이썬 = zlib 존재)
    assert mem.capabilities().supports_decompression is True


def test_put_get_roundtrip_exact(mem):
    records = {"meta": b'{"v":1}', "device:dev000": b'{"t":"washer"}'}
    assert mem.put_records(records) == []
    got, errs = mem.get_records(["meta", "device:dev000"])
    assert errs == []
    assert got == records          # 바이트 등가 — '언급 여부' 단언 아님


def test_serialize_roundtrip_through_carrier(mem):
    """1.2 자산 재사용: serialize() 결과를 넣고 꺼내 deserialize() → 검증 통과.

    단일 레코드 왕복은 SMALL만 가능하다 — TYPICAL 전체(4,180B 실측)는 키당
    한계 4,096B를 넘는다. 그게 바로 기기 단위 분할(파티 결정)이 존재하는
    이유이며, 아래 test_typical_profile_needs_chunking이 그 사실을 고정한다.
    """
    profile = st.make_sample_profile(*st.SMALL)
    data, errs = serialize(profile)
    assert errs == [] and data is not None
    assert mem.put_records({"profile": data}) == []
    got, errs = mem.get_records(["profile"])
    assert errs == []
    restored, errs = deserialize(got["profile"])
    assert errs == []
    assert validate_profile(restored) == []
    assert restored == profile


def test_typical_profile_needs_chunking(mem):
    """TYPICAL 전체는 단일 레코드로 안 들어간다 — 분할 저장이 필수인 실측 근거.
    한계를 신고만 하는 어댑터라면 이 테스트가 통과해버린다(그래서 존재한다)."""
    profile = st.make_sample_profile(*st.TYPICAL)
    data, errs = serialize(profile)
    assert errs == [] and data is not None
    limit = mem.capabilities().max_record_bytes.value
    assert len(data) > limit                      # 실측: 4,180B > 4,096B
    errs = mem.put_records({"profile": data})
    assert len(errs) == 1


def test_split_chunks_roundtrip_through_carrier(mem):
    """분할 저장(파티 결정) 모양도 인터페이스가 수용한다 — TYPICAL도 조각으로는
    전부 들어간다. 1.2 미결정(분할/압축)을 인터페이스가 못 박지 않는 증거."""
    profile = st.make_sample_profile(*st.TYPICAL)
    chunks = st.split_chunks(profile)
    # 리뷰 P8: 비공개 st._dumps 대신 테스트 로컬 직렬화 — storage 내부와 절연.
    # 기준 표현(JSON UTF-8 compact)은 공개 계약이므로 여기서 재현해도 정당하다.
    def _compact(obj):
        return json.dumps(obj, ensure_ascii=False,
                          separators=(",", ":")).encode("utf-8")
    records = {name: _compact(obj) for name, obj in chunks.items()}
    assert mem.put_records(records) == []
    got, errs = mem.get_records(list(records))
    assert errs == []
    assert got == records


def test_record_limit_is_actually_enforced(mem):
    """한계를 신고만 하고 통과시키면 어댑터가 거짓말을 하는 것이다."""
    limit = mem.capabilities().max_record_bytes.value
    ok = {"fits": b"x" * limit}
    too_big = {"burst": b"x" * (limit + 1)}
    assert mem.put_records(ok) == []
    errs = mem.put_records(too_big)
    assert len(errs) == 1
    # 오류는 이름·크기·한계만 말한다 — 페이로드 값 자체는 담지 않는다
    assert "burst" in errs[0]
    assert f"{limit + 1:,}" in errs[0] and f"{limit:,}" in errs[0]
    assert "xxx" not in errs[0]
    # 거부된 레코드는 저장되지 않았다 (fail-closed)
    got, errs2 = mem.get_records(["burst"])
    assert got is None and len(errs2) == 1


def test_total_limit_is_enforced(mem):
    """리뷰 P4+P7: 나눗셈 암묵 가정 제거 + 총량은 **이름 바이트 포함**으로 판정.
    상수가 바뀌어도 경계 직전/직후를 정확히 친다."""
    limit_rec = mem.capabilities().max_record_bytes.value
    limit_total = mem.capabilities().max_total_bytes.value

    def fp(name, payload_len):                    # footprint = 이름 + 페이로드
        return len(name.encode("utf-8")) + payload_len

    names = iter(f"r{i:04d}" for i in range(10 ** 4))
    records, used = {}, 0
    while True:                                   # 한계 직전까지 채운다
        n = next(names)
        if used + fp(n, limit_rec) > limit_total:
            break
        records[n] = b"x" * limit_rec
        used += fp(n, limit_rec)
    assert mem.put_records(records) == []
    slack = limit_total - used                    # 남은 예산 (이름 포함)
    over_payload = max(0, slack - len("overflow") + 1)
    errs = mem.put_records({"overflow": b"x" * over_payload})
    assert len(errs) == 1                         # 경계 직후 — 1B 초과로 거부
    got, _ = mem.get_records(["overflow"])
    assert got is None
    fill_payload = slack - len("fill")
    if fill_payload >= 0:                         # 경계 정확히 — 통과해야 한다
        assert mem.put_records({"fill": b"x" * fill_payload}) == []


def test_put_is_atomic_on_partial_failure(mem):
    """한 레코드라도 거부되면 배치 전체가 저장되지 않는다 — 부분 저장 금지."""
    limit = mem.capabilities().max_record_bytes.value
    batch = {"good": b"ok", "bad": b"x" * (limit + 1)}
    errs = mem.put_records(batch)
    assert len(errs) == 1
    got, errs2 = mem.get_records(["good"])
    assert got is None and len(errs2) == 1


def test_erase_duplicate_names_is_atomic(mem):
    """리뷰 P1 회귀 고정: erase(["a","a"])가 부분 삭제 후 '거부'를 허위 보고했다.
    중복 이름은 dedup되어 성공하고, 상태는 정확히 한 번 삭제된 것과 같다."""
    assert mem.put_records({"a": b"1", "b": b"2"}) == []
    assert mem.erase(["a", "a"]) == []            # dedup — 오류도 예외도 아님
    got, errs = mem.get_records(["b"])
    assert errs == [] and got == {"b": b"2"}      # b 무사
    got, errs = mem.get_records(["a"])
    assert got is None and len(errs) == 1         # a는 정확히 삭제됨


def test_erase_failure_leaves_store_untouched(mem):
    """실패한 erase 후 저장소는 무손상 — '거부'가 참말인지 확인."""
    assert mem.put_records({"a": b"1", "b": b"2"}) == []
    errs = mem.erase(["a", "ghost"])              # ghost 없음 → 전체 거부
    assert len(errs) == 1
    got, errs = mem.get_records(["a", "b"])
    assert errs == [] and got == {"a": b"1", "b": b"2"}


def test_erase_removes_and_reports_missing(mem):
    assert mem.put_records({"a": b"1", "b": b"2"}) == []
    assert mem.erase(["a"]) == []
    got, errs = mem.get_records(["a"])
    assert got is None and len(errs) == 1
    errs = mem.erase(["ghost"])
    assert len(errs) == 1 and "ghost" in errs[0]
    # b는 무사하다
    got, errs = mem.get_records(["b"])
    assert errs == [] and got == {"b": b"2"}


# ---------- 4. 어댑터 계약 테스트 — 공통 스위트 (AC1·AC3·AC4) ----------

BAD_INPUTS = (
    None,
    "문자열",
    42,
    [("name", b"x")],
    {"": b"x"},                    # 빈 이름
    {b"bytes-name": b"x"},         # 비문자열 이름
    {"name": "비바이트"},           # 비bytes 페이로드
    {"name": None},
    {"name": 3.14},
)


@pytest.fixture(params=["memory", "garmin"])
def any_carrier(request):
    return {"memory": MemoryCarrier, "garmin": GarminConnectIQCarrier}[request.param]()


def test_no_exception_on_any_put_input(any_carrier):
    for bad in BAD_INPUTS:
        errs = any_carrier.put_records(bad)      # 예외가 나면 여기서 테스트 실패
        assert isinstance(errs, list) and len(errs) >= 1


def test_no_exception_on_any_get_input(any_carrier):
    for bad in (None, "x", 42, [None], [b"x"], [""], ["없는레코드"]):
        got, errs = any_carrier.get_records(bad)
        assert got is None
        assert isinstance(errs, list) and len(errs) >= 1


def test_no_exception_on_any_erase_input(any_carrier):
    for bad in (None, "x", 42, [None], [""], ["없는레코드"]):
        errs = any_carrier.erase(bad)
        assert isinstance(errs, list) and len(errs) >= 1


def test_no_exception_on_huge_record(any_carrier):
    errs = any_carrier.put_records({"huge": b"x" * (1024 * 1024)})
    assert isinstance(errs, list) and len(errs) >= 1


def test_adapter_satisfies_carrier_protocol(any_carrier):
    """리뷰 P9: Carrier Protocol은 살아있는 심볼 — 공통 스위트가 참조한다."""
    assert isinstance(any_carrier, Carrier)


def test_capabilities_never_raises_and_has_all_fields(any_carrier):
    caps = any_carrier.capabilities()
    assert isinstance(caps, CarrierCapabilities)
    for cv in (caps.max_record_bytes, caps.max_total_bytes, caps.transfer_mtu):
        assert isinstance(cv, CapabilityValue)
        assert isinstance(cv.value, int) and cv.value > 0
        assert isinstance(cv.source, str) and cv.source
    # 리뷰 P4: 미확인은 None, 아는 것은 bool — 그 외 타입 금지 (공통 계약)
    assert any_carrier.capabilities().supports_decompression in (True, False, None)


def test_status_determines_behavior(any_carrier):
    """리뷰 P4 핵심: '항상 실패하는 스텁'이 공통 스위트를 통과하던 구멍을 막는다.
    SUPPORTED면 왕복이 **실제로 성공**해야 하고(스텁 판별),
    UNIMPLEMENTED면 유효 입력조차 전부 실패해야 한다(AC4)."""
    records = {"meta": b'{"v":1}', "device:dev000": b'{"t":"washer"}'}
    if any_carrier.status is CarrierStatus.SUPPORTED:
        assert any_carrier.put_records(records) == []
        got, errs = any_carrier.get_records(list(records))
        assert errs == [] and got == records          # 바이트 등가
        assert any_carrier.erase(list(records)) == []
        got, errs = any_carrier.get_records(["meta"])
        assert got is None and len(errs) == 1         # 정말 지워짐
    else:
        assert any_carrier.put_records(records) != []
        got, errs = any_carrier.get_records(list(records))
        assert got is None and errs != []


def test_zero_byte_record_is_accepted_by_supported(any_carrier):
    """리뷰 P4: 0바이트 레코드 경계 고정 — 불투명 바이트 계약상 수용이다
    (0 ≤ 한계). UNIMPLEMENTED는 물론 거부."""
    errs = any_carrier.put_records({"empty": b""})
    if any_carrier.status is CarrierStatus.SUPPORTED:
        assert errs == []
        got, gerrs = any_carrier.get_records(["empty"])
        assert gerrs == [] and got == {"empty": b""}
    else:
        assert errs != []


def test_duplicate_names_no_exception(any_carrier):
    """리뷰 P4(← P1): get/erase의 중복 이름은 예외 없이 처리된다."""
    got, errs = any_carrier.get_records(["x", "x"])
    assert got is None and isinstance(errs, list) and errs != []
    errs = any_carrier.erase(["x", "x"])
    assert isinstance(errs, list) and errs != []


def test_error_messages_never_contain_payload(any_carrier):
    """오류 문구에 레코드 페이로드 값을 넣지 않는다 (1.1 리뷰 PII 누출 계승)."""
    marker = "PII-CANARY-daria@example.com"
    for errs in (
        any_carrier.put_records({"r": marker.encode() * 500}),
        any_carrier.put_records({"r": marker}),          # 비bytes 거부 경로
    ):
        for e in errs:
            assert marker not in e


def test_error_messages_never_contain_long_names(any_carrier):
    """리뷰 P2 회귀 고정: 이름 채널로도 밀수 금지 — 긴 이름은 길이만 표기된다.
    페이로드를 이름에 담는 우회(put·get·erase 전 경로)가 오류 문구로 새지 않는다."""
    marker = "PII-CANARY-daria@example.com"
    long_name = marker * 50                              # 1,400자 이름
    for errs in (
        any_carrier.put_records({long_name: b"x"}),
        any_carrier.get_records([long_name])[1],
        any_carrier.erase([long_name]),
    ):
        for e in errs:
            assert marker not in e


# ---------- 5. 미구현 정직 표기 (AC4) ----------

@pytest.fixture
def garmin():
    return GarminConnectIQCarrier()


def test_garmin_is_unimplemented(garmin):
    assert garmin.status is CarrierStatus.UNIMPLEMENTED
    assert garmin.is_device is False    # 실기기 보유와 무관 — 이 코드는 워치가 아니다


def test_carrier_status_has_exactly_two_values():
    """3값 이상 금지 — '부분 동작' 회색지대가 AC4가 막는 것이다."""
    assert {s.name for s in CarrierStatus} == {"SUPPORTED", "UNIMPLEMENTED"}


def test_unimplemented_all_operations_fail_with_notice(garmin):
    """모든 연산이 실패하고 오류 문구에 '미구현'이 포함된다 (AC4 문면)."""
    valid_put = {"meta": b'{"v":1}'}
    errs_put = garmin.put_records(valid_put)
    got, errs_get = garmin.get_records(["meta"])
    errs_erase = garmin.erase(["meta"])
    assert len(errs_put) == 1 and "미구현" in errs_put[0]
    assert got is None and len(errs_get) == 1 and "미구현" in errs_get[0]
    assert len(errs_erase) == 1 and "미구현" in errs_erase[0]


def test_unimplemented_never_returns_data(garmin):
    """get_records가 (dict, [])를 내는 경로가 존재하지 않는다 —
    put이 '성공한 척'한 뒤 get이 데이터를 돌려주면 시연 사기가 된다."""
    garmin.put_records({"meta": b'{"v":1}'})     # 실패했어야 함
    for names in (["meta"], [], list("abc")):
        got, errs = garmin.get_records(names)
        assert got is None
        assert errs != []


# ---------- 6. 공개 표면 ----------

def test_package_exports_carrier_symbols():
    for sym in ("Carrier", "CarrierStatus", "CarrierCapabilities",
                "CapabilityValue", "MemoryCarrier"):
        assert sym in home_profile.__all__
        assert hasattr(home_profile, sym)
