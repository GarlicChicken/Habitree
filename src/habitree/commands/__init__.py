"""명령 등록부. 명령 하나는 모듈 하나이고 SUMMARY·add_arguments(p)·run(args, ctx)를 둔다.
/ Command registry: one module per command with SUMMARY, add_arguments(p) and run(args, ctx)."""

COMMANDS = ["init", "rules", "check", "export", "hook", "guard", "models", "verify"]
