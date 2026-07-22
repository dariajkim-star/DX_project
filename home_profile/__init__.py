# -*- coding: utf-8 -*-
"""home_profile — 온바디 홈 프로필 제품 코드 (Epic 1).

분석 파이프라인(`dx_pipeline_v2.2/`)과 계보가 다르다.
파이프라인은 VOC에서 Pain을 도출하는 '발견' 트랙이고,
이 패키지는 그 결과로 설계된 '처방' 트랙이다. 서로 import하지 않는다.
"""
from .schema import (  # noqa: F401
    MIGRATIONS,
    SCHEMA_VERSION,
    TOP_LEVEL_KEYS,
    assert_no_identifiers,
    is_supported,
    new_profile,
    validate_profile,
)
