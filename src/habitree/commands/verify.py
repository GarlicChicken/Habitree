"""verify: 설정 verify의 검증 명령을 셸 없이 차례로 돌린다. 종료 코드 0이 합격. / Run verify commands.

  habitree verify                    등록한 명령 전부
  habitree verify test lint          이름을 골라서
  habitree verify --task task/code   결과를 모델 배분 기록(models record)에도 남긴다
  habitree verify --json

설정 예(언어와 무관, 무엇이든 종료 코드로 판정):
  "verify": {"test": ["pytest", "-q"], "types": ["npx", "tsc", "--noEmit"],
             "go": {"cmd": ["go", "test", "./..."], "timeout": 900}}
종료 코드: 모두 합격 0, 하나라도 불합격 1, 등록한 명령이 없으면 2.
"""
import json
import os
import shutil
import subprocess
import sys
import time

from ..core import HabitreeError
from ..core import io as hio
from ..core.modelpolicy import load_db, normalize_task, policy, record, verify_spec
from ..core.vendors import parse_cell

SUMMARY = {"ko": "검증 명령(테스트·빌드·린트)을 셸 없이 돌리고 결과 요약(종료 코드 0이 합격)",
           "en": "Run verify commands (tests, build, lint) without a shell and summarize (exit 0 passes)"}

DEFAULT_TIMEOUT = 600
TAIL = 5


def add_arguments(p):
    p.add_argument("names", nargs="*", help="돌릴 이름(기본: 전부) / names to run (default: all)")
    p.add_argument("--json", action="store_true", help="결과를 JSON으로 / JSON output")
    p.add_argument("--task", help="결과를 이 작업의 모델 배분 기록에 남김 / record the outcome for this task")
    p.add_argument("--cell", help="--task와 함께: 쓴 칸 tier:effort(기본: 그 작업의 칸) / cell used")


def _exe(cmd):
    """셸 없이 찾는다. Windows의 npm.cmd 같은 것도 실제 경로로. / Resolve the program without a shell."""
    first = cmd[0]
    if os.sep in first or "/" in first:
        return cmd
    found = shutil.which(first)
    return [found] + cmd[1:] if found else cmd


def run_one(ctx, name, cmd, timeout):
    start = time.monotonic()
    status, code, out = "fail", None, b""
    try:
        res = subprocess.run(_exe(cmd), cwd=str(ctx.root), capture_output=True, timeout=timeout or DEFAULT_TIMEOUT)
        code = res.returncode
        out = (res.stdout or b"") + (res.stderr or b"")
        status = "pass" if code == 0 else "fail"
    except subprocess.TimeoutExpired as e:
        status = "timeout"
        out = (e.stdout or b"") + (e.stderr or b"")
    except OSError as e:
        status = "error"
        out = str(e).encode("utf-8", errors="replace")
    tail = [line for line in hio.read_bytes_text(out).strip().splitlines() if line.strip()][-TAIL:]
    return {"name": name, "cmd": cmd, "status": status, "ok": status == "pass", "exit": code,
            "seconds": round(time.monotonic() - start, 2), "tail": tail}


LABEL = {"pass": {"ko": "합격", "en": "pass"}, "fail": {"ko": "불합격", "en": "fail"},
         "timeout": {"ko": "시간 초과", "en": "timeout"}, "error": {"ko": "실행 못 함", "en": "could not run"}}


def run(args, ctx):
    ko = ctx.lang == "ko"
    cfg = ctx.get("verify") or {}
    if not cfg:
        print("등록한 검증 명령이 없습니다. 설정 verify에 {\"test\": [\"pytest\", \"-q\"]}처럼 더하세요." if ko else
              "No verify commands. Add some under verify in the config, e.g. {\"test\": [\"pytest\", \"-q\"]}.",
              file=sys.stderr)
        return 2
    names = args.names or list(cfg)
    unknown = [n for n in names if n not in cfg]
    if unknown:
        raise HabitreeError((f"없는 검증 이름: {', '.join(unknown)} (있는 것: {', '.join(cfg)})" if ko else
                             f"Unknown verify names: {', '.join(unknown)} (available: {', '.join(cfg)})"))
    specs = [(n, *verify_spec(cfg[n])) for n in names]
    task = cell = None
    if args.task:  # 돌리기 전에 작업 이름부터 확인한다
        db = load_db(ctx)
        task = normalize_task(db, args.task, ctx.lang)
        cell = parse_cell(args.cell, ctx.lang) if args.cell else policy(db, task)["cell"]
    results = [run_one(ctx, n, cmd, timeout) for n, cmd, timeout in specs]
    passed = sum(1 for r in results if r["ok"])
    failed = len(results) - passed
    event = None
    skipped_record = False
    if task:
        if any(r["status"] == "error" for r in results):
            skipped_record = True  # 도구가 없어서 못 돌린 것은 모델 품질이 아니다
        else:
            bad = [r["name"] for r in results if not r["ok"]]
            event = record(ctx, task, "quality_fail" if bad else "pass", cell,
                           note=("verify: " + ", ".join(bad)) if bad else "", source="verify")
    if args.json:
        print(json.dumps({"ok": failed == 0, "passed": passed, "failed": failed, "results": results,
                          "recorded": event}, ensure_ascii=False, indent=1))
        return 0 if failed == 0 else 1
    print(("검증" if ko else "Verify") + f": {ctx.root}")
    for r in results:
        label = LABEL[r["status"]]["ko" if ko else "en"]
        extra = f" · {'종료 코드' if ko else 'exit'} {r['exit']}" if r["status"] == "fail" else ""
        print(f"  [{label}] {r['name']}  {r['seconds']}{'초' if ko else 's'}{extra}  ({' '.join(r['cmd'])})")
        if not r["ok"]:
            for line in r["tail"]:
                print(f"      {line}")
    print(("\n  합격 {p} · 불합격 {f}" if ko else "\n  passed {p} · failed {f}").format(p=passed, f=failed))
    if event:
        print(("  기록: " if ko else "  recorded: ") + f"{task} {event['result']} ({event['cell']})")
    if skipped_record:
        print("  실행하지 못한 명령이 있어 모델 배분 기록은 남기지 않았습니다(모델 품질 문제가 아님)." if ko else
              "  Some commands could not start, so no model outcome was recorded (not a model quality issue).")
    return 0 if failed == 0 else 1
