"""guard의 틀 문구. 규칙마다 다른 문구는 규칙 DB의 message에 있고, 여기는 그것을 싸는 틀이다.
/ Frame texts for guard. Per-rule wording lives in the rule DB (message); these wrap it.

사람에게 보이는 글은 두 벌, AI에게 넣는 글도 설정 언어 한 벌만 골라 쓴다.
AI에게 넣는 글은 사실을 적는 말투로 쓴다(명령조는 주입 방어에 걸릴 수 있다는 공식 안내).
"""
from ..core.i18n import tr

T = {
    "head.warn": {"ko": "[Habitree 경고]", "en": "[Habitree warning]"},
    "head.stop": {"ko": "[Habitree 멈춤]", "en": "[Habitree stop]"},
    "head.info": {"ko": "[Habitree 알림]", "en": "[Habitree note]"},
    "head.delegate": {"ko": "[Habitree 위임]", "en": "[Habitree delegation]"},
    "suggest": {"ko": "제안:", "en": "Suggested:"},
    "rule_tail_ai": {"ko": "(규칙 {id})", "en": "(rule {id})"},
    "rule_tail_user": {
        "ko": "(규칙 {id} · 틀린 알림이면 `habitree rules miss {id} --feedback \"…\"` · "
              "이 세션만 끄기 `habitree guard off {id}`)",
        "en": "(rule {id} · if wrong: `habitree rules miss {id} --feedback \"…\"` · "
              "mute for this session: `habitree guard off {id}`)"},
    "user_prefix": {"ko": "Habitree: ", "en": "Habitree: "},
    "relay": {
        "ko": "Habitree 사용자 알림(화면에 이 알림을 보여 주지 않는 앱이 있어 함께 적는다). "
              "답 맨 앞에 다음 줄을 그대로 전하면 된다: «{line}»",
        "en": "Habitree note for the user (some apps do not show it on screen). "
              "Pass this line on verbatim at the start of the reply: «{line}»"},
    "stop.ask": {"ko": "같은 일이 계속되고 있어 이번 호출은 사용자 확인을 받는다.",
                 "en": "This keeps repeating, so this call needs the user's confirmation."},
    "stop.deny": {"ko": "맡긴 작업 중이라 사용자에게 묻지 않고 이번 호출을 막았다. "
                        "같은 시도를 멈추고, 지금까지 시도한 것과 막힌 점을 정리해 보고한다.",
                  "en": "During a delegated task the user is not asked, so this call was blocked. "
                        "Stop repeating it and report what was tried and where it is stuck."},
    "stop.user": {"ko": "같은 일이 되풀이돼 확인을 받아요. 계속해도 되면 허용, 아니면 거절해 주세요.",
                  "en": "This keeps repeating, so I am asking first. Allow to continue, or deny."},
    "summary.head": {"ko": "Habitree 이번 답의 알림 {n}개:", "en": "Habitree notes from this reply ({n}):"},
    "summary.tail": {"ko": "맞는 알림이면 `habitree rules hit <id> --feedback \"…\"`, "
                           "틀렸으면 `habitree rules miss <id> --feedback \"…\"`로 남겨 주세요.",
                     "en": "Record a useful one with `habitree rules hit <id> --feedback \"…\"`, "
                           "a wrong one with `habitree rules miss <id> --feedback \"…\"`."},
    "check.block": {
        "ko": "[Habitree 점검] 끝내기 전에 `habitree check`가 오류 {n}개를 찾았다:\n{items}\n"
              "고친 뒤 끝내면 된다. 지금 고칠 수 없는 것은 변경 기록의 '손볼 것'에 적고 그 사실을 보고한다.",
        "en": "[Habitree check] Before finishing, `habitree check` found {n} error(s):\n{items}\n"
              "Fix them, then finish. Anything that cannot be fixed now goes under 'To fix' in the change log, "
              "and the report says so."},
    "check.user": {"ko": "Habitree: 끝내기 전 점검에서 오류 {n}개가 나와 한 번 더 고치게 했어요.",
                   "en": "Habitree: the pre-finish check found {n} error(s), so the agent was asked to fix them."},
    "start.full": {
        "ko": "Habitree가 이 프로젝트의 작업 습관을 돕는다.\n"
              "작업 순환: 찾기(지도 {map}, `habitree rules brief <범위>`) → 있으면 쓰기 → 없으면 만들기"
              "(되풀이할 일이면 도구·모듈) → 기록(폴더 README·지도·{log}) → 못 고친 것은 '손볼 것'에 → "
              "끝내기 전 `habitree check`와 검증 명령.",
        "en": "Habitree supports this project's working habits.\n"
              "Work cycle: find (map {map}, `habitree rules brief <scope>`) → reuse → build if missing "
              "(tools or modules for repeated work) → record (folder README, map, {log}) → note what is left "
              "under 'To fix' → run `habitree check` and the verify commands before finishing."},
    "start.short": {"ko": "Habitree가 켜져 있다. 작업 순환과 필수 규칙은 AGENTS.md에 있다.",
                    "en": "Habitree is on. The work cycle and must rules are in AGENTS.md."},
    "start.must": {"ko": "필수 규칙:", "en": "Must rules:"},
    "start.react": {
        "ko": "작업 중에 '[Habitree 경고 … (규칙 <id>)]' 알림이 붙을 수 있다. 사용자가 그 알림이 맞았다고 하면 "
              "`habitree rules hit <id> --feedback \"…\"`, 틀렸거나 잔소리였다고 하면 "
              "`habitree rules miss <id> --feedback \"…\"`로 남긴다. 사용자 피드백은 고치면서 규칙으로 남긴다.",
        "en": "Notes like '[Habitree warning … (rule <id>)]' may appear while working. When the user says a note "
              "was right, record `habitree rules hit <id> --feedback \"…\"`; when wrong or noisy, "
              "`habitree rules miss <id> --feedback \"…\"`. Record user feedback as rules while fixing it."},
    "start.delegated": {"ko": "이 세션에는 맡긴 작업이 있다(\"{task}\"). 끝나면 대신 정한 것을 모아 보고한다.",
                        "en": "This session has a delegated task (\"{task}\"). Report the decisions made when done."},
    "delegate.limit": {
        "ko": "[Habitree 위임] 맡긴 작업이 정한 한도(도구 호출 {n}번)에 닿아 위임을 끝냈다. "
              "지금까지 한 것과 대신 정한 것을 보고하고, 이어서 할지 사용자에게 묻는다.",
        "en": "[Habitree delegation] The delegated task reached its limit ({n} tool calls), so delegation ended. "
              "Report progress and the decisions made, and ask the user whether to continue."},
    "delegate.cancel": {"ko": "[Habitree 위임] 사용자가 위임을 거뒀다. 이제부터는 평소처럼 확인하며 진행한다.",
                        "en": "[Habitree delegation] The user withdrew the delegation. From now on, confirm as usual."},
    "delegate.topic": {"ko": "[Habitree 위임] 새 요청이 맡긴 작업과 다른 주제라 위임을 끝냈다. 평소처럼 확인하며 진행한다.",
                       "en": "[Habitree delegation] The new request is a different topic, so delegation ended. "
                             "Confirm as usual."},
    "delegate.boundaries": {"ko": " 함께 받은 경계(위임 중에도 지킨다): {items}.",
                            "en": " Boundaries given with it (kept during delegation): {items}."},
    "delegate.suppressed": {"ko": " 위임 중 미뤄 둔 알림 {n}개: {items}.", "en": " Notes held back during delegation ({n}): {items}."},
    "delegate.none": {"ko": " 위임 중 미뤄 둔 알림은 없다.", "en": " No notes were held back during delegation."},
    "category.delete": {"ko": "지우기", "en": "deleting"},
    "category.deploy": {"ko": "배포·올리기", "en": "deploying or pushing"},
    "category.external": {"ko": "외부로 보내기", "en": "sending outside"},
    "category.payment": {"ko": "결제", "en": "payment"},
    "category.secrets": {"ko": "비밀 정보·개인정보", "en": "secrets or personal data"},
    "category.outside": {"ko": "작업 폴더 밖 수정", "en": "changes outside the project"},
    "category.outside_scope": {"ko": "맡긴 범위 밖 파일", "en": "a file outside the delegated scope"},
    "category.boundary": {"ko": "사용자가 정한 경계", "en": "a boundary the user set"},
}


def t(key, lang, **kw):
    text = tr(T[key], lang)
    return text.format(**kw) if kw else text


def fmt(text, facts):
    """빠진 자리표시자는 그대로 두는 format. / format that leaves unknown placeholders alone."""
    class _D(dict):
        def __missing__(self, k):
            return "{" + k + "}"
    try:
        return str(text).format_map(_D(facts or {}))
    except (ValueError, IndexError, AttributeError):
        return str(text)


def numbered(items, lang):
    marks = "①②③④⑤⑥⑦⑧⑨" if lang == "ko" else None
    out = []
    for i, s in enumerate(items):
        out.append(f"{marks[i]} {s}" if marks and i < len(marks) else f"{i + 1}) {s}")
    return " ".join(out)
