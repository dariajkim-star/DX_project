# -*- coding: utf-8 -*-
"""벤더 어댑터 — 경계가 디렉터리로 보이는 곳 (Story 1.3).

이 디렉터리 안에서만 벤더 의존이 허용된다(경계의 정의).
tests/test_carrier_neutrality.py의 AST 검사에서 이 디렉터리는 면제 대상이다.

현황 (docs/CARRIER_INTERFACE.md 캐리어 현황표가 원본):
  garmin  — 미구현 (경계 설계·용량 신고만. Monkey C 런타임 필요, 이 저장소엔 없음)
  apple   — 미구현 (파일 자체를 만들지 않았다 — 빈 스텁 금지, Task 4)
  xiaomi  — 미구현 (동상)
"""
