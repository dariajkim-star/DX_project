# -*- coding: utf-8 -*-
"""오프라인 강제 하네스 — 시험 장비 (Story 2.3, Task 2).

⚠️ **이것은 제품 코드가 아니라 시험 장비다.** 저장소 루트에 두는 이유이며,
이 프로젝트의 "예외 금지" 계약이 여기에는 적용되지 않는다 —
오히려 **예외를 던지는 것이 이 하네스의 임무**다.

2.2가 만든 것과의 차이:
  - 2.2 `test_no_network_calls_during_execution`: monkeypatch로 **감시**했다.
    통과했지만 그건 "이번 실행에서 안 불렀다"이다("부르지 않았다").
  - 2.3 이 하네스: **막는다.** 막힌 상태에서 통과해야 심사위원의 의심에
    답이 된다("부를 수 없다").

차단 시 `OfflineViolation`을 던진다. **`BaseException` 파생**이다 —
제품 코드의 `except Exception`이 위반을 흡수하면(fail-closed가 여기서는 함정),
이 스토리 전체가 무의미해진다. `BaseException`은 일반 `except Exception`에
잡히지 않으므로 위반이 반드시 밖으로 나온다(pytest.raises·finally는 정상 동작).
"""
import socket
import subprocess
import urllib.request

__all__ = ["OfflineViolation", "enforce_offline", "is_active",
           "blocking_installed"]


class OfflineViolation(BaseException):
    """오프라인 강제 중 네트워크 접근 시도. BaseException 파생 — 제품 코드의
    `except Exception`에 흡수되지 않게 하기 위함(모듈 docstring 참조)."""


# 차단 대상과 원본. 2.2 감시 목록을 승계하고, 2.2 리뷰(Paige)가 구멍으로
# 지적한 getaddrinfo(DNS)·socketpair를 추가한다.
_TARGETS = (
    (socket, "socket"),
    (socket, "create_connection"),
    (socket, "getaddrinfo"),          # DNS — Paige 지적
    (socket, "socketpair"),           # Paige 지적
    (urllib.request, "urlopen"),
    (subprocess, "Popen"),
    (subprocess, "run"),
)

_depth = 0            # 중첩 카운트
_saved = []          # [(module, name, original), ...]


def is_active() -> bool:
    """현재 오프라인 강제가 활성인지 — **카운터 기준**."""
    return _depth > 0


def blocking_installed() -> bool:
    """차단이 **실제로 설치돼 있는지** — 카운터가 아니라 함수 실체를 확인한다.

    리뷰(2026-07-22, Mary): `is_active()`는 `_depth > 0`만 본다. 종단 테스트가
    "하네스 활성"을 그것으로 확인했는데, 카운터가 1이어도 blocker가 무력화돼
    있으면 여전히 True를 낸다 — "카운터 언급"이지 "차단 확인"이 아니다
    (1.1 '단어 언급 단언 금지'의 사촌). 이 함수는 대상 함수가 우리 blocker로
    바뀌어 있는지를 정체(identity)로 검사한다."""
    if _depth == 0:
        return False
    return all(getattr(m, n).__name__ == "_blocker" for m, n in _TARGETS)


def _make_blocker(label: str):
    def _blocker(*args, **kwargs):
        raise OfflineViolation(
            f"오프라인 강제 중 네트워크 접근 시도: {label}")
    return _blocker


class _EnforceOffline:
    """컨텍스트 매니저. 재진입 안전(중첩 시 가장 바깥이 실제 복구를 담당)."""

    def __enter__(self):
        global _depth
        if _depth == 0:
            # 원자적으로 설치한다 (리뷰 2026-07-22, Winston):
            # v1은 setattr 루프 중간에 예외가 나면 일부만 막힌 채 _depth가 0으로
            # 남아 __exit__이 영영 불리지 않았다 — 시험 장비가 자기 실패에서
            # 빠져나오지 못하고 프로세스를 오염시켰다. put_records를 원자화한
            # 것과 같은 원리(오늘 P1): 먼저 전부 읽어 스테이징하고, 그 다음
            # 한꺼번에 적용하되 적용 중 실패하면 이미 바꾼 것을 되돌린다.
            staged = [(m, n, getattr(m, n)) for m, n in _TARGETS]
            applied = []
            try:
                for module, name, _original in staged:
                    setattr(module, name,
                            _make_blocker(f"{module.__name__}.{name}"))
                    applied.append((module, name))
            except BaseException:
                for module, name, original in staged:
                    if (module, name) in applied:
                        setattr(module, name, original)
                raise
            _saved.clear()
            _saved.extend(staged)
        _depth += 1
        return self

    def __exit__(self, exc_type, exc, tb):
        global _depth
        _depth -= 1
        if _depth == 0:
            for module, name, original in _saved:
                setattr(module, name, original)
            _saved.clear()
        return False      # 예외를 삼키지 않는다 — OfflineViolation은 전파된다


def enforce_offline():
    """`with enforce_offline():` 블록 안에서 네트워크 접근을 차단한다.

    블록을 정상 종료하든 예외로 빠져나가든 원본 함수가 복구된다 —
    뒤따르는 코드/테스트를 오염시키지 않는다."""
    return _EnforceOffline()
