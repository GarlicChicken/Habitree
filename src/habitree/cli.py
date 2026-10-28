"""Habitree 실행 입구: habitree <명령>. / Entry point: habitree <command>."""
import argparse
import importlib
import sys

from . import __version__
from .commands import COMMANDS
from .core import HabitreeError
from .core import io as hio
from .core.config import Context
from .core.i18n import LANGS, tr

DESC = {"ko": "Habitree: AI와 일하는 습관을 나무처럼 키운다. 피드백은 규칙으로, 반복은 모듈로.",
        "en": "Habitree: grow good habits for AI coding. Feedback becomes rules, repetition becomes modules."}
USAGE_TAIL = {"ko": "명령별 도움말: habitree <명령> -h", "en": "Per-command help: habitree <command> -h"}


def _peek(argv, *names):
    for i, a in enumerate(argv):
        for n in names:
            if a == n and i + 1 < len(argv):
                return argv[i + 1]
            if a.startswith(n + "="):
                return a.split("=", 1)[1]
    return None


def load_command(name):
    return importlib.import_module(f".commands.{name.replace('-', '_')}", __package__)


def build_parser(lang):
    p = argparse.ArgumentParser(prog="habitree", description=tr(DESC, lang), epilog=tr(USAGE_TAIL, lang))
    p.add_argument("--version", action="version", version=f"habitree {__version__}")
    p.add_argument("-C", "--path", help="프로젝트 폴더 / project folder (default: current)")
    p.add_argument("--lang", choices=LANGS, help="출력 언어 / output language")
    sub = p.add_subparsers(dest="command", metavar="<command>")
    mods = {}
    for name in COMMANDS:
        mod = load_command(name)
        sp = sub.add_parser(name, help=tr(mod.SUMMARY, lang), description=tr(mod.SUMMARY, lang))
        mod.add_arguments(sp)
        mods[name] = mod
    return p, mods


def main(argv=None):
    hio.setup_stdio()
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["hook"]:
        # 훅은 빠르고 절대 실패하지 않아야 한다: 다른 명령을 불러오지 않고, 설정이 깨져도 0으로 끝낸다.
        # / Hooks must be fast and never fail: skip loading other commands, exit 0 even on broken config.
        from .commands import hook
        return hook.entry(argv[1:])
    try:
        ctx = Context.load(_peek(argv, "-C", "--path"), _peek(argv, "--lang"))
    except Exception:  # 설정이 깨져도 도움말은 보이게
        ctx = None
    lang = ctx.lang if ctx else "en"
    parser, mods = build_parser(lang)
    args = parser.parse_args(argv)
    if not args.command:
        print(tr(DESC, lang) + "\n")
        for name, mod in mods.items():
            print(f"  {name:<9} {tr(mod.SUMMARY, lang)}")
        print("\n" + tr(USAGE_TAIL, lang))
        return 0
    if ctx is None:
        ctx = Context.load(args.path, args.lang)
    try:
        return mods[args.command].run(args, ctx) or 0
    except HabitreeError as e:
        print(str(e), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
