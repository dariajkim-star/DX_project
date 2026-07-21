# 설문 배포 정보 — 스마트홈(ThinQ) 사용 경험 3분 설문

생성 2026-07-21 · SURVEY_PLAN v2 기반 · 생성 스크립트 [survey_form.gs](survey_form.gs)

## 폼 URL

- **편집**: https://docs.google.com/forms/d/1x-JqmEHcyfekFUC2FHKnAKbk_QrnFi5WhlgdFQPNWUU/edit
- **응답(기본)**: https://docs.google.com/forms/d/e/1FAIpQLSee6ZHTE027ky3IchtyPrB4z6zyKU67Ne7ew4HoOvsRKTETOA/viewform
- Apps Script 프로젝트: https://script.google.com/home/projects/1Ktt-uX6qTgIZp_txorN0LOU_dhNLYnUd5HnTyYPp9jHs5Ts5zpThgMQt/edit

## 채널별 배포 링크 (문15 유입 채널 사전 채움)

`entry.1072160501` = 문15. 아래 링크로 배포하면 유입 채널이 자동 선택되어 사후 편향 점검이 가능.

| 채널 | 군 | 링크 |
|---|---|---|
| 동탄 맘카페 | G1 | `…/viewform?usp=pp_url&entry.1072160501=맘카페` |
| 당근 동네생활 | G1 | `…/viewform?usp=pp_url&entry.1072160501=당근+동네생활` |
| 레몬테라스 | G1/G2 | `…/viewform?usp=pp_url&entry.1072160501=레몬테라스` |
| 오늘의집 | G2 | `…/viewform?usp=pp_url&entry.1072160501=오늘의집` |
| 신혼 친구(파일럿 3명) | G2 | `…/viewform?usp=pp_url&entry.1072160501=지인+소개` |
| 블라인드 | G3 | `…/viewform?usp=pp_url&entry.1072160501=블라인드` |
| 스마트싱스 카페 | G3 | `…/viewform?usp=pp_url&entry.1072160501=스마트싱스+카페` |
| 클리앙·뽐뿌 | G3 | `…/viewform?usp=pp_url&entry.1072160501=클리앙·뽐뿌` |
| LGDX 동기 | G3 전용 | `…/viewform?usp=pp_url&entry.1072160501=LGDX` |

`…` = 응답(기본) URL. 한글 값은 브라우저가 자동 인코딩하므로 그대로 붙여넣어도 동작.
정확한 인코딩 링크가 필요하면 Apps Script에서 `fixAndPrefill` 재실행 후 로그 복사.

## 검수 결과 (verifyForm 로그, 2026-07-21 18:38 — v3 적용 후)

- 제목/진행률바 true / 이메일수집 false / 1인1응답 false → **익명·로그인 불필요 확인**
- 섹션 구조: 1(문1 스크리닝) → 2 기본정보(문2~7) → 3 불편경험(문8~10) → 4 워치·지불성향(문11~16) → 5 종료(SUBMIT)
- **분기 정상**: 문1 `0대→[섹션5] 설문 대상이 아니에요`, `1대/2~3대/4대 이상→[섹션2] 기본 정보`
  (파일럿 4건 중 2건이 실제로 0대 종료 — 실증됨)
- **순서 원칙 준수**: Pain 회상(섹션3)이 지불성향(문13, 섹션4)보다 앞
- v3 반영 확인: 문2 '사용해본 적 없음', 문4 '부모님댁에 거주', 문8·9·10·12 척도 라벨 전체 표기,
  문11-1 체크박스, 문11-2 "확인하거나 조절", 문11-3 신설, 문13 성향 3단, 문13-2 신설
- 문항 순서 `17: 13 → 18: 13-1 → 19: 13-2` (fixOrder로 교정 — applyV2 초기 실행 시 13-2가
  13-1보다 앞에 삽입되어 바로잡음)

## 적용 이력

| 일시 | 함수 | 내용 |
|---|---|---|
| 07-21 17:34 | `createSurveyForm` | 폼 최초 생성 (v2 문항) |
| 07-21 17:39 | `fixAndPrefill` | 제목 보정 + 채널 사전 채움 링크 생성 |
| 07-21 18:36 | `dumpResponses` | 파일럿 4건 백업 → [survey_responses_v2_backup.md](survey_responses_v2_backup.md) |
| 07-21 18:38 | `applyV2` | v3 문항 적용 (문11-1 재생성으로 해당 문항 응답 소실) |
| 07-21 18:39 | `fixOrder` | 13-2를 13-1 뒤로 이동 |

## 남은 일

- [ ] **파일럿 응답 4건 삭제** (v2 문항 기준이라 v3 데이터와 혼재 불가 — 백업 완료)
- [ ] 파일럿 재수집 (신혼 친구 3명) → 문구·소요시간 점검
- [ ] 동탄 맘카페 매니저 사전 허락 문의 (Vex 3원칙: LG 공식 아님·익명·수집항목 고지 — 폼 설명에 반영 완료)
- [ ] 본배포 → 응답 시트 → `data/survey.csv` → `04_segmentation.py`
- [ ] `04_segmentation.py`의 `지불의사` 인코딩을 `0/1/2`로 갱신 (v3 변경 반영)
