"""guard: 작업 중 비효율을 감지해 먼저 알리고, 위임을 기록한다. / In-flight inefficiency warnings and delegation.

  events.py     표준 이벤트(도구 이름, 입력, 결과 성패·길이, 파일 경로, 사용자 메시지)
  detectors.py  감지기(행동만 본다, 기준값은 규칙의 detect)
  engine.py     적기 → 판정 → 전달(반복 제한, 위임 처리)
  delegate.py   위임 신호·경계·위험한 일
  copyscan.py   복사 코드 찾기(줄 해시)
  claude.py     Claude Code 훅 입력·출력 어댑터
  install.py    훅 연결 정의(플러그인과 init --hooks가 함께 씀)
  texts.py      틀 문구(두 언어)
"""
