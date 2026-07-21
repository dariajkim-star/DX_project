# DX_project — CX 분석 파이프라인 + MoA 오케스트레이터

리뷰·설문 데이터로 **타겟 세그먼트**와 **Pain Point**를 정량 도출하고(DX 파이프라인),
그 산출물을 근거로 GPT 서브 에이전트(A~F)와 Claude Code(G)가 CX 보고서를 만드는(MoA)
프로젝트입니다.

> **상태**: 템플릿 하드닝 완료(v2.8, GPT 7차 교차검증). 실제 프로젝트(팀·주제·앱)는
> 아직 미확정 — `SERVICE`, `APP_ID`, `FEATURE_COLUMNS`가 채워지면 실행 단계로 넘어갑니다.

## 폴더 구조

```
DX_project/
├─ README.md                  ← 이 문서
├─ CLAUDE.md                  ← Master Agent(G) 규칙 (v2.7)
├─ moa_orchestrator.py        ← GPT A~F 호출 + 계보 게이트 (v2.8)
├─ docs/
│  ├─ API_SPEC.md             ← 스크립트·파일 계약 명세
│  └─ DEV_PLAN.md             ← 개발계획서 (이력 + 로드맵)
├─ dx_pipeline/               ← 원본 템플릿 (v2.1, 참고용 보존)
└─ dx_pipeline_v2.2/          ← 현행 파이프라인 (v2.8)
   ├─ 01_collect.py ~ 06_visualize.py
   ├─ lineage.py              ← 계보 해시 공통 유틸
   ├─ requirements.txt
   ├─ data/                   ← 생성물 (git 미추적)
   └─ out/                    ← 차트 산출물 (git 미추적)
```

## 빠른 시작 (데모)

```bash
cd dx_pipeline_v2.2
pip install pandas numpy scikit-learn scipy matplotlib   # 최소 설치
python 01_collect.py --demo    # 합성 45건 (실데이터 아님이 계보에 기록됨)
python 02_preprocess.py
python 03_embedding.py
python 04_segmentation.py --demo
python 05_painpoint.py
python 06_visualize.py --demo
```

실데이터 실행·MoA 연동·산출물 목록은 [dx_pipeline_v2.2/README.md](dx_pipeline_v2.2/README.md) 참고.

## 핵심 설계 원칙

1. **데이터 계보(lineage)**: 합성 데모와 실수집을 파일·메타에서 분리하고,
   metadata → preprocess_meta → painpoints_meta를 run_id + 파일 SHA-256으로 연결.
   orchestrator는 이 체인을 통과한 산출물만 "실데이터"로 GPT에 주입.
2. **폴백은 기록과 함께**: 라이브러리 부재 시 가벼운 기법으로 자동 폴백하되,
   어떤 방식이 쓰였는지 산출물 메타에 남긴다 (`sentiment_method` 등).
3. **모르는 것은 수치화하지 않는다**: 실데이터 없으면 신뢰도는 '산출 불가',
   검색 없는 A·C·D의 수치는 전부 '(미검증 — 조사 필요)'.

## 알려진 잔여 리스크 (수용됨)

- **Prompt injection**: system/user 메시지 분리 + JSON 직렬화는 완화책이며
  결정적 방어가 아님. 최종 보고서의 인용문·신뢰도는 사람이 원본 대조 검수.
- **A·C·D 무검색**: 시장·경쟁사 수치는 리서치 질문·가설 용도로만 사용.

상세: [dx_pipeline_v2.2/README.md](dx_pipeline_v2.2/README.md) 상단, [CLAUDE.md](CLAUDE.md).

## 검증 이력

v2.2→v2.8까지 GPT 7차 교차검증(Claude 수정 ↔ GPT 재검증 루프)을 거침.
라운드별 변경 내역은 [dx_pipeline_v2.2/README.md](dx_pipeline_v2.2/README.md)의
버전 로그, 전체 계획과 남은 일은 [docs/DEV_PLAN.md](docs/DEV_PLAN.md) 참고.
