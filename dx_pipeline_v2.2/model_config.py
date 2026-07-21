# -*- coding: utf-8 -*-
"""모델 설정 단일 소스 (v2.8)
03(임베딩)·05(감성/토픽)와 orchestrator 게이트가 같은 값을 참조한다.
모델을 교체할 때는 이 파일만 수정하면 됨.

[주의] SENTIMENT_MODEL 교체 시 LABEL_MAP 방향이 반대일 수 있음 —
05 실행 시 출력되는 검증용 샘플 3건으로 반드시 확인할 것.
"""

SBERT_MODEL = "jhgan/ko-sroberta-multitask"

SENTIMENT_MODEL = "matthewburke/korean_sentiment"
# 허용 라벨 화이트리스트 — 여기 없는 라벨이 나오면 05가 평점 폴백으로 강등
LABEL_MAP = {"LABEL_0": "neg", "LABEL_1": "pos"}
