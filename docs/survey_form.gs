/**
 * SURVEY_PLAN v2 → Google Form 생성 스크립트
 * 실행: script.google.com 새 프로젝트에 붙여넣고 createSurveyForm 실행
 * 실행 후 로그(보기>로그 또는 Ctrl+Enter)에 편집 URL / 응답 URL 출력
 *
 * 구조: 섹션1(안내+문1 스크리닝) →[분기]→ 섹션2(문2~7) → 섹션3(문8~10 Pain)
 *       → 섹션4(문11~15) → 제출 / 0대는 종료 섹션 → 제출
 */
function createSurveyForm() {
  const form = FormApp.create('스마트홈(ThinQ) 사용 경험 3분 설문');

  form.setDescription(
    '안녕하세요! LG 스마트가전(ThinQ) 사용 경험에 대한 짧은 설문입니다.\n\n' +
    '⏱ 약 3분 소요 (13문항)\n' +
    '🎁 응답자 중 추첨 5명께 기프티콘을 드립니다 (연락처는 추첨 희망자만 마지막에 선택 입력)\n\n' +
    '· 본 설문은 LG전자 공식 설문이 아니며, 개인 리서치 프로젝트입니다.\n' +
    '· 익명으로 진행되며, 응답은 통계 분석 목적으로만 사용 후 폐기됩니다.\n' +
    '· 수집 항목: 가전 사용 경험·가구 형태 등 아래 문항 응답 (개인 식별 정보 수집 없음)'
  );
  form.setProgressBar(true);           // 진행률 표시
  form.setCollectEmail(false);         // 익명
  form.setLimitOneResponsePerUser(false); // 구글 로그인 강요 안 함

  const L5_EXP = ['1 전혀 없다', '2 없다', '3 보통', '4 자주 있다', '5 매우 자주 있다'];

  // ── 섹션 1: 스크리닝 (문1 단독 — 분기가 섹션 끝에서 작동하므로 반드시 단독 섹션)
  const q1 = form.addMultipleChoiceItem()
    .setTitle('1. 보유하신 LG 스마트가전은 몇 대인가요?')
    .setHelpText('스마트가전 = ThinQ 앱에 연결 가능한 가전 (세탁기·건조기·에어컨·냉장고 등)')
    .setRequired(true);

  // ── 섹션 2: 기본 정보 (문2~7)
  const secBasic = form.addPageBreakItem().setTitle('기본 정보');

  form.addMultipleChoiceItem().setTitle('2. ThinQ 앱을 얼마나 자주 사용하시나요?')
    .setChoiceValues(['사용해본 적 없음', '설치만 해둠', '월 1회 이하', '주 1~2회', '거의 매일']).setRequired(true);

  form.addMultipleChoiceItem().setTitle('3. 연령대를 알려주세요')
    .setChoiceValues(['20대 이하', '30대', '40대', '50대', '60대 이상']).setRequired(true);

  form.addMultipleChoiceItem().setTitle('4. 가구 형태를 알려주세요')
    .setChoiceValues(['1인 가구', '부부 (자녀 없음)', '자녀 있음 (미취학)', '자녀 있음 (취학 이상)', '부모님댁에 거주', '기타']).setRequired(true);

  // H2 소스 — 자가/전월세 이진을 오염시키지 않도록 '가족과 함께 거주'는 기타로 흡수
  form.addMultipleChoiceItem().setTitle('5. 현재 주거 점유 형태는 무엇인가요?')
    .setHelpText('가족 소유 집에 함께 사는 경우 등은 "기타"를 선택해주세요')
    .setChoiceValues(['자가', '전세', '월세', '기타']).setRequired(true);

  form.addMultipleChoiceItem().setTitle('6. 2년 내 이사 계획이 있으신가요?')
    .setChoiceValues(['있다', '없다', '아직 모르겠다']).setRequired(true);

  form.addMultipleChoiceItem().setTitle('7. LG 가전을 주로 어떤 계기로 구매하셨나요?')
    .setChoiceValues(['혼수 준비', '이사·입주', '고장으로 교체', '프로모션·구독 서비스', '기타']).setRequired(true);

  // ── 섹션 3: 불편 경험 (문8~10) — Pain 회상이 지불의사(문13)보다 반드시 먼저
  form.addPageBreakItem().setTitle('사용 중 불편 경험')
    .setHelpText('최근 1년 내 경험을 떠올리며 답해주세요.');

  form.addMultipleChoiceItem().setTitle('8. 앱이나 서버 문제로 가전 제어에 실패한 경험이 있나요?')
    .setHelpText('예: 앱 오류·서버 점검·응답 없음으로 에어컨/세탁기 제어 불가')
    .setChoiceValues(L5_EXP).setRequired(true);

  form.addMultipleChoiceItem().setTitle('9. 앱 재설치나 공유기 교체 후, 가전을 다시 등록/설정한 경험이 있나요?')
    .setChoiceValues(L5_EXP).setRequired(true);

  form.addMultipleChoiceItem().setTitle('10. 가전 앱의 회원가입·약관 동의·개인정보 요구가 부담스러웠던 적이 있나요?')
    .setChoiceValues(['1 전혀 부담 없다', '2 부담 없다', '3 보통', '4 부담된다', '5 매우 부담된다']).setRequired(true);

  // ── 섹션 4: 워치·수용도·지불의사 (문11~15)
  form.addPageBreakItem().setTitle('스마트워치와 새로운 방식');

  // 복수 보유 가능 → 체크박스
  form.addCheckboxItem().setTitle('11-1. 스마트워치를 보유하고 계신가요? (여러 개면 모두 선택)')
    .setChoiceValues(['없음', '애플워치', '갤럭시워치', '가민', '기타']).setRequired(true);

  // 척도 유지(FEATURE_COLUMNS 야간사용) + 질문을 Night Keeper Job("확인")으로 교체
  form.addMultipleChoiceItem().setTitle('11-2. 밤 10시 이후, 잠든 뒤나 자다 깨서 집 상태를 확인하거나 조절한 적이 얼마나 있나요?')
    .setHelpText('예: 아이 방 온도 확인, 조명·에어컨 조절')
    .setChoiceValues(L5_EXP).setRequired(true);

  // 상황 복수 선택 — 기능 우선순위 인사이트용 (군집 변수 아님)
  form.addCheckboxItem().setTitle('11-3. 앱으로 가전을 제어할 수 있다면 편할 것 같은 상황을 모두 골라주세요')
    .setChoiceValues([
      '아이 재우고 나서 불·가전 끄기',
      '자다 깨서 아이 방 온도·공기 확인',
      '잠들기 전 침대에서 조명·에어컨 조절',
      '밤중에 소음 걱정 없이 세탁기·건조기 예약',
      '새벽에 일어나 집 상태 한 번 훑기',
      '낮에 외출 중 집 상태 확인',
    ]).showOtherOption(true).setRequired(true);

  form.addMultipleChoiceItem().setTitle('12. "앱을 열지 않아도, 손목의 워치에 담긴 내 설정으로 집이 알아서 반응한다"면 사용하시겠어요?')
    .setChoiceValues(['1 전혀 아니다', '2 아니다', '3 보통', '4 희망한다', '5 꼭 쓰고 싶다']).setRequired(true);

  // 금액 사다리 대신 성향 — 응답자가 상상 없이 답할 수 있는 값. 금액 what-if는 합성 패널 담당(SURVEY_PLAN §4)
  form.addMultipleChoiceItem().setTitle('13. 이런 기능이 나온다면, 어떤 쪽에 가까우세요?')
    .setChoiceValues([
      '무료가 아니면 쓰지 않겠다',
      '무료로 써보고 괜찮으면 유료도 고려하겠다',
      '유료라도 쓸 의향이 있다',
    ]).setRequired(true);

  form.addMultipleChoiceItem().setTitle('13-2. 돈을 낸다면 어떤 방식이 가장 자연스러울까요?')
    .setChoiceValues([
      '월 구독료',
      '가전 살 때 가격에 포함',
      '한 번 결제하고 계속 사용',
      '무료 대신 광고·데이터 제공',
      '잘 모르겠다',
    ]).setRequired(true);

  form.addMultipleChoiceItem().setTitle('13-1. (12번에서 "3 보통" 이상 선택하신 분만) 이 기능에서 가장 걱정되는 점은?')
    .setChoiceValues(['워치를 항상 차고 있어야 함', '분실 시 보안', '설정이 복잡할 것 같음', '워치 배터리', '내 생활패턴이 기록되는 것', '오작동(원치 않는 자동 실행)', '걱정 없음'])
    .setRequired(false);

  form.addParagraphTextItem().setTitle('14. (선택) ThinQ 앱 사용 중 최악의 경험 한 가지를 들려주세요')
    .setRequired(false);

  // 유입 채널 — Forms에 숨김 필드가 없어 문항+사전 채움 URL로 대체
  // 배포 시 채널별 사전 채움 링크 생성: 폼 편집 화면 ⋮ > '미리 채워진 링크 받기'
  form.addMultipleChoiceItem().setTitle('15. 이 설문을 어디에서 보셨나요? (이미 선택되어 있으면 그대로 두세요)')
    .setChoiceValues(['맘카페', '당근 동네생활', '레몬테라스', '오늘의집', '지인 소개', '블라인드', '스마트싱스 카페', '클리앙·뽐뿌', 'LGDX', '기타'])
    .setRequired(true);

  form.addTextItem().setTitle('16. (선택) 기프티콘 추첨을 원하시면 연락처를 남겨주세요')
    .setHelpText('추첨·발송에만 사용 후 즉시 폐기합니다.')
    .setRequired(false);

  // ── 종료 섹션 (스크리닝 아웃)
  const secEnd = form.addPageBreakItem().setTitle('설문 대상이 아니에요')
    .setHelpText('이 설문은 LG 스마트가전 보유자 대상입니다. 관심 가져주셔서 감사합니다!');
  secEnd.setGoToPage(FormApp.PageNavigationType.SUBMIT);

  // 문1 분기: 0대 → 종료 섹션 / 1대 이상 → 섹션 2
  q1.setChoices([
    q1.createChoice('0대 (없음)', secEnd),
    q1.createChoice('1대', secBasic),
    q1.createChoice('2~3대', secBasic),
    q1.createChoice('4대 이상', secBasic),
  ]);

  form.setConfirmationMessage('응답해주셔서 감사합니다! 🙏 추첨 결과는 개별 연락드립니다.');

  Logger.log('편집 URL: ' + form.getEditUrl());
  Logger.log('응답 URL: ' + form.getPublishedUrl());
}

