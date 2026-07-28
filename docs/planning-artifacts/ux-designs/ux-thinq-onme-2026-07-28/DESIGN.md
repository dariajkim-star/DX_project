---
status: final
updated: 2026-07-28
project: ThinQ OnMe — 데모 프레젠테이션 층
sources:
  - ../../../DEMO_SCRIPT.md
  - ../../../PERSONA_NIGHT_KEEPER.md
  - ../../../PROFILE_SCHEMA.md
colors:
  terminal:
    background: "#0D1117"        # 발표장 프로젝터 대비 최우선 — 순검정 대신 저채도 남흑
    foreground: "#E6EDF3"        # 본문 텍스트
    dim: "#8B949E"               # 보조·캡션 (정직 표기 라벨, device_ref)
    accent: "#58A6FF"            # 장면 제목·Job 문장
    success: "#3FB950"           # 상태 전이 성공 (✓)
    blocked: "#F85149"           # 차단·거부·복원 실패 (✗) — '실패=나쁨' 아님, 증거색
    held: "#D29922"              # 보류(이사 매핑) — 버린 게 아니라 사유와 함께 남긴 것
  sketch:
    watch_bg: "#000000"          # 손목 1장 전용 — AMOLED 워치 관례
    watch_fg: "#FFFFFF"
    watch_dim: "#6E7681"         # device_ref 표기
typography:
  terminal:
    family: "D2Coding, Cascadia Code, monospace"   # 한글 고정폭 필수 — 표 정렬 깨짐 방지
    scene_title: "굵게 + accent"
    body: "regular"
    caption: "dim"
    min_projector_size: "터미널 폰트 18pt 이상 — 발표장 뒷줄 가독 기준(검증 필요: 리허설 실측)"
  sketch:
    alias: "크게 (화면 폭 대비 주 시선)"
    device_ref: "작게 + watch_dim"
rounded: {}
spacing:
  scene_gap: "장면 사이 빈 줄 2 — 프로젝터에서 장면 경계가 스크롤 없이 읽히게"
  label_indent: "정직 표기 라벨은 본문보다 2칸 들여쓰기"
components:
  scene_header: "장면 번호·제목·겨냥 Pain 한 줄 (accent)"
  transition_row: "기기 전환 1줄 = [기기] [전이 내용] [✓/✗/보류] — 코드값이 아니라 읽히는 문장"
  honesty_footer: "장면 말미 고정 슬롯 — 시뮬레이터·미측정·범위 한계 (dim)"
  evidence_block: "검증 증거 블록 — 주장 대신 실측 결과 (폐기 장면의 주인공)"
  boundary_table: "막는 것 🛡️ / 못 막는 것 ⚠️ 병렬 표 (릴레이 장면)"
---

# ThinQ OnMe — DESIGN.md (데모 프레젠테이션 층)

> **AI 초안 — 최종 책임은 팀.** 본 문서는 시각 계약이다. 충돌 시 본 문서와
> EXPERIENCE.md가 모든 목업·스케치에 우선한다.

## Brand & Style

- 무대는 **터미널**이다. 이를 숨기지 않는다 — 프로토타입의 정직성이 곧 브랜드.
  "예쁜 앱인 척"이 아니라 **"읽히는 증거"**가 스타일 목표.
- 어휘는 LG 언어의 결을 따른다(정도경영·고객감동·Effortless). 공격적 비교 금지.
- 정직 표기(시뮬레이터·미측정·미검증·잔여 한계)는 디자인 요소다 — 구석에 숨기지
  않고 `honesty_footer` 고정 슬롯에 매 장면 배치한다.

## Colors

- 색은 5개 의미역만: 본문 / 보조 / 성공 / 차단·실패 / 보류. 장식색 금지.
- `blocked`(적색)는 "나쁨"이 아니라 **증거**다 — 소켓 열기 실패, 재생 거부,
  폐기 후 복원 실패는 전부 적색 ✗로 표기되며, 그것이 주장의 증명이다.
- `held`(황색)는 이사 매핑 전용 — "조용히 버리지 않았다"의 색.

## Typography

- 한글 고정폭(D2Coding 계열) 강제 — 이전/보류 요약표·소재 표의 열 정렬이
  프로젝터에서 깨지면 신뢰 표면이 같이 깨진다.
- 프로젝터 최소 크기는 **(검증 필요)** — 리허설에서 뒷줄 가독으로 실측 후 확정.

## Layout & Spacing

- 한 장면 = 한 화면. 스크롤 중 발화 금지 — 장면 전환은 명령 실행과 일치.
- 정직 표기는 들여쓰기 2칸 + dim — 본문과 시각적으로 구분되되 같은 화면 안에.

## Components

- `transition_row` — `fan_speed: low` 같은 코드값을 그대로 두지 않는다.
  **"에어컨 바람 약하게 ✓ (소음↓ — 아이를 깨우지 않게)"** 처럼 Job 대응까지 한 줄.
  코드값은 괄호 보조 표기로 유지(코드가 진실 원천이라는 표시).
- `evidence_block` — 폐기 장면 전용 규칙: **"완료" 배지 금지.**
  두 검증 축(①복원 시도 → 실패 ②잔류 스캔 → 0건)의 실측 결과를 전면에.
  (4.4 리뷰 교훈: 성공 보고를 믿지 않고 검증한다 — 화면도 같은 원칙)
- `boundary_table` — 릴레이 장면 전용: 막는 것/못 막는 것 병렬. 못 막는 것을
  작게 쓰지 않는다 — 같은 크기, 같은 무게.

## 손목 1장 (제품 UI 스케치 — 설계안, 미구현)

- **그림 안**: 별칭 크게("안방 에어컨") + `d1` 작게 + 캡션 "프로필이 아는 전부".
  무별칭 폴백 = device_type 한글화("에어컨").
- **그림 밖 캡션 줄**: "설계안 — 미구현" · "인구통계는 설문 검증 대기".
  라벨을 그림 안에 넣어 경고문 포스터를 만들지 않는다.
- 장면은 야간모드 1개만. 다른 화면 창작 금지.

## Do's and Don'ts

- ✅ 실패·거부·차단을 적색 증거로 크게 보여라 — 그게 증명이다
- ✅ 못 막는 것을 막는 것과 같은 무게로
- ❌ "완료" 배지 (폐기 장면 — evidence_block으로 대체)
- ❌ 장식색·애니메이션·이모지 남용 — 증거 화면이지 프로모션이 아니다
- ❌ 미구현 화면 추가 창작 (손목 1장 외 금지 — 방어 표면적 증가)
