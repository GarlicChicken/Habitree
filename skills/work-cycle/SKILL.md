---
name: work-cycle
description: Habitree 작업 순환. 작업을 시작하거나 끝낼 때 지도(README)에서 먼저 찾고, 있으면 쓰고, 없으면 만들고, 기록하고, 끝내기 전에 habitree check와 검증 명령으로 점검한다. "작업 시작해", "다 됐어?", "마무리해 줘", "점검해 줘" 같은 요청에 쓴다. Use when starting or finishing work in a Habitree project, or when asked "are you done?" or "wrap it up": search the map first, reuse, build only what is missing, record changes, and run habitree check plus the verify commands before saying done.
license: MIT
---

# 작업 순환 · Work cycle

1. 찾기 · Find: `README.md` 지도와 `habitree rules brief <범위>`로 관련 문서·도구·규칙을 먼저 본다. / Read the map and `habitree rules brief <scope>` first.
2. 있으면 쓰기 · Reuse: 있는 것을 쓰고, 낡은 곳은 그 자리에서 고친다. / Use what exists; fix stale parts on the spot.
3. 없으면 만들기 · Build: 되풀이할 일이면 도구·모듈·양식으로 만든다. / Make repeated work a tool, module or template.
4. 기록하기 · Record: 폴더 README, 지도, 변경 기록(LOG.md)을 함께 고친다. / Update the folder README, the map and the change log.
5. 고치기 · Fix later: 지금 못 고친 것은 변경 기록의 '손볼 것'에 적는다. / Write what is left under "To fix".
6. 점검하기 · Check: `habitree check`와 설정의 verify 명령을 돌리고, 명령과 결과를 보고에 넣는다. / Run `habitree check` and the verify commands; put the commands and results in the report.

'다 됐다'고 말하기 전에 6번의 결과가 있어야 한다. / Do not say "done" without the results of step 6.
