# 출처와 감사

Habitree를 만들기 전에 비슷한 일을 하는 오픈소스와 자료를 꽤 오래 살펴봤습니다. 좋은 생각이 많았고, 그중 일부를 빌려 왔습니다. 무엇을 어디서 배웠는지 여기에 적어 둡니다. 코드나 데이터를 그대로 옮기게 되면 원래 라이선스 고지도 함께 둡니다.

## 옮겨 온 코드와 데이터

옮겨 온 코드는 아직 없고, 데이터 하나를 옮겼습니다.

**scc 언어표.** `habitree map`이 파일의 언어를 판정하고 줄 수를 셀 때 쓰는 [src/habitree/data/languages.json](src/habitree/data/languages.json)은 [boyter/scc](https://github.com/boyter/scc)의 `languages.json`(커밋 `27c14c46b3d33599fb96ca5f946781db9530df51`, 2026-10-28 확인)에서 왔습니다. 언어 375개의 확장자, 파일 이름, shebang, 줄 주석과 여러 줄 주석 표시만 남기고 칸 이름을 줄였습니다. 여러 언어가 함께 쓰던 확장자 12개는 한 언어에만 두었습니다(`_source.shared_ext`). 라이선스는 MIT이고 원문 고지는 아래와 같습니다.

```
MIT License

Copyright (c) 2021 Ben Boyter

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice (including the next paragraph) shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

모델 대응표(`src/habitree/data/vendors.json`)의 값은 각 회사의 공식 가격·모델·단종 문서를 직접 읽고 적었고, 항목마다 출처와 확인일을 남겼습니다.

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
| 참조 그래프와 PageRank로 순위를 매기고 글자 예산 안에서 이진 탐색으로 코드 지도 만들기(코드는 옮기지 않고 새로 씀) | [Aider](https://github.com/Aider-AI/aider) repo map |
| 심볼 기록(이름, 종류, 줄, 시그니처, 설명)과 몸통 해시, 이름 정규화, 목록을 먼저 보이고 몸통은 나중에 | [token-savior](https://github.com/Mibayy/token-savior), [code-index-mcp](https://github.com/johnhuang316/code-index-mcp), [kit](https://github.com/cased/kit) |
| 수정 시각과 크기로 거르고 sha256으로 확정하는 증분 색인 | [codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp), [claude-context](https://github.com/zilliztech/claude-context) |
| 문법을 몰라도 창 단위로 찾는 글 중복 | [jscpd](https://github.com/kucherenko/jscpd) |
| 비밀 파일은 이름만 보고 먼저 빼기 | [Repomix](https://github.com/yamadashy/repomix) |
| '없다'와 '못 읽었다'를 나누고, 빈 결과 대신 다음에 할 일을 알려 주기 | [llm-context.py](https://github.com/cyberchitta/llm-context.py), [jCodeMunch-MCP](https://github.com/jgravelle/jcodemunch-mcp)(공개 설명만 참고) |
| 코드가 바뀌면 그 코드를 설명한 글을 낡았을 수 있다고 알리기 | [code-graph-rag](https://github.com/vitali87/code-graph-rag), [contextful](https://github.com/Inferensys/contextful) |
| 표준 입출력 MCP 서버, 도구는 몇 개만 | [MCP 명세](https://modelcontextprotocol.io/specification) |
| 세션 기록에서 응답 하나를 한 번만 세기(`message.id`·`requestId` 묶음), 도구 호출은 `tool_use.id` 단위 | [ccusage](https://github.com/ccusage/ccusage), [tokscale](https://github.com/junhoyeo/tokscale), [Harbor](https://github.com/harbor-framework/harbor) |
| 큰 결과 × 남은 요청 수로 다시 청구되는 비용 매기기 | [claude-context-optimizer](https://github.com/egorfedorov/claude-context-optimizer), [tokenwise](https://github.com/lohani-mohit/tokenwise), [cctx](https://github.com/jacquardlabs/cctx) |
| 낭비 유형마다 고정 처방을 두고 규칙 후보로 잇기 | [cctx](https://github.com/jacquardlabs/cctx) |
| 짧은 사용자 응답과 정정 표지로 정정을 찾기 | [agentsview](https://github.com/kenn-io/agentsview) |
| 모르는 기록 형식은 세어 알리고, 실제 형식을 본뜬 픽스처로 회귀를 막기 | [claude-code-log](https://github.com/daaain/claude-code-log), [agent-sessions](https://github.com/jazzyalex/agent-sessions) |
| 같은 호출 3번, 같은 오류 3번을 막힘의 기준으로 | [Cline](https://github.com/cline/cline), [OpenHands](https://github.com/All-Hands-AI/OpenHands), [Gemini CLI](https://github.com/google-gemini/gemini-cli) |
| 두 갈래를 기본 3번씩 돌려 평균과 표준편차로 비교 | [claude plugin eval](https://code.claude.com/docs/en/plugin-evals.md), [skill-creator](https://github.com/anthropics/skills/tree/main/skills/skill-creator) |
| 채점을 작업 폴더 밖에 두고, 아예 돌지 못한 실행은 통과로 세지 않기 | [Aider 벤치마크](https://github.com/Aider-AI/aider/tree/main/benchmark), [SWE-bench](https://github.com/SWE-bench/SWE-bench) |

---

## English

Before building Habitree we spent a good while studying open-source projects and research doing similar things. There were many good ideas, and we borrowed some of them. This page records what we learned and from where. If we ever copy code or data, its original license notice will be included here.

### Copied code and data

No code has been copied yet; one data file has. The language table used by `habitree map` ([src/habitree/data/languages.json](src/habitree/data/languages.json)) comes from the `languages.json` of [boyter/scc](https://github.com/boyter/scc) (commit `27c14c46b3d33599fb96ca5f946781db9530df51`, checked 2026-10-28). Only extensions, file names, shebangs and comment markers for 375 languages were kept, with shorter field names, and the 12 extensions shared by several languages were each given to one language (`_source.shared_ext`). It is MIT licensed; the original notice is reproduced in the Korean section above.

The values in the model vendor table (`src/habitree/data/vendors.json`) were read directly from each vendor's official pricing, model and deprecation pages, and every entry keeps its source and checked date.

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
| A code map ranked by a reference graph and PageRank, fitted to a character budget by binary search (rewritten, no code copied) | Aider |
| Symbol records with body hashes, name normalization, lists first and bodies on request | token-savior, code-index-mcp, kit |
| Incremental indexing filtered by mtime and size, confirmed by sha256 | codebase-memory-mcp, claude-context |
| Grammar-free windowed duplicate detection | jscpd |
| Leaving secret files out by name first | Repomix |
| Telling "not there" from "could not read", and giving next steps instead of empty results | llm-context.py, jCodeMunch-MCP |
| Flagging descriptions as possibly stale when the code they describe changes | code-graph-rag, contextful |
| A stdio MCP server with only a few tools | MCP specification |
| Counting each response once in transcripts (`message.id` and `requestId`), tool calls by `tool_use.id` | ccusage, tokscale, Harbor |
| Pricing large results by the number of later requests that bill them again | claude-context-optimizer, tokenwise, cctx |
| A fixed prescription per waste type, linked to rule candidates | cctx |
| Finding corrections from short replies with correction markers | agentsview |
| Counting unknown record types and guarding the format with realistic fixtures | claude-code-log, agent-sessions |
| Three identical calls or three identical errors as the sign of being stuck | Cline, OpenHands, Gemini CLI |
| Two arms, three runs each by default, compared by mean and standard deviation | claude plugin eval, skill-creator |
| Graders outside the work folder; runs that never started are not passes | Aider benchmark, SWE-bench |

Links are in the Korean table above.
