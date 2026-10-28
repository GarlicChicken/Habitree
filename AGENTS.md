<!-- habitree:begin habitree -->
## Habitree 작업 순환

이 프로젝트는 Habitree로 작업 습관을 관리한다. 모든 작업은 이 순서를 따른다.

1. 찾기: [지도](README.md)와 `habitree rules brief <범위>`로 관련 문서·도구·규칙을 먼저 본다.
2. 있으면 쓰기: 있는 것을 쓰고, 낡았거나 틀린 곳은 그 자리에서 고친다.
3. 없으면 만들기: 되풀이가 실제로 보일 때만 도구·모듈·양식으로 만든다. 한 번 쓰고 마는 것은 만들지 않는다.
4. 기록하기: 바꾼 것을 폴더 README, 지도, [변경 기록](LOG.md)에 함께 반영한다.
5. 고치기: 지금 못 고친 문제는 변경 기록의 '손볼 것'에 적는다. 쌓는 만큼 덜어낸다: 겹치거나 안 쓰이는 규칙·도구·코드는 합치거나 지운다.
6. 점검하기: 끝내기 전에 `habitree check`와 검증 명령을 실행하고 나온 문제를 고친다.

사용자 피드백은 고치는 것과 동시에 규칙으로 남긴다. 같은 뜻 규칙이 있으면 `habitree rules hit <id> --feedback "…"`, 없으면 `habitree rules add --scope … --aspect … --rule "…" --why "…" --feedback "…"`. 전체 규칙: [.habitree/RULES.md](.habitree/RULES.md).

### 필수 규칙 (요약)
[docs] 문서와 지도
- [필수·docs] 같은 내용을 여러 곳에 복사하지 않고 원본 한 곳에 두고 링크한다.
- [필수·docs] 도구가 만든 파일과 구역(habitree:begin/end 사이)은 직접 고치지 않는다. 원본을 고친 뒤 도구로 다시 만든다.

[security] 보안과 개인정보
- [필수·security] API 키·토큰·비밀번호·개인정보를 코드, 문서, 커밋에 넣지 않는다. 환경 변수나 .env(커밋 제외)로 받는다.
<!-- habitree:end habitree -->
