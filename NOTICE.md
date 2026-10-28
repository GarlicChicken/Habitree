# 출처와 감사

Habitree를 만들기 전에 비슷한 일을 하는 오픈소스와 자료를 꽤 오래 살펴봤습니다. 좋은 생각이 많았고, 그중 일부를 빌려 왔습니다. 무엇을 어디서 배웠는지 여기에 적어 둡니다. 코드나 데이터를 그대로 옮기게 되면 원래 라이선스 고지도 함께 둡니다.

## 옮겨 온 코드와 데이터

아직 없습니다. 모델 대응표(`src/habitree/data/vendors.json`)의 값은 각 회사의 공식 가격·모델·단종 문서를 직접 읽고 적었고, 항목마다 출처와 확인일을 남겼습니다.

## 빌려 온 생각

| 생각 | 출처 |
|---|---|
| 도구가 만든 구역과 사람이 쓴 부분을 나누고, 해시로 사람이 고친 것을 알아보기 | [ruler](https://github.com/intellectronica/ruler), [spec-kit](https://github.com/github/spec-kit), [claude-reflect](https://github.com/BayramAnnakov/claude-reflect) |
| 피드백을 같은 뜻끼리 묶고, 여러 번 나온 것부터 다루기 | [claude-reflect](https://github.com/BayramAnnakov/claude-reflect) |
| 규칙을 언제 올리고 언제 버릴지에 대한 판단 | [BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD), [Compound Engineering](https://github.com/EveryInc/compound-engineering-plugin) |
| '쓸모없었다'는 반응의 비율로 경고 기준을 조정하기 | Sadowski et al., "Tricorder: Building a Program Analysis Ecosystem", ICSE 2015 |
| 지침 파일 크기, `@import`, 숨은 유니코드 점검 | [agnix](https://github.com/agent-sh/agnix), [lychee](https://github.com/lycheeverse/lychee), [AGENTS.md](https://agents.md) |
| 명세, 적합성 시험, 참조 구현으로 여러 구현을 맞추기 | [EditorConfig](https://editorconfig.org), [CommonMark](https://commonmark.org) |
| 여러 도구가 함께 읽는 AGENTS.md와 그것을 불러오는 얇은 CLAUDE.md | [AGENTS.md](https://agents.md), [Claude Code 문서](https://code.claude.com/docs) |
| 등급과 강도를 한 칸으로 보고, 모델을 바꾸기 전에 강도부터 조정하고, 완료된 작업당 비용으로 비교하기 | Anthropic [Optimizing for cost and intelligence](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence), [Effort](https://platform.claude.com/docs/en/build-with-claude/effort), [Choosing a Claude model and effort level in Claude Code](https://claude.com/resources/articles/claude-model-and-effort-level-in-claude-code) |
| 장애 때의 대체를 품질 실패와 따로 다루기, 관측 10번 전에는 조정하지 않기 | [LiteLLM](https://github.com/BerriAI/litellm) |
| 가벼운 모델을 먼저 쓰고 안 되면 주 모델로, 언어별 검증 명령 | [Aider](https://github.com/Aider-AI/aider) |
| 판정이 자주 틀리면 단계식 승격이 오히려 나빠진다는 점, 학습형 라우터를 만들지 않은 근거 | RouterBench (arXiv 2403.12031), LLMRouterBench (arXiv 2601.07206) |

---

## English

Before building Habitree we spent a good while studying open-source projects and research doing similar things. There were many good ideas, and we borrowed some of them. This page records what we learned and from where. If we ever copy code or data, its original license notice will be included here.

### Copied code and data

None yet. The values in the model vendor table (`src/habitree/data/vendors.json`) were read directly from each vendor's official pricing, model and deprecation pages, and every entry keeps its source and checked date.

### Borrowed ideas

| Idea | Source |
|---|---|
| Separating tool-generated blocks from human text, and using hashes to notice human edits | ruler, spec-kit, claude-reflect |
| Grouping feedback by meaning and handling repeated items first | claude-reflect |
| Judging when to promote or drop a rule | BMAD-METHOD, Compound Engineering |
| Tuning warning thresholds by the rate of "not useful" reactions | Sadowski et al., "Tricorder", ICSE 2015 |
| Checking instruction size, `@import` targets and hidden Unicode | agnix, lychee, AGENTS.md |
| Keeping implementations aligned with a spec, a conformance suite and a reference implementation | EditorConfig, CommonMark |
| AGENTS.md as the file every tool reads, with a thin CLAUDE.md that imports it | AGENTS.md, Claude Code docs |
| Treating tier and effort as one cell, adjusting effort before switching models, comparing cost per completed task | Anthropic docs and articles |
| Handling outage fallbacks apart from quality failures; no tuning before 10 observations | LiteLLM |
| Trying a lighter model first and falling back to the main one; per-language verify commands | Aider |
| Why stepwise escalation suffers when judgments are often wrong, and why we built no learned router | RouterBench, LLMRouterBench |

Links are in the Korean table above.
