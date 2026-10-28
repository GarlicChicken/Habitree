---
name: feedback-to-rule
description: 사용자가 결과를 바로잡거나 같은 지적을 되풀이할 때, 또는 Habitree 알림이 맞았다거나 틀렸다고 할 때 그 피드백을 규칙 DB에 남긴다(habitree rules similar, hit, add, miss). "또 그러네", "그거 말고", "이 경고 틀렸어", "잔소리야" 같은 말에 쓴다. Use when the user corrects the work, repeats the same feedback, or says a Habitree warning was right, wrong or noisy: record it with habitree rules hit, add or miss so the same feedback is never needed twice.
license: MIT
---

# 피드백을 규칙으로 · Feedback to rules

고치는 것과 동시에 남긴다. 사용자가 같은 말을 두 번 하지 않게 하는 것이 목적이다. / Record while fixing, so the user never repeats the same feedback.

1. 바로 더하기 · Add it: `habitree rules add --scope <가장 넓게 맞는 범위, 보통 code> --aspect <structure·quality·process 등> --rule "<무엇을 쓰고 무엇을 하지 않는지 구체적으로>" --why "<이유>" --feedback "<사용자가 한 말>"`. 미리 찾지 않아도 add가 같은 뜻 규칙을 찾아 알려 준다. / No need to search first: add reports a rule with the same meaning.
2. add가 같은 뜻 규칙을 알려 주면 · If add reports one: `habitree rules hit <id> --feedback "<사용자가 한 말>"` (권장 규칙은 필수로 오른다 / a should rule becomes must). 다른 뜻이면 `--force`로 더한다. / If it means something else, add with `--force`.
3. 규칙이 바뀌면 AGENTS.md의 '이 프로젝트의 규칙'이 바로 고쳐져 다음 세션이 읽는다. / Changing a rule refreshes AGENTS.md at once, so the next session reads it.
4. Habitree 알림이 틀렸거나 잔소리였으면 · A wrong or noisy warning: `habitree rules miss <id> --feedback "…"`. 잘못된 비율이 쌓이면 기준이 완화된다. / Enough misses relax the threshold.
5. 이 세션에서만 그 알림을 끄려면 · Mute for this session only: `habitree guard off <id>` ('틀렸다'로 세지 않는다 / not counted as a miss).

알림 끝의 `(규칙 <id>)`가 그 id다. / The id is the `(rule <id>)` at the end of each warning.
