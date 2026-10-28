# hooks

Habitree를 Claude Code 플러그인으로 설치하면 이 폴더의 `hooks.json`이 훅을 겁니다. 하는 일은 하나입니다. 세션 시작, 요청, 도구 사용 앞뒤, 끝날 때마다 `habitree hook <이벤트>`를 불러서, 같은 일을 맴돌거나 파일에 덧대기만 할 때 그 자리에서 알려 주고, 맡긴 작업은 범위와 경계를 지키게 합니다.

- 마지막 갱신: 2026-10-28

훅은 `habitree` 명령을 부르므로 엔진을 먼저 설치합니다.

```
uv tool install git+https://github.com/GarlicChicken/habitree
claude plugin marketplace add GarlicChicken/habitree
claude plugin install habitree@habitree
```

훅은 셸을 거치지 않는 방식(`command`와 `args`)으로 불러서 bash, zsh, PowerShell 어디서나 같게 돕니다. 프로젝트에 `.habitree/config.json`이 없으면 아무것도 하지 않으니 `habitree init`을 먼저 해 주세요. 훅 안에서 오류가 나도 작업은 막지 않고 `.habitree/state/hook-errors.log`에만 남깁니다. 플러그인 없이 쓰고 싶다면 `habitree init --hooks`가 같은 훅을 프로젝트의 `.claude/settings.json`에 넣어 줍니다.

`hooks.json`의 원본은 [src/habitree/guard/install.py](../src/habitree/guard/install.py)이고, 시험이 둘이 같은지 확인합니다. 무엇을 왜 잡는지는 [docs/spec/guard.md](../docs/spec/guard.md)에 있습니다.

---

## English

When Habitree is installed as a Claude Code plugin, `hooks.json` in this folder wires the hooks. They do one thing: call `habitree hook <event>` at session start, on each prompt, around each tool call and at the end, so that going in circles or patching onto one file is pointed out on the spot, and delegated work keeps its scope and boundaries.

The hooks call the `habitree` command, so install the engine first (see the commands above). They run without a shell (`command` plus `args`), so bash, zsh and PowerShell behave the same. Without `.habitree/config.json` in the project they do nothing, so run `habitree init` first. Errors inside a hook never block the work; they are only written to `.habitree/state/hook-errors.log`. Without the plugin, `habitree init --hooks` adds the same hooks to the project's `.claude/settings.json`.

The source of `hooks.json` is [src/habitree/guard/install.py](../src/habitree/guard/install.py), and a test checks that the two match. What is caught and why is described in [docs/spec/guard.md](../docs/spec/guard.md).
