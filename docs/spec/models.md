# 모델 배분과 검증

AI에게 일을 맡길 때 가장 비싼 모델을 늘 쓰면 돈이 새고, 가장 싼 모델을 늘 쓰면 틀린 결과를 고치느라 시간이 샌다. Habitree의 `models`와 `verify`는 그 사이에서 일의 종류마다 시작할 자리를 정해 두고, 싼 자리에서 시작한 일이 틀렸을 때 기계가 확인할 수 있는 신호로만 한 칸씩 올리게 한다. 이 문서는 그렇게 정한 이유와 방향을 적는다. 영어 본문은 [아래](#english)에 있다.

## 1. 왜 모델 배분을 다루나

토큰, 비용, 정확도는 함께 움직인다.

같은 일이라도 모델과 강도에 따라 쓰는 토큰이 다르고 단가도 다르다. 2026-10-28에 공식 가격 문서에서 확인한 값으로 Claude Haiku 5.5는 입력 100만 토큰당 0.10달러, Claude Opus 5.5는 4달러다. 그렇다고 싼 모델이 늘 싼 것은 아니다. 틀린 결과를 다시 돌리면 그 비용도 든다. Anthropic은 토큰당이 아니라 끝낸 작업당 비용으로 비교하라고 권한다(비용·지능 최적화 문서).

같은 문서의 내부 측정이 방향을 보여 준다. Anthropic 스스로 "방향을 보여 줄 뿐 보장이 아니다"라고 적은 수치다. SWE-bench Pro 일부 과제에서 Opus 5.5를 low로 돌리면 87.4%를 작업당 0.11달러에, high로 돌리면 95.3%를 0.29달러에 풀었다. 모든 과제를 low로 돌리고 실패한 13%만 high로 다시 돌리면 약 97%를 약 0.17달러에 풀었다. 다만 실패를 걸러 내는 판정(여기서는 과제의 테스트)이 있어야 하고, 나쁜 결과를 통과시키는 판정이면 실패가 그대로 지나간다고 함께 적었다.

그래서 Habitree가 다루는 질문은 "어떤 모델이 제일 좋은가"가 아니라 "이 일은 어디서 시작하고, 무엇을 보고 언제 올리나"다.

## 2. 칸: 등급과 강도

정책은 회사 이름이 아니라 칸(cell)으로 쓴다. 칸은 `등급:강도`다.

- **등급** `low`·`mid`·`high`·`top`(하·중·상·최상). 세 회사(Anthropic, OpenAI, Google) 모두 이 네 줄에 놓을 모델이 있다. Google에는 최상 가격대가 없어서 상 등급에 최대 강도로 대신한다.
- **강도** `low`·`medium`·`high`·`max`. 세 회사 모두 같은 모델 안에서 생각하는 양을 정하는 값을 둔다(Anthropic `output_config.effort`, OpenAI `reasoning.effort`, Google `thinking_level`). 대응표가 회사의 값으로 옮긴다. 중립 `max`는 Anthropic과 OpenAI에서 `xhigh`, Google에서 `high`가 된다.

강도를 등급과 따로 둔 것은 모델 이름만 보면 놓치는 선택지가 있어서다. 앞의 Anthropic 측정에서 Sonnet 5.5 high는 87.6%, Opus 5.5 low는 87.4%였다. 공식 안내도 두 번째 모델을 더하기 전에 지금 모델의 강도부터 훑어 보라고 한다. 승격할 때도 단계를 건너뛴 경우에는 강도를 먼저 올린다.

회사 이름 대신 등급으로 쓴 것은 같은 자리라도 값이 회사마다 달라서다. "상" 자리의 Opus 5.5는 입력/출력 100만 토큰당 4/20달러, GPT-6.1 Sol은 2/10달러다(두 회사 가격 문서, 2026-10-28). 등급은 가격대가 아니라 맡기는 역할이다. 회사 사이 성능이 같은지는 아무도 재지 않았으므로, 등급과 모델의 대응은 각 회사가 모델에 붙인 설명으로 맞춘 추정이라고 대응표에 적어 두었다. 회사를 바꾸려면 정책은 그대로 두고 대응표만 바꾸면 된다.

기본 강도에는 기대지 않는다. 모델마다 기본값이 다르다(API 기준 Opus 5.5는 medium, Sonnet 5.5는 high). 그래서 Habitree가 내보내는 설정에는 늘 강도를 적는다.

## 3. 기본 칸과 근거

기본 칸은 규칙 DB의 `task` 범위에 있다(꾸러미 [task.json](../../src/habitree/data/packs/task.json), `habitree init`이 넣는다). 하위 범위는 가까운 상위 범위의 칸, 자동 승격 상한(`max_cell`), 검증 묶음(`verify`)을 물려받는다. 근거는 규칙의 `why`에 공식 문서로 확인한 것 [확인], 프로젝트나 논문이 스스로 밝힌 것 [주장], 우리 판단 [추정]으로 나눠 적었다.

| 작업 | 기본 칸 | 승격 상한 | 검증 | 근거 |
|---|---|---|---|---|
| `task` (유형 미정) | mid:medium | high:high | 전부 | [확인] Claude Code 비용 문서: Sonnet이 대부분의 코딩을 잘 하고 Opus보다 싸다 |
| `task/explore` | low:medium | mid:medium | 없음 | [확인] 같은 문서: 단순한 서브에이전트 작업은 `model: haiku`. 강도 문서: Haiku 5.5는 긴 에이전트 프롬프트에서 low일 때 검색을 건너뛰기 쉽다 |
| `task/summarize` | low:low | mid:medium | 없음 | [확인] Aider는 대화 요약에 약한 모델을 쓴다. Haiku 5.5는 프롬프트가 10만 토큰을 넘으면 입력 단가가 5배(가격 문서) |
| `task/commit-message` | low:low | mid:low | 없음 | [확인] Aider는 커밋 메시지를 약한 모델로 먼저 만든다. opencode는 제목 생성에 `small_model` |
| `task/bulk` | low:low | mid:medium | 없음 | [확인] Haiku 5.5는 분류·추출·라우팅용, Batch API 50% 할인(모델 개요) |
| `task/plan` | high:high | top:high | 없음 | [확인] Claude Code `opusplan`, 모델·강도 글 "설계 결정은 큰 모델". [추정] 방향이 틀리면 뒤 작업이 헛수고 |
| `task/code` | mid:medium | high:high | 전부 | [확인] 강도 문서: Sonnet 5.5로 에이전트 코딩을 할 때 명세가 분명하면 medium부터 |
| `task/code/clear-spec` | mid:medium | high:high | 전부 | [확인] 모델·강도 글: 정확히 설명할 수 있는 변경은 작은 모델 |
| `task/code/ambiguous` | high:medium | top:high | 전부 | [확인] 모델 개요: 잘 모르면 Opus 5.5로 시작(기본 강도 medium) |
| `task/refactor/mechanical` | mid:low | high:medium | 전부 | [확인] 기계적 변경은 작은 모델. [추정] 테스트가 있으면 low로 충분 |
| `task/refactor/structural` | high:high | top:high | 전부 | [확인] 비용 문서: Opus는 복잡한 설계 결정과 여러 단계 추론에 |
| `task/debug` | high:high | top:high | 전부 | [확인] 모델·강도 글: 미묘한 버그는 큰 모델 |
| `task/test` | mid:medium | high:medium | 전부 | [추정] 통과해도 아무것도 검사하지 않는 테스트가 있을 수 있어 사람이 본다 |
| `task/review` | high:medium | top:high | 없음 | [주장] LLM 판정자는 자기 계열 답을 좋게 본다(arXiv 2306.05685). [확인] Codex의 `review_model`. [추정] 작성 칸보다 한 단계 위, 되도록 다른 회사 |
| `task/docs` | mid:medium | high:medium | 없음 | [추정] 읽기 쉬움은 사람이 본다 |
| `task/review/security` | **high:high 하한** | top:high | 없음 | [추정] 놓친 문제를 되돌리는 비용이 매우 크다 |
| `task/risky` | **high:high 하한** | top:high | 전부 | [추정] 인증·돈·개인정보·비밀값·마이그레이션·삭제·배포는 되돌리기 비용이 매우 크다 |
| `task/long-autonomous` | top:high | top:high | 전부 | [확인] 모델 개요: Fable 5.1은 오래 도는 에이전트 작업용. [추정] 최상은 이런 직접 지정과 승격으로만 |

"검증 전부"는 설정 `verify`에 등록한 명령 전부, "없음"은 기계 검증이 없는 작업이다.

권장(should) 규칙의 칸은 기본값이라 기록에 따라 움직인다. 필수(must) 규칙의 칸은 하한이라 통계로도, 자동으로도 내려가지 않는다. 하한은 규칙 사다리의 끝까지 올라가 있다. `habitree check`는 에이전트 파일의 모델이 하한보다 낮으면 오류(`models.floor`)를 내고, `habitree models export`는 하한보다 낮은 값을 쓰지 않는다. 사람이 말로 한 피드백("보안 리뷰는 하위 모델로 하지 마")은 다른 규칙과 똑같이 바로 필수가 된다.

## 4. 낮은 칸의 결과를 검증하고 올리기

시작은 싸게, 올리는 것은 증거로 한다. 그 증거가 기계 검증이다. `habitree verify`는 설정 `verify`에 적은 명령(`npm test`, `pytest`, `go test ./...`, `cargo test` 등 무엇이든)을 셸 없이 차례로 돌리고 종료 코드 0을 합격으로 본다. 언어와 도구를 가리지 않고 지켜지는 가장 넓은 약속이 종료 코드라서다. `--task`를 주면 결과가 모델 배분 기록에도 남는다. 도구가 없어 명령을 돌리지 못한 것은 모델 품질의 문제가 아니므로 기록하지 않는다.

자동 승격은 기계 검증이 있는 작업만 한다. RouterBench(arXiv 2403.12031)는 싼 모델부터 돌리고 판정으로 올리는 계단식 라우터가 판정 오류율 0.2를 넘으면 급격히 나빠진다고 보고했다. 판정을 믿을 수 없으면 사다리를 타는 것이 오히려 손해다. 그래서 검증이 없는 작업은 처음부터 기본 칸으로 하고, 결과는 사람이나 다른 회사 모델이 본다.

실패는 신호에 따라 다르게 다룬다(`habitree models escalate`).

| 신호 | 다음 할 일 |
|---|---|
| `skipped_steps` 파일을 안 읽음, 테스트를 안 돌림 | 강도 +1, 강도가 이미 최대면 등급 +1 |
| `confident_wrong` 맥락이 충분한데도 틀림 | 등급 +1 |
| `loop` 같은 자리를 맴돎 | 멈추고 등급 +1 |
| `format_error` 형식이 깨짐, 패치가 안 붙음 | 같은 칸에서 1번 더, 그다음 등급 +1 |
| `infra` 429, 5xx, 과부하, 컨텍스트 초과 | 등급은 그대로, 같은 등급의 다른 배포·회사 |
| `refusal` 거절 | 등급은 그대로, 같은 등급의 다른 모델 |
| `truncated` 출력이 잘림 | 같은 칸, 출력 한도를 늘리거나 강도를 낮춤 |

건너뜀은 강도로, 자신 있게 틀림은 모델로 푼다는 구분은 Anthropic의 Claude Code 모델·강도 글(2026-07-07)에서 왔다. 그 글은 두 손잡이를 돌리기 전에 맥락과 지시문부터 보라고 하고, `escalate`도 같은 조언을 붙인다. 장애를 품질 실패와 나눈 것은 LiteLLM이 장애 대체(`fallbacks`)를 따로 두는 방식을 따른 것이다. 둘을 섞으면 서버 장애 때문에 등급이 올라가 돈이 샌다.

작업 하나에서 자동으로 올리는 것은 2단계, 시도는 4번까지다. 그다음은 실패 기록과 함께 사람에게 넘긴다(`escalate`의 종료 코드 3). 이 두 숫자는 추정이다. 측정이 뒷받침하는 것은 "실패한 것을 한 단계 위에서 한 번 다시"까지라서, 그보다 길게 기계에 맡기지 않는다. 하한이 있는 위험 작업은 자동으로 올리지 않고 바로 사람에게 넘기며, 상한(`max_cell`)을 넘는 승격도 사람에게 넘긴다. 올린 칸은 새 서브에이전트에서 실패 요약만 넘겨 돌린다. 요청 사이에 최상위 강도를 바꾸면 프롬프트 캐시가 다시 시작된다고 Anthropic 강도 문서가 밝혔기 때문이다.

### 기록으로 기본 칸 고치기

`habitree models record`와 `habitree verify --task`는 결과를 `.habitree/state/models-events.jsonl`에 한 줄씩 더한다. 시각은 UTC로 저장하고, 이 폴더는 커밋하지 않는다.

```
{"at": "2026-10-28T11:45:11Z", "task": "task/code", "result": "pass", "cell": "mid:medium", "source": "verify"}
```

`habitree models tune`은 작업마다 지금 기본 칸으로 돌린 최근 20번을 본다. 품질 실패가 20% 이상이면 기본 칸을 한 단계(강도 먼저) 올리고 규칙 이력에 숫자를 남긴다. 관측이 10번이 안 되면 움직이지 않고, 장애는 세지 않는다. 내리는 쪽은 느리게 간다. 최근 20번에서 품질 실패가 5% 이하이면 한 단계 내려 볼 만하다고 제안만 하고, 바꾸는 것은 사람이 `habitree models set`으로 이유를 적어 한다. 하한은 통계로 바꾸지 않는다.

이 숫자들도 추정이다. 10번은 LiteLLM의 adaptive_router가 시작값의 무게를 10으로 두고 실제 관측이 그만큼 쌓이면 의미 있게 움직인다고 적은 것을 참고했다. 올림을 빠르게, 내림을 느리게 둔 것은 칸이 오르내리며 흔들리지 않게 하려는 것이다. 칸이 바뀌면 규칙 글 속의 칸 표기(예: `` `mid:medium` ``)도 함께 바뀌어, AI가 읽는 규칙 요약과 실제 칸이 어긋나지 않는다.

## 5. 모델 관리

대응표는 [vendors.json](../../src/habitree/data/vendors.json)이고 형식은 [vendors.schema.json](../../src/habitree/data/schema/vendors.schema.json)이다. 모델 하나마다 고정 ID, 별칭, 받는 강도 값, 가격(입력·출력·캐시 읽기·캐시 쓰기, 100만 토큰당 USD, 프롬프트 크기 구간과 예고된 가격 변경 포함), 컨텍스트, 단종일, 출처 URL, 확인일을 적는다. 확인하지 못한 값은 추측해서 채우지 않고 `null`과 메모로 둔다.

- **고정 ID와 별칭을 나눈다.** Anthropic은 모든 모델 ID가 고정 스냅숏이라고 밝혔지만, Claude Code의 `opus`·`sonnet`·`haiku`는 버전에 따라 가리키는 모델이 바뀐다. 다시 돌렸을 때 같은 결과를 얻으려고 내보내기는 기본으로 고정 ID를 쓴다. 편한 쪽을 원하면 `models.claude_model`을 `"alias"`로 바꾼다. OpenAI 모델 문서에는 이번에 날짜 스냅숏이 보이지 않아, OpenAI ID가 고정인지는 확인하지 못한 채(`pinned: null`)로 두었다.
- **단종을 미리 안다.** 예고 기간은 회사마다 다르다. Anthropic은 공개 모델 단종 60일 전 이상, OpenAI는 정식 모델 6개월 이상·특수 변형 3개월 이상·preview는 2주 정도, Google은 preview 2주 이상과 `-latest` 별칭의 깨지는 변경 2주 전 메일이다(각 회사의 단종·모델 문서, 2026-10-28). `habitree check`는 쓰는 모델의 단종일이 90일 안이면 경고한다(`models.deprecated`). 쓰는 모델은 기본 회사의 등급 모델과 `models.agents`에 적은 에이전트 파일의 모델이다.
- **가격은 바뀐다.** 2026-10-28 조사 때 본 한 참고 자료는 Sonnet 5.5 캐시 읽기를 0.20달러로 적었지만 공식 가격 문서는 0.10달러였다. 그래서 회사마다 확인일을 두고 90일이 지나면 알린다(`models.price-stale`). 고칠 때는 공식 페이지를 다시 읽고 프로젝트의 `.habitree/vendors.json`에 바뀐 항목만 적는다. 이 파일은 항목 단위로 덮어쓴다. 모델 하나의 가격만 바꾸거나, 회사를 더하거나, `null`로 모델을 빼는 것이 된다.

```json
{"vendors": {"anthropic": {"checked": "2027-01-20",
  "models": {"claude-opus-5-5": {"price": {"input": 4, "output": 20}, "checked": "2027-01-20"}}}}}
```

### 다른 코드가 쓰는 함수

다음 버전의 세션 분석(`audit`)은 세션 기록의 토큰을 돈으로 바꿀 때 `core/vendors.py`의 `price()`를 쓴다. 이름과 반환 형태를 약속으로 둔다.

```
load(ctx=None) -> dict
    기본 표 + .habitree/vendors.json(항목 단위 병합). 스키마에 맞지 않으면 HabitreeError.
resolve(cell, vendor, table=None) -> dict
    {vendor, cell, tier, effort, model, model_name, aliases, pinned, used_tier, used_effort,
     effort_param, effort_value, substituted, reason{ko,en}, price, checked, source}
price(model_id, table=None, on=None) -> dict | None
    model_id  고정 ID, 별칭, "회사/ID", Bedrock ID(대소문자와 "[1m]"은 무시)
    on        날짜. 그날 효력이 있는 가격(예고된 변경 반영). 기본은 오늘(UTC)
    돌려줌    {model, vendor, currency: "USD", per_tokens: 1000000,
               input, output, cache_read, cache_write, cache_write_long, cache_storage_hour,
               above: [{prompt_tokens, input, output, ...}], upcoming: [{from, ...}],
               as_of, checked, source, note}
              모르는 모델이나 가격을 확인하지 않은 모델은 None. 값을 모르는 칸은 None.
deprecations(within_days=90, table=None, today=None, models=None) -> list[dict]
    [{vendor, model, name, status, retire, days_left, replacement, source}]
checked_age_days(table=None, vendor=None, today=None) -> int | None | dict
```

`cache_write`는 짧은 캐시 쓰기(Anthropic 5분, OpenAI 30분), `cache_write_long`은 긴 캐시 쓰기(Anthropic 1시간, OpenAI 12시간)다. `above`는 프롬프트가 `prompt_tokens`를 넘을 때의 단가다.

## 6. 다른 도구로 내보내기

정책은 하나이고, 각 도구의 설정은 거기서 만든다(`habitree models export <대상>`).

| 대상 | 만드는 것 |
|---|---|
| `claude` | 설정 `models.agents`({에이전트 이름: 작업})에 적은 `.claude/agents/<이름>.md`의 머리말에서 `model`과 `effort`만 고친다. 본문은 그대로 둔다. `--write`가 없으면 미리 보기 |
| `codex` | 칸마다 `~/.codex/ht-<등급>-<강도>.config.toml` 프로필, `config.toml`에 `review_model`과 `plan_mode_reasoning_effort` |
| `aider` | `.aider.conf.yml`: `model`, `weak-model`, `editor-model`, `reasoning-effort`, `test-cmd`, `lint-cmd` |
| `litellm` | `config.yaml`: 칸마다 `model_name`, 같은 칸의 다른 회사 모델을 장애 대체(`fallbacks`)로 |
| `opencode` | `opencode.json`: `model`, `small_model`, `agent.<이름>.model` |

`claude` 말고는 표준 출력으로만 낸다. 형식은 2026-10-28에 각 도구의 공식 문서로 확인했고, 확인하지 못한 부분(aider 모델 이름의 회사 접두어, Codex 프로필 파일이 `review_model`을 읽는지, LiteLLM `fallbacks`의 자리 등)은 출력 안에 주석으로 밝힌다.

## 7. 라우터를 직접 만들지 않은 이유

요청마다 모델을 고르는 라우터를 만드는 길도 있었다. 만들지 않았다.

1. 실제로 모델을 나누는 일은 이미 각 도구가 한다. Claude Code 서브에이전트의 `model`·`effort`, Codex 프로필, Aider의 약한 모델, opencode의 `small_model`이 그렇다. Habitree는 그 설정을 정책 하나에서 만들어 주면 된다.
2. 라우팅·장애 대체·예산은 LiteLLM이 이미 한다. 회사마다 다른 API를 맞추는 일은 유지 부담이 크다. 2026-10-28에 LiteLLM 저장소의 열린 이슈는 5,704개였고, 최근 것은 대부분 회사별 변환 문제였다.
3. 넓은 벤치마크에서 학습형 라우터가 단순한 기준선을 안정적으로 넘지 못했다(RouterBench, LLMRouterBench arXiv 2601.07206).
4. API 키를 다루면 보안 부담이 생기고, 표준 라이브러리만 쓰는 원칙과도 맞지 않는다.
5. 요청마다 모델을 바꾸면 같은 대화 안에서 캐시를 잃기 쉽다. Habitree는 서브에이전트와 세션의 경계에서만 칸을 바꾼다.

## 8. 명령과 설정

```
habitree models                                작업별 칸과 회사별 대응표
habitree models show <작업>                    작업 하나: 회사별 모델·강도·가격
habitree models pick <작업> [--vendor V] [--json]
habitree models escalate <작업> --signal <신호> [--from 칸] [--attempt N] [--json]
habitree models record <작업> --result pass|quality_fail|infra_fail [--cell 칸] [--note "…"]
habitree models tune [--dry-run]
habitree models set <작업> --cell 칸 --why "…"
habitree models export claude|codex|aider|litellm|opencode [--write]
habitree models check
habitree verify [이름…] [--json] [--task 작업] [--cell 칸]
```

작업 이름은 `task/`를 빼고 써도 된다(`explore`는 `task/explore`).

```json
{
  "verify": {"test": ["pytest", "-q"], "types": ["npx", "tsc", "--noEmit"],
             "go": {"cmd": ["go", "test", "./..."], "timeout": 900}},
  "models": {"vendor": "anthropic", "agents": {"explorer": "task/explore", "reviewer": "task/review"}}
}
```

설정 파일에 `models` 절이 없으면 `habitree check`는 모델 점검을 건너뛴다. 나머지 설정(`claude_model`, `deprecation_days`, `price_stale_days`, `tune`, `escalate`)의 기본값은 `src/habitree/core/config.py`에 있다. 점검 항목은 [check.md](check.md)에 있다.

## English

Using the most expensive model for everything wastes money; using the cheapest for everything wastes time fixing wrong results. Habitree's `models` and `verify` set a starting place for each kind of work and move up one cell at a time, only on signals a machine can check. This section explains why, and in which direction.

### 1. Why model allocation

Tokens, cost and accuracy move together.

The same task spends different tokens at different prices depending on model and effort. On the official pricing page checked on 2026-10-28, Claude Haiku 5.5 input costs $0.10 per million tokens and Claude Opus 5.5 costs $4. A cheap model is not always cheap, though: re-running wrong results costs too. Anthropic recommends comparing cost per completed task, not per token (cost and intelligence guide).

Internal measurements in the same guide show the direction; Anthropic itself calls them directional, not guarantees. On a subset of SWE-bench Pro, Opus 5.5 at low solved 87.4% at $0.11 per task and at high 95.3% at $0.29. Running everything at low and re-running only the 13% that failed at high solved about 97% for about $0.17. The guide adds that this needs a failure signal (there, the benchmark's own tests), and that a checker which passes bad work lets those failures through.

So Habitree does not ask "which model is best" but "where does this task start, and what evidence moves it up".

### 2. Cells: tier and effort

Policy is written in cells, not vendor names. A cell is `tier:effort`.

- **Tier** `low`, `mid`, `high`, `top`. All three vendors (Anthropic, OpenAI, Google) have a model for each row. Google has no top price tier, so its high tier at max effort stands in.
- **Effort** `low`, `medium`, `high`, `max`. All three vendors let one model think more or less (Anthropic `output_config.effort`, OpenAI `reasoning.effort`, Google `thinking_level`). The vendor table translates: neutral `max` becomes `xhigh` at Anthropic and OpenAI and `high` at Google.

Effort is separate from tier because model names alone hide options. In the same Anthropic measurements, Sonnet 5.5 at high scored 87.6% and Opus 5.5 at low 87.4%. The official guidance also says to sweep effort on the current model before adding a second one, so escalation raises effort first when steps were skipped.

Tiers replace vendor names because the same role is priced differently. In the "high" row, Opus 5.5 costs $4/$20 per million input/output tokens and GPT-6.1 Sol $2/$10 (both pricing pages, 2026-10-28). A tier is a role, not a price band. Nobody has measured whether vendors are equal at a tier, so the table says its mapping is an estimate based on each vendor's own model descriptions. To switch vendors, keep the policy and change only the table.

Habitree never relies on default effort. Defaults differ (on the API, Opus 5.5 defaults to medium and Sonnet 5.5 to high), so every exported setting states effort explicitly.

### 3. Default cells and their basis

Default cells live in the `task` scopes of the rule DB ([task.json](../../src/habitree/data/packs/task.json), installed by `habitree init`). Child scopes inherit the nearest parent's cell, escalation cap (`max_cell`) and verification (`verify`). Each rule's `why` separates [verified] facts from official docs, [claim]s that projects or papers make about themselves, and our [estimate]s. The table in [section 3](#3-기본-칸과-근거) lists every task with its basis; in short:

- Cheap and checkable work starts low: exploration `low:medium`, summaries, commit messages and bulk work `low:low`.
- Ordinary coding starts in the middle: `task/code` and `task/code/clear-spec` at `mid:medium`, mechanical refactoring at `mid:low`.
- Hard or ambiguous work starts high: planning, structural refactoring and debugging at `high:high`, ambiguous code and review at `high:medium`.
- Risky work (auth, money, personal data, secrets, migrations, deletion, deploys) and security review have a **floor** of `high:high`.
- Long autonomous work uses `top:high`; the top tier is otherwise reached only by escalation.

Cells in should rules are defaults and move with recorded outcomes. Cells in must rules are floors: neither statistics nor automation lowers them. Floors sit at the top of the rule ladder: `habitree check` reports an error (`models.floor`) when an agent file's model is below the floor, and `habitree models export` never writes a lower value. Spoken feedback ("never review security on a small model") becomes a must rule right away, like any other rule.

### 4. Verifying low-cell results and escalating

Start cheap, move up on evidence. The evidence is machine verification. `habitree verify` runs the commands under `verify` in the config (`npm test`, `pytest`, `go test ./...`, `cargo test`, anything) one by one without a shell, and exit code 0 passes. The exit code is the widest promise every language and tool keeps. With `--task`, the outcome is also recorded for model allocation. A command that could not start (a missing tool) says nothing about model quality, so it is not recorded.

Only tasks with machine verification escalate automatically. RouterBench (arXiv 2403.12031) reports that cascades, which start cheap and escalate on a judge, degrade sharply once judge error exceeds 0.2. When the judge cannot be trusted, climbing the ladder costs more than it saves. Tasks without verification run at their default cell, and a person or a model from another vendor reviews the result.

Failures are handled by signal (`habitree models escalate`):

| Signal | Next step |
|---|---|
| `skipped_steps` unread files, tests not run | effort +1, or tier +1 if effort is already max |
| `confident_wrong` wrong despite enough context | tier +1 |
| `loop` going in circles | stop, tier +1 |
| `format_error` broken format, patch does not apply | one more try in the same cell, then tier +1 |
| `infra` 429, 5xx, overload, context overflow | same tier, another deployment or vendor |
| `refusal` | same tier, another model |
| `truncated` | same cell, raise the output limit or lower effort |

Effort for skipped steps and a bigger model for confident mistakes comes from Anthropic's Claude Code model and effort article (2026-07-07), which also says to look at context and instructions before turning either knob; `escalate` repeats that advice. Keeping outages apart from quality failures follows LiteLLM, which configures `fallbacks` separately. Mixing them would raise tiers because of server trouble and leak money.

Per task, automatic escalation stops after 2 steps or 4 attempts; then the task goes to a person with its failure log (exit code 3 from `escalate`). Both numbers are estimates: the measurements support "re-run the failures one step higher, once", so the machine is not trusted for longer chains. Risky tasks with a floor go straight to a person, and so does any step beyond the cap (`max_cell`). An escalated cell runs in a fresh subagent that receives only a failure summary, because Anthropic's effort docs state that changing top-level effort between requests restarts the prompt cache.

#### Tuning defaults from records

`habitree models record` and `habitree verify --task` append one line per outcome to `.habitree/state/models-events.jsonl`, with UTC timestamps; the folder is not committed.

`habitree models tune` looks at the last 20 runs of each task at its current default cell. If quality failures reach 20%, it raises the default one step (effort first) and writes the numbers into the rule history. Below 10 runs it does nothing, and outages are not counted. Lowering is slow: when quality failures over the last 20 runs are 5% or less, it only suggests one step down, and a person applies it with `habitree models set` and a reason. Floors are never changed by statistics.

These numbers are estimates too. The 10-run minimum follows LiteLLM's adaptive_router, which gives its starting values a weight of 10 and notes that about that many real observations move it meaningfully. Raising fast and lowering slowly keeps cells from oscillating. When a cell changes, the cell notation inside the rule text (for example `` `mid:medium` ``) changes with it, so the rule summary the AI reads stays in step with the real cell.

### 5. Managing models

The vendor table is [vendors.json](../../src/habitree/data/vendors.json), with its format in [vendors.schema.json](../../src/habitree/data/schema/vendors.schema.json). Each model has a pinned ID, aliases, accepted effort values, prices (input, output, cache read, cache write, USD per million tokens, with prompt-size bands and announced price changes), context, retirement date, source URL and checked date. Unverified values are never guessed; they stay `null` with a note.

- **Pinned IDs and aliases are kept apart.** Anthropic states that every model ID is a pinned snapshot, but Claude Code's `opus`, `sonnet` and `haiku` point to different models across versions. For reproducible runs, exports use pinned IDs by default; set `models.claude_model` to `"alias"` for convenience. The OpenAI models page showed no dated snapshots this time, so whether OpenAI IDs are pinned is recorded as unknown (`pinned: null`).
- **Retirements are known in advance.** Notice periods differ: Anthropic gives at least 60 days for public models; OpenAI at least 6 months for GA models, 3 months for specialized variants and about 2 weeks for previews; Google at least 2 weeks for previews and 2 weeks' email notice for breaking changes behind `-latest` (each vendor's deprecation and model pages, 2026-10-28). `habitree check` warns when a model in use retires within 90 days (`models.deprecated`). Models in use are the default vendor's tier models and the models in agent files listed under `models.agents`.
- **Prices change.** During the 2026-10-28 review, one reference listed Sonnet 5.5 cache reads at $0.20 while the official pricing page said $0.10. Each vendor therefore carries a checked date, and `habitree check` notes when it is over 90 days old (`models.price-stale`). To update, re-read the official pages and put only the changed entries in the project's `.habitree/vendors.json`, which overrides the table entry by entry: change one model's price, add a vendor, or remove a model with `null`.

#### Functions other code relies on

The next version's session audit (`audit`) uses `price()` from `core/vendors.py` to turn session tokens into money. Names and return shapes are a contract; the signatures are listed in [the Korean section](#다른-코드가-쓰는-함수). `price(model_id, table=None, on=None)` accepts a pinned ID, an alias, `provider/ID` or a Bedrock ID (case and `[1m]` ignored), applies announced price changes effective on `on` (default: today, UTC), and returns `model, vendor, currency, per_tokens, input, output, cache_read, cache_write, cache_write_long, cache_storage_hour, above, upcoming, as_of, checked, source, note`, or `None` for unknown models and models whose price was not verified. `cache_write` is the short cache write (Anthropic 5 minutes, OpenAI 30 minutes) and `cache_write_long` the long one (Anthropic 1 hour, OpenAI 12 hours).

### 6. Exporting to other tools

There is one policy, and each tool's settings are generated from it (`habitree models export <target>`):

- `claude` edits only `model` and `effort` in the front matter of `.claude/agents/<name>.md` for agents listed under `models.agents` ({agent name: task}); the body is left as is. Without `--write` it previews.
- `codex` prints one profile per cell as `~/.codex/ht-<tier>-<effort>.config.toml`, plus `review_model` and `plan_mode_reasoning_effort` for `config.toml`.
- `aider` prints `.aider.conf.yml` keys `model`, `weak-model`, `editor-model`, `reasoning-effort`, `test-cmd`, `lint-cmd`.
- `litellm` prints a `config.yaml` with one `model_name` per cell and the other vendors' same-cell models as outage `fallbacks`.
- `opencode` prints `opencode.json` with `model`, `small_model` and `agent.<name>.model`.

Everything except `claude` goes to standard output. Formats were checked against each tool's official docs on 2026-10-28; what could not be verified (the provider prefix in aider model names, whether Codex profile files read `review_model`, where LiteLLM expects `fallbacks`, and so on) is marked in comments inside the output.

### 7. Why Habitree does not build a router

Building a router that picks a model per request was an option. Habitree does not do it.

1. Tools already split work across models: Claude Code subagent `model` and `effort`, Codex profiles, Aider's weak model, opencode's `small_model`. Habitree only needs to generate those settings from one policy.
2. LiteLLM already does routing, fallbacks and budgets. Keeping up with every vendor's API is costly: on 2026-10-28 the LiteLLM repository had 5,704 open issues, most recent ones about per-vendor translation.
3. On broad benchmarks, learned routers did not reliably beat simple baselines (RouterBench; LLMRouterBench, arXiv 2601.07206).
4. Handling API keys adds security burden and conflicts with the standard-library-only rule.
5. Switching models per request tends to lose the cache inside one conversation. Habitree changes cells only at subagent and session boundaries.

### 8. Commands and settings

The command list and a config example are in [section 8](#8-명령과-설정). Task names may drop the `task/` prefix (`explore` means `task/explore`). Without a `models` section in the config file, `habitree check` skips the model checks. Defaults for the other settings (`claude_model`, `deprecation_days`, `price_stale_days`, `tune`, `escalate`) are in `src/habitree/core/config.py`. Check items are listed in [check.md](check.md).
