# 이월 작업 (Deferred Work)

code-review에서 실재하나 지금 조치하지 않기로 한 항목. 후속 스토리·리팩터에서 재검토.

## Deferred from: code review of 3-1-reinstall-restore (2026-07-23)

- **`merge_chunks` 반환이 입력 조각을 참조로 물고 나온다(aliasing)** —
  `home_profile/storage.py` `merge_chunks`. 반환 프로필의 중첩 객체(routines·
  settings)가 입력 `chunks`(및 `split_chunks` 경로에선 원본 프로필)와 참조를
  공유한다. 캐리어 복원(주 경로)은 JSON 재역직렬화로 신선한 객체를 만들어
  무해하고, `split_chunks` 자체도 이미 동일한 얕은 복사 특성을 가진다.
  직접 `merge_chunks(split_chunks(x))` 반환값을 "독립 소유물"로 다루며 중첩을
  변형하는 호출자만 영향. 수정 시 반환 직전 deepcopy(비용 발생)로 격리 가능.
  값 동등(`==`) 테스트로는 드러나지 않음. blind 리뷰 Med.
