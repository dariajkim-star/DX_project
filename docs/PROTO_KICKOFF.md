# ThinQ OnMe — 프로토 개발 킥오프 (새 창 인계용)

작성 2026-07-22 · 이 문서는 **새 세션이 콜드 스타트로 프로토 개발을 시작**하기 위한 인계 노트다.

---

## 지금 무엇을 만드는가

**ThinQ OnMe** — "집이 나를 따라온다(Home Follows You)"의 프로토타입.
온바디 홈 프로필(가전 등록·설정·루틴)을 워치에 담아, 서버가 죽어도·이사를 가도·
앱을 지워도 집 설정이 손목에 남게 한다.

**데모 목표(범위 한정)**: 가민 실기기 1 + 애플워치 1 = **워치 2대에 같은 프로필**을
띄우는 **캐리어 중립 데모**. 가전은 시뮬레이터. "서버 없이 야간 모드 전환"(Night Keeper Job).

## 이미 완성된 것 (Python, `home_profile/`)

Epic 1의 Story 1.1·1.2가 구현·리뷰 완료됐다. **이건 데이터 계층이지 워치 앱이 아니다.**

| 파일 | 내용 |
|---|---|
| [home_profile/schema.py](../home_profile/schema.py) | 홈 프로필 스키마 v1.0.0 + 검증(`validate_profile`) |
| [home_profile/storage.py](../home_profile/storage.py) | 직렬화·역직렬화·크기 리포트·`split_chunks` |
| [docs/PROFILE_SCHEMA.md](PROFILE_SCHEMA.md) | 스키마 명세 + 크기 예산 결정 이력(§5.1~5.5) |
| [tests/](../tests/) | 회귀 129 passed |

**계약 요약** (전부 예외 금지 fail-closed, 위반은 목록 반환):
- `validate_profile(p) -> list[str]` (빈 리스트 = 통과)
- `serialize(p) -> (bytes|None, errors)` / `deserialize(bytes) -> (profile|None, errors)`
- `split_chunks(p) -> {"meta":..., "device:<ref>":..., "routine:<i>":...}` (저장 키 경계)
- 값은 스칼라만(str≤64/int≤20자리/bool/유한 float), 식별자·PII·웰니스 데이터는 거부

## 확정된 설계 결정 (파티, 2026-07-22)

1. **포맷**: JSON 유지. **워치 측 JSON 파서를 직접 작성한다** — Monkey C엔 런타임 JSON
   파서가 없다(makeWebRequest는 HTTP 계층 전용). 우리 JSON은 좁은 부분집합이라 구현 가능.
2. **예산**: 보수 4,096B/키 단일 기준(마진 없음 — 4KB가 곧 마진). 실기기 실측 시 교체.
3. **개수 상한**: 스키마 상한 = 보안 천장(기기30·루틴20 등). 낮추지 않는다.
4. **저장 전략**: **기기 단위 분할** — `Application.Storage`에 meta/기기별/루틴별 키로 저장.
   최악 케이스에서도 조각당 4,096B 내(실측 확인).

## 새 창에서 할 일 (프로토 = 워치 앱)

⚠️ **이건 Python이 아니라 Monkey C(Connect IQ) 작업이다.** 별도 트랙.

- **Story 1.3(캐리어 중립 추상화)** 컨텍스트가 이미 준비돼 있다:
  [docs/implementation-artifacts/1-3-carrier-neutral-abstraction.md](implementation-artifacts/1-3-carrier-neutral-abstraction.md)
- **Epic 2(서버 없는 BLE 데모)**가 발표 클라이맥스의 마지막 증거.
- 착수 전 확인: `bmad-dev-story 1.3` 또는 Epic 2 스토리 생성.

### Connect IQ 실증 사실 (조사 완료, [PROFILE_SCHEMA §5.3](PROFILE_SCHEMA.md))
- `Application.Storage`: 값당 공식 32KB(단 기기별 상이), ByteArray·Dictionary 저장 가능.
  `setValue` System Error 버그(361건) 있으니 `try/catch` 필수.
- 압축(zlib) API 없음 — 압축 전략 폐기됨.
- 런타임 JSON 파서 없음 — 직접 작성.
- 임의 파일 쓰기 불가(파일시스템 API 없음).

### 실기기 실측 항목 (가민 보유 — Epic 4 백로그였으나 프로토에 필요)
- [ ] `System.getSystemStats()` freeMemory/totalMemory (기기 모델 병기)
- [ ] `Application.Storage.setValue("t", "x"*N)` N 증가 → 키당 실제 상한
- [ ] Storage **키 개수** 상한 (최악 51개 키 — CIQ 16슬롯은 앱 슬롯이지 Storage 키 아님, 확인 필요)

## 크리티컬 패스 (병렬 트랙, 코드 아님)

**설문 배포**가 여전히 크리티컬 패스다. 다리아 일정: 실행 순서 엄수 —
`dumpResponses()` → v2 응답 4건 수동 삭제 → `applyV3()` → `verifyForm()` → 파일럿 3명
(G1 유자녀 1 + G2 신혼 2) → 채널 배포. 설문 문6(보유 가전 수)이 개수 상한을 실측으로 교체한다.

## 저장소 · ⚠️ bmad config 주의
`dariajkim-star/DX_project` (최신 `e29fc5d`).

⚠️ **bmad config(`_bmad/bmm/config.yaml`)는 Desktop 전역이라 경로 한 벌뿐이고,
다른 창(crm-targeting-lab)과 서로 덮어쓴다.** 새 창에서 bmad 스킬
(`create-story`·`dev-story` 등)을 쓰기 **전에 반드시** 아래 3줄이 DX_project를
가리키는지 눈으로 확인하고, 아니면 고칠 것:
```yaml
planning_artifacts:       "{project-root}/DX_project/docs/planning-artifacts"
implementation_artifacts: "{project-root}/DX_project/docs/implementation-artifacts"
project_knowledge:        "{project-root}/DX_project/docs"
```
(이 노트 작성 직후 다른 창이 crm으로 되돌려 놓은 상태 — 새 창에서 다시 세팅 필요.)