const FORM_ID = '1x-JqmEHcyfekFUC2FHKnAKbk_QrnFi5WhlgdFQPNWUU';

/** 수정 전 백업: 기존 응답 전체를 로그로 덤프 */
function dumpResponses() {
  const form = FormApp.openById(FORM_ID);
  const rs = form.getResponses();
  Logger.log('총 응답 수: ' + rs.length);
  rs.forEach(function (r, i) {
    Logger.log('===== 응답 ' + (i + 1) + ' | 제출: ' + r.getTimestamp());
    r.getItemResponses().forEach(function (ir) {
      const v = ir.getResponse();
      Logger.log('  [' + ir.getItem().getTitle() + '] => ' + (Array.isArray(v) ? v.join(' ; ') : v));
    });
  });
}

/**
 * v2 수정 적용 (2026-07-21 파티 결정 반영)
 * ⚠️ 11-1은 타입 변경(객관식→체크박스)이라 삭제·재생성 — 해당 문항 기존 응답은 소실됨.
 *    실행 전 dumpResponses()로 백업할 것.
 */
function applyV2() {
  const form = FormApp.openById(FORM_ID);
  const L5 = ['1 전혀 없다', '2 없다', '3 보통', '4 자주 있다', '5 매우 자주 있다'];
  const items = form.getItems();
  function find(prefix) {
    for (var i = 0; i < items.length; i++) {
      if (items[i].getTitle().indexOf(prefix) === 0) return items[i];
    }
    return null;
  }

  find('2.').asMultipleChoiceItem().setChoiceValues(['사용해본 적 없음', '설치만 해둠', '월 1회 이하', '주 1~2회', '거의 매일']);
  find('4.').asMultipleChoiceItem().setChoiceValues(['1인 가구', '부부 (자녀 없음)', '자녀 있음 (미취학)', '자녀 있음 (취학 이상)', '부모님댁에 거주', '기타']);
  find('5.').setHelpText('가족 소유 집에 함께 사는 경우 등은 "기타"를 선택해주세요');
  find('5.').asMultipleChoiceItem().setChoiceValues(['자가', '전세', '월세', '기타']);
  find('8.').asMultipleChoiceItem().setChoiceValues(L5);
  find('9.').asMultipleChoiceItem().setChoiceValues(L5);
  find('10.').asMultipleChoiceItem().setChoiceValues(['1 전혀 부담 없다', '2 부담 없다', '3 보통', '4 부담된다', '5 매우 부담된다']);
  find('12.').asMultipleChoiceItem().setChoiceValues(['1 전혀 아니다', '2 아니다', '3 보통', '4 희망한다', '5 꼭 쓰고 싶다']);
  Logger.log('선택지 수정 완료 (2,4,5,8,9,10,12)');

  // 11-2: 질문·도움말·선택지 교체 (척도 유지 → 타입 변경 없음, 응답 보존)
  const q112 = find('11-2.');
  q112.setTitle('11-2. 밤 10시 이후, 잠든 뒤나 자다 깨서 집 상태를 확인하거나 조절한 적이 얼마나 있나요?')
      .setHelpText('예: 아이 방 온도 확인, 조명·에어컨 조절');
  q112.asMultipleChoiceItem().setChoiceValues(L5);
  Logger.log('11-2 교체 완료 (척도 유지)');

  // 11-1: 객관식 → 체크박스 (타입 변경이라 삭제 후 재생성, 원위치로 이동)
  const old111 = find('11-1.');
  const idx111 = old111.getIndex();
  form.deleteItem(old111);
  const new111 = form.addCheckboxItem()
    .setTitle('11-1. 스마트워치를 보유하고 계신가요? (여러 개면 모두 선택)')
    .setChoiceValues(['없음', '애플워치', '갤럭시워치', '가민', '기타'])
    .setRequired(true);
  form.moveItem(new111.getIndex(), idx111);
  Logger.log('11-1 → 체크박스 전환, index ' + idx111);

  // 11-3 신설: 11-2 바로 뒤에 배치
  const idx113 = form.getItems().filter(function (it) {
    return it.getTitle().indexOf('11-2.') === 0;
  })[0].getIndex() + 1;
  const new113 = form.addCheckboxItem()
    .setTitle('11-3. 앱으로 가전을 제어할 수 있다면 편할 것 같은 상황을 모두 골라주세요')
    .setChoiceValues([
      '아이 재우고 나서 불·가전 끄기',
      '자다 깨서 아이 방 온도·공기 확인',
      '잠들기 전 침대에서 조명·에어컨 조절',
      '밤중에 소음 걱정 없이 세탁기·건조기 예약',
      '새벽에 일어나 집 상태 한 번 훑기',
      '낮에 외출 중 집 상태 확인',
    ])
    .setRequired(true);
  new113.showOtherOption(true);
  form.moveItem(new113.getIndex(), idx113);
  Logger.log('11-3 신설, index ' + idx113);

  // 13: 금액 사다리 → 성향 문항으로 교체 (타입 동일, 응답 보존)
  const q13 = form.getItems().filter(function (it) {
    return it.getTitle().indexOf('13.') === 0;
  })[0];
  q13.setTitle('13. 이런 기능이 나온다면, 어떤 쪽에 가까우세요?');
  q13.asMultipleChoiceItem().setChoiceValues([
    '무료가 아니면 쓰지 않겠다',
    '무료로 써보고 괜찮으면 유료도 고려하겠다',
    '유료라도 쓸 의향이 있다',
  ]);
  Logger.log('13 교체 완료 (금액 → 성향)');

  // 13-2 신설: 13 바로 뒤
  const idx132 = form.getItems().filter(function (it) {
    return it.getTitle().indexOf('13.') === 0;
  })[0].getIndex() + 1;
  const new132 = form.addMultipleChoiceItem()
    .setTitle('13-2. 돈을 낸다면 어떤 방식이 가장 자연스러울까요?')
    .setChoiceValues([
      '월 구독료',
      '가전 살 때 가격에 포함',
      '한 번 결제하고 계속 사용',
      '무료 대신 광고·데이터 제공',
      '잘 모르겠다',
    ])
    .setRequired(true);
  form.moveItem(new132.getIndex(), idx132);
  Logger.log('13-2 신설, index ' + idx132);

  Logger.log('=== applyV2 완료 ===');
}
