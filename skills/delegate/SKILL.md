---
name: delegate
description: 사용자가 "알아서 해 줘", "묻지 말고 끝까지 해", "추천대로 해", "맡길게"처럼 작업을 맡길 때 쓴다. 범위를 한 줄로 되말하고, 그 작업에 한해 되묻지 않고 추천안대로 진행하되 위험한 일은 그때도 묻고, 끝에 대신 정한 것을 모아 보고한다. Use when the user delegates a task ("just do it", "don't ask", "use your judgment", "your call"): restate the scope, proceed with the recommended options without questions for that task only, still confirm risky actions, and report the decisions at the end.
license: MIT
---

# 위임 · Delegation

1. 범위 밝히기 · State the scope (첫 줄 / first line):
   "이 작업(…)에 한해서는 되묻기 없이 추천안대로 진행하겠습니다. 다만 지우기·배포·외부로 보내기·결제·개인정보는 그때도 여쭙겠습니다."
   / "For this task (…) only, I will go with the recommended options without asking. Deleting, deploying, sending anything outside, payments and personal data will still need your OK."
2. 훅이 위임을 알아채지 못했으면 명령으로 켠다 · If the hook did not notice, turn it on:
   `habitree guard delegate on --task "<작업 한 줄>" --boundary "<지킬 경계>"`
3. 함께 받은 경계("지우지는 마", "don't push")는 끝까지 지킨다. 경계는 좁히기만 한다. / Keep every boundary given with the delegation; boundaries only narrow.
4. 결정마다 적어 둔다 · Keep a note of each decision: 무엇, 왜, 다른 안, 되돌리는 법 / what, why, the alternative, how to undo.
5. 끝 보고 · End report:
   - 대신 정한 것(번호를 붙여 위 네 가지와 함께) / decisions made, numbered, with the four items
   - 위임 중 미뤄 둔 알림 / notes held back during delegation (`habitree guard report`)
   - 실행한 검사와 결과(명령과 출력) / checks run, with commands and output
   - 확인이 필요한 것 / anything that needs confirmation
6. 사용자가 끝 보고에서 바로잡으면 피드백을 규칙으로 남긴다(feedback-to-rule). / Record corrections from the report as rules.

위임을 거두려면 "이제 물어보고 해" 또는 `habitree guard delegate off`. / To end it: "ask me first" or `habitree guard delegate off`.
