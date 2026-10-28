"""bench: 같은 과제를 규칙을 켠 갈래(with)와 끈 갈래(without)로 여러 번 돌려 비교한다. 부를 때만 돈다.
/ Run one task with Habitree rules on and off, several times each, and compare.

  habitree bench run <과제> [--arms with,without] [--reps 3] [--runner claude|fake] [--model M]
                     [--isolation none|bare|config-dir] [--max-budget-usd 2] [--out 폴더] [--dry-run] [--yes]
  habitree bench report <결과 폴더> [--json]

과제 폴더: <과제>/task.json(prompt, verify 명령 배열, timeout, description, rules) + <과제>/project/(시작 상태).
실행마다 project/를 시스템 임시 폴더로 복사한다(이 리포 안에서 돌리면 위 폴더의 CLAUDE.md가 섞인다).
with 갈래에만 habitree init과 과제의 rules를 넣고 지침 파일을 만든다. 실행기는 셸 없이 인자 배열로 부른다.
verify 명령이 모두 종료 코드 0이면 합격. 결과는 bench/results/<UTC 날짜>-<과제>/(커밋하지 않음).
claude 실행기는 실제 사용량이 들어 --yes가 있어야 돈다. 자세히: docs/spec/bench.md
"""
import hashlib
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

from .. import __version__
from ..core import HabitreeError
from ..core import io as hio
from ..core.config import DEFAULTS, Context, deep_merge
from ..core.i18n import tr
from ..core.paths import git
from ..core.ruledb import RuleDB
from ..core.timeutil import now_iso, now_utc
from . import export, init
from .verify import run_one

SUMMARY = {"ko": "같은 과제를 규칙 켬·끔으로 여러 번 돌려 토큰·비용·시간·합격률 비교",
           "en": "Run a task with rules on and off several times; compare tokens, cost, time and pass rate"}
METRICS = ("tokens", "input", "output", "cache_read", "cache_write", "cost_usd", "seconds", "turns")
FAKE = {"type": "result", "subtype": "success", "is_error": False, "num_turns": 1, "duration_ms": 0,
        "total_cost_usd": 0.0, "usage": {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0,
                                         "cache_creation_input_tokens": 0}, "modelUsage": {}, "result": "fake"}


def add_arguments(p):
    sub = p.add_subparsers(dest="action", metavar="<action>")
    r = sub.add_parser("run", help="과제를 돌림 / run a task")
    r.add_argument("task", help="과제 폴더 또는 bench/ 아래 이름 / task folder or name under bench/")
    r.add_argument("--arms", default="with,without", help="갈래(with, without) / arms")
    r.add_argument("--reps", type=int, default=3, help="갈래마다 반복 수(기본 3) / repetitions per arm")
    r.add_argument("--runner", choices=("claude", "fake"), default="claude")
    r.add_argument("--model", help="claude --model 값 / model for claude")
    r.add_argument("--isolation", choices=("none", "bare", "config-dir"), default="none",
                   help="사용자 설정을 얼마나 떼어 낼지 / how much user config to keep out")
    r.add_argument("--max-budget-usd", type=float, help="실행 하나의 비용 한도(claude) / cost cap per run")
    r.add_argument("--out", help="결과 폴더 / results folder")
    r.add_argument("--dry-run", action="store_true", help="계획만 보기 / show the plan only")
    r.add_argument("--yes", action="store_true", help="claude 실행기를 실제로 돌림(사용량이 듦) / really run claude")
    rp = sub.add_parser("report", help="결과 요약 / summarize results")
    rp.add_argument("results", help="결과 폴더 / results folder")
    rp.add_argument("--json", action="store_true")


# ── 과제 · Task ──

def load_task(ctx, name):
    d = Path(name)
    if not (d / "task.json").is_file():
        d = ctx.root / "bench" / name
    if not (d / "task.json").is_file() or not (d / "project").is_dir():
        raise HabitreeError(f"과제가 아닙니다(task.json과 project/가 필요) / not a task folder: {name}")
    task = hio.load_json(d / "task.json")
    verify = task.get("verify")
    if not task.get("prompt") or not isinstance(verify, list) or not verify or \
            not all(isinstance(v, list) and v and all(isinstance(x, str) for x in v) for v in verify):
        raise HabitreeError(f"task.json에는 prompt와 verify(명령 배열의 목록)가 있어야 합니다 / bad task.json: {d}")
    task.setdefault("name", d.name)
    return d.resolve(), task


def task_hash(task_dir):
    h = hashlib.sha256()
    for p in sorted(x for x in task_dir.rglob("*") if x.is_file() and "__pycache__" not in x.parts):
        h.update(p.relative_to(task_dir).as_posix().encode("utf-8") + b"\0" + p.read_bytes())
    return h.hexdigest()[:16]


def _sub(arg, task_dir):
    return arg.replace("{python}", sys.executable).replace("{task}", str(task_dir))


def setup_with(workdir, task, lang):
    """with 갈래: habitree init + 과제 규칙 + 지침 파일. / Install Habitree and the task's rules."""
    import contextlib
    import io
    ctx = Context(workdir, deep_merge(DEFAULTS, {}), lang)
    args = Namespace(init_lang=lang, packs=None, no_readme=False, force=False, dry_run=False, hooks=False)
    with contextlib.redirect_stdout(io.StringIO()):
        init.run(args, ctx)
        ctx = Context.load(workdir, lang)
        db = RuleDB.load(ctx.p(ctx.get("rules.db")), lang)
        for r in task.get("rules", []):
            db.add(r["scope"], r["aspect"], r["rule"], r["why"], "bench", level=r.get("level", "must"))
        db.save(ctx.p(ctx.get("rules.doc")), lang)
        export.apply(ctx, export.plan(ctx, db))
    return sorted(p.relative_to(workdir).as_posix() for p in workdir.rglob("*") if p.is_file() and
                  (p.name in ("AGENTS.md", "CLAUDE.md") or ".habitree" in p.parts))


# ── 실행기 · Runners ──

def claude_command(task, arm, workdir, args, run_dir):
    """claude -p 인자 배열과 환경. / argv and environment for claude -p."""
    exe = shutil.which("claude") or "claude"
    prompt = tr(task["prompt"], task.get("lang", "ko"))
    if exe.lower().endswith((".cmd", ".bat")) and any(ch in prompt for ch in '%^&|<>"'):
        # npm 설치의 claude.cmd는 인자가 cmd.exe를 거친다. 네이티브 설치(claude.exe)를 쓰거나 이 글자를 뺀다.
        raise HabitreeError("prompt has % ^ & | < > \" and claude is a .cmd shim; use the native claude.exe")
    argv = [exe, "-p", prompt, "--output-format", "json",
            "--permission-mode", task.get("permission_mode", "acceptEdits")]
    if task.get("allowed_tools"):
        argv += ["--allowedTools", ",".join(task["allowed_tools"])]
    if task.get("max_turns"):
        argv += ["--max-turns", str(task["max_turns"])]
    if args.model:
        argv += ["--model", args.model]
    if args.max_budget_usd:
        argv += ["--max-budget-usd", str(args.max_budget_usd)]
    env = dict(os.environ)
    if args.isolation == "bare":
        argv.append("--bare")  # CLAUDE.md도 건너뛰므로 with 갈래는 지침을 시스템 프롬프트에 덧붙인다
        if arm == "with":
            argv += ["--append-system-prompt-file", str(Path(workdir) / "AGENTS.md")]
    elif args.isolation == "config-dir":
        env["CLAUDE_CONFIG_DIR"] = str(Path(run_dir) / "claude-home")
    return argv, env


def run_runner(task_dir, task, arm, rep, workdir, args, run_dir):
    start = time.monotonic()
    if args.runner == "fake":
        spec = (task.get("fake") or {}).get(arm) or {}
        if spec.get("files"):
            shutil.copytree(str(task_dir / spec["files"]), str(workdir), dirs_exist_ok=True)
        outs = spec.get("outputs") or [FAKE]
        out = dict(outs[(rep - 1) % len(outs)])
        out.setdefault("session_id", f"fake-{arm}-{rep}")
        return {"exit": 0, "stdout": json.dumps(out), "stderr": "", "seconds": 0.0, "status": "ok"}
    argv, env = claude_command(task, arm, workdir, args, run_dir)
    try:
        r = subprocess.run(argv, cwd=str(workdir), env=env, capture_output=True, timeout=task.get("timeout", 900))
        status, code, out, err = "ok", r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired as e:
        status, code, out, err = "timeout", None, e.stdout or b"", e.stderr or b""
    except OSError as e:
        status, code, out, err = "error", None, b"", str(e).encode("utf-8")
    return {"exit": code, "stdout": hio.read_bytes_text(out or b""), "stderr": hio.read_bytes_text(err or b""),
            "seconds": round(time.monotonic() - start, 2), "status": status}


def parse_result(text):
    """--output-format json 결과(SDKResultMessage)를 방어적으로 읽는다. 토큰은 서브에이전트까지 든 modelUsage를
    먼저 쓰고, 없으면 usage. / Parse the result message defensively; prefer modelUsage for tokens."""
    obj = None
    try:
        obj = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        for line in reversed((text or "").splitlines()):  # stream-json이면 마지막 result 줄
            try:
                cand = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(cand, dict) and cand.get("type") == "result":
                obj = cand
                break
    if isinstance(obj, list):
        obj = next((x for x in reversed(obj) if isinstance(x, dict) and x.get("type") == "result"), None)
    if not isinstance(obj, dict):
        return {"parsed": False}

    def num(v):
        return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None
    m = {"parsed": True, "cost_usd": num(obj.get("total_cost_usd")), "turns": num(obj.get("num_turns")),
         "duration_ms": num(obj.get("duration_ms")), "is_error": obj.get("is_error"), "subtype": obj.get("subtype"),
         "session_id": obj.get("session_id")}
    mu = obj.get("modelUsage") if isinstance(obj.get("modelUsage"), dict) else {}
    usage = obj.get("usage") if isinstance(obj.get("usage"), dict) else {}
    pairs = (("input", "inputTokens", "input_tokens"), ("output", "outputTokens", "output_tokens"),
             ("cache_read", "cacheReadInputTokens", "cache_read_input_tokens"),
             ("cache_write", "cacheCreationInputTokens", "cache_creation_input_tokens"))
    if mu:
        m["token_source"] = "modelUsage"
        for k, camel, _ in pairs:
            m[k] = sum(num(v.get(camel)) or 0 for v in mu.values() if isinstance(v, dict))
        m["models"] = sorted(mu)
    else:
        m["token_source"] = "usage" if usage else None
        for k, _, snake in pairs:
            m[k] = num(usage.get(snake))
    known = [m[k] for k, _, _ in pairs if m[k] is not None]
    m["tokens"] = sum(known) if known else None
    m["missing"] = [k for k in ("total_cost_usd", "num_turns", "session_id") if obj.get(k) is None]
    return m


def recount(session_id, workdir, claude_dir=None):
    """세션 기록으로 토큰을 다시 센다(audit와 같은 중복 제거). 없으면 None. / Recount from the transcript."""
    from ..sessions import claude
    folder = claude.transcript_dir(session_id, workdir, claude_dir)
    if folder is None:
        return None
    ses = claude.scan(str(workdir), folders=[folder]).sessions.get(session_id)
    if ses is None:
        return None
    t = {"requests": len(ses.requests), "tool_calls": len(ses.calls), "input": 0, "output": 0, "cache_read": 0,
         "cache_write": 0}
    for r in ses.requests.values():
        for k, v in r.tokens().items():
            t["cache_write" if k.startswith("cache_write") else k] += v
    return t


# ── run ──

def _out_dir(ctx, task, args):
    if args.out:
        return Path(args.out)
    base = ctx.root / "bench" / "results" / f"{now_utc().strftime('%Y-%m-%d')}-{task['name']}"
    out, n = base, 2
    while out.exists():
        out, n = Path(f"{base}-{n}"), n + 1
    return out


def _meta(ctx, task_dir, task, args, arms):
    meta = {"task": task["name"], "task_hash": task_hash(task_dir), "description": task.get("description"),
            "arms": arms, "reps": args.reps, "runner": args.runner, "model": args.model,
            "isolation": args.isolation, "max_budget_usd": args.max_budget_usd, "habitree": __version__,
            "python": platform.python_version(), "os": platform.system(), "created_at": now_iso(),
            "order": "interleaved"}
    head = git(ctx.root, "rev-parse", "HEAD")
    if head:
        dirty = git(ctx.root, "status", "--porcelain")
        meta["commit"] = head.decode().strip()[:12] + ("-dirty" if dirty and dirty.strip() else "")
    if args.runner == "claude" and not args.dry_run:
        exe = shutil.which("claude")
        try:
            meta["claude_version"] = subprocess.run([exe, "--version"], capture_output=True, timeout=30
                                                    ).stdout.decode("utf-8", "replace").strip() if exe else None
        except (OSError, subprocess.SubprocessError):
            meta["claude_version"] = None
        user_md = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude") / "CLAUDE.md"
        if args.isolation == "none" and user_md.is_file():  # 내용 대신 해시만: 두 갈래가 같은 것을 읽었다는 표시
            meta["user_claude_md_sha256"] = hashlib.sha256(user_md.read_bytes()).hexdigest()[:16]
    return meta


def run_bench(ctx, args):
    ko = ctx.lang == "ko"
    task_dir, task = load_task(ctx, args.task)
    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    if not arms or any(a not in ("with", "without") for a in arms) or args.reps < 1:
        raise HabitreeError("--arms는 with,without 중에서, --reps는 1 이상 / --arms from with,without; --reps >= 1")
    plan = [(rep, arm) for rep in range(1, args.reps + 1) for arm in arms]
    out = _out_dir(ctx, task, args)
    print((f"bench: {task['name']} · 실행기 {args.runner} · 갈래 {', '.join(arms)} × {args.reps}번 = {len(plan)}번 · "
           f"격리 {args.isolation}" if ko else f"bench: {task['name']} · runner {args.runner} · arms "
           f"{', '.join(arms)} × {args.reps} = {len(plan)} runs · isolation {args.isolation}"))
    if args.runner == "claude":
        budget = (f"최대 약 ${args.max_budget_usd * len(plan):.2f}(실행당 한도 × 실행 수)" if ko else
                  f"at most about ${args.max_budget_usd * len(plan):.2f} (cap × runs)") if args.max_budget_usd else \
            ("한도 없음(--max-budget-usd 권장)" if ko else "no cap (consider --max-budget-usd)")
        print(("  사용량: " if ko else "  usage: ") + budget)
        if args.isolation == "none":
            print("  " + ("격리 none: 사용자 전역 설정·CLAUDE.md가 두 갈래 모두에 들어간다." if ko else
                          "isolation none: your global settings and CLAUDE.md load in both arms."))
    if args.dry_run:
        for arm in arms:
            argv = claude_command(task, arm, "<work>", args, "<run>")[0] if args.runner == "claude" else ["(fake)"]
            print(f"  [{arm}] " + " ".join(a if len(a) < 60 else a[:57] + "..." for a in argv))
        for v in task["verify"]:
            print("  verify: " + " ".join(_sub(a, task_dir) for a in v))
        print(("  결과 폴더: " if ko else "  results: ") + str(out) + (" (만들지 않음)" if ko else " (not created)"))
        return 0
    if args.runner == "claude" and not args.yes:
        raise HabitreeError("claude 실행기는 실제 사용량이 듭니다. 계획은 --dry-run, 실제로 돌리려면 --yes."
                            if ko else "The claude runner uses real usage. See --dry-run; add --yes to run.")
    (out / "runs").mkdir(parents=True, exist_ok=True)
    hio.save_json(out / "plan.json", _meta(ctx, task_dir, task, args, arms))
    for rep, arm in plan:
        run_dir = out / "runs" / f"{arm}-{rep}"
        run_dir.mkdir(parents=True, exist_ok=True)
        tmp = Path(tempfile.mkdtemp(prefix="habitree-bench-"))
        work = tmp / "project"
        try:
            shutil.copytree(str(task_dir / "project"), str(work))
            setup = setup_with(work, task, task.get("lang", "ko")) if arm == "with" else []
            res = run_runner(task_dir, task, arm, rep, work, args, run_dir)
            hio.write_text(run_dir / "runner.out", res["stdout"])
            if res["stderr"]:
                hio.write_text(run_dir / "runner.err", res["stderr"])
            m = parse_result(res["stdout"])
            m["seconds"] = res["seconds"] if m.get("duration_ms") is None else round(m["duration_ms"] / 1000, 2)
            checks = [run_one(SimpleNamespace(root=work), f"v{i + 1}", [_sub(a, task_dir) for a in v],
                              task.get("verify_timeout", 300)) for i, v in enumerate(task["verify"])]
            if res["status"] == "error" or any(c["status"] == "error" for c in checks):
                status = "not_scored"
            else:
                status = "pass" if all(c["ok"] for c in checks) else "fail"
            rec = {"arm": arm, "rep": rep, "at": now_iso(), "runner": args.runner, "runner_status": res["status"],
                   "exit": res["exit"], "status": status, "metrics": m, "setup": setup,
                   "verify": [{k: c[k] for k in ("name", "status", "exit", "seconds", "tail")} for c in checks]}
            if args.runner == "claude" and m.get("session_id"):
                cdir = run_dir / "claude-home" if args.isolation == "config-dir" else None
                rec["recount"] = recount(m["session_id"], work, cdir)
            hio.save_json(run_dir / "run.json", rec)
            print(f"  {arm}-{rep}: {status} · " + (f"토큰 {m.get('tokens')} · ${m.get('cost_usd')}" if ko else
                                                    f"tokens {m.get('tokens')} · ${m.get('cost_usd')}"))
        finally:
            shutil.rmtree(str(tmp), ignore_errors=True)
    data = report(out)
    print()
    print(markdown(data, ctx.lang))
    return 0


# ── report ──

def _stats(vals):
    vals = [v for v in vals if isinstance(v, (int, float))]
    if not vals:
        return {"n": 0, "mean": None, "sd": None}
    return {"n": len(vals), "mean": round(statistics.mean(vals), 4),
            "sd": round(statistics.stdev(vals), 4) if len(vals) > 1 else None}


def report(out):
    out = Path(out)
    runs = [hio.load_json(p) for p in sorted(out.glob("runs/*/run.json"))]
    if not runs:
        raise HabitreeError(f"실행 기록이 없습니다 / no runs in: {out}")
    meta = hio.load_json(out / "plan.json", {}) or {}
    arms = {}
    for arm in [a for a in meta.get("arms", []) if a in {r["arm"] for r in runs}] or sorted({r["arm"] for r in runs}):
        rs = [r for r in runs if r["arm"] == arm]
        scored = [r for r in rs if r["status"] in ("pass", "fail")]
        passed = sum(1 for r in scored if r["status"] == "pass")
        a = {"runs": len(rs), "scored": len(scored), "passed": passed,
             "pass_rate": round(passed / len(scored), 4) if scored else None,
             "metrics": {k: _stats([r["metrics"].get(k) for r in scored]) for k in METRICS}}
        cost = a["metrics"]["cost_usd"]
        a["cost_per_pass"] = round(cost["mean"] * cost["n"] / passed, 4) if passed and cost["n"] else None
        arms[arm] = a
    warn = []
    w, wo = arms.get("with"), arms.get("without")
    delta = {}
    if w and wo:
        for k in METRICS:
            x, y = w["metrics"][k]["mean"], wo["metrics"][k]["mean"]
            delta[k] = round((x - y) / y, 4) if x is not None and y else None
        if w["pass_rate"] is not None and wo["pass_rate"] is not None:
            delta["pass_rate_points"] = round(w["pass_rate"] - wo["pass_rate"], 4)
            if (delta.get("tokens") or 0) < 0 and delta["pass_rate_points"] < 0:
                warn.append("fewer_tokens_lower_pass")
    if any(a["scored"] < 3 for a in arms.values()):
        warn.append("few_runs")
    if any(r["status"] == "not_scored" for r in runs):
        warn.append("not_scored")
    if meta.get("isolation") == "none" and meta.get("runner") == "claude":
        warn.append("not_isolated")
    if any(r["metrics"].get("cost_usd") is None for r in runs if r["status"] != "not_scored"):
        warn.append("cost_missing")
    data = {"task": meta.get("task"), "meta": meta, "arms": arms, "delta": delta, "warnings": warn,
            "generated_at": now_iso()}
    hio.save_json(out / "report.json", data)
    hio.write_text(out / "report.md", markdown(data, "ko") + "\n\n---\n\n" + markdown(data, "en") + "\n")
    return data


WARN = {"fewer_tokens_lower_pass": {"ko": "토큰은 줄었지만 합격률도 떨어졌다. 아낀 것이 아니라 덜 한 것일 수 있다.",
                                    "en": "Tokens went down but so did the pass rate: this may be doing less, not saving."},
        "few_runs": {"ko": "채점된 실행이 갈래마다 3번보다 적어 편차를 믿기 어렵다.",
                     "en": "Fewer than 3 scored runs per arm; the spread is not reliable."},
        "not_scored": {"ko": "실행기나 검증 명령을 돌리지 못한 실행은 채점에서 뺐다.",
                       "en": "Runs where the runner or a verify command could not start were not scored."},
        "not_isolated": {"ko": "격리 none: 사용자 전역 설정과 CLAUDE.md가 두 갈래 모두에 들어갔다.",
                         "en": "Isolation none: global settings and CLAUDE.md were loaded in both arms."},
        "cost_missing": {"ko": "비용을 받지 못한 실행이 있다.", "en": "Some runs reported no cost."}}


def _ms(s, digits=0):
    if s["mean"] is None:
        return "-"
    fmt = f"{{:,.{digits}f}}"
    return fmt.format(s["mean"]) + (f" ± {fmt.format(s['sd'])}" if s["sd"] is not None else "")


def markdown(data, lang):
    ko, meta = lang == "ko", data["meta"]
    head = ["갈래", "실행", "합격률", "토큰", "비용(USD)", "합격당 비용", "시간(초)", "턴"] if ko else \
        ["Arm", "Runs", "Pass rate", "Tokens", "Cost (USD)", "Cost per pass", "Time (s)", "Turns"]
    lines = [f"# bench: {data['task']}", "",
             (f"- 실행기 {meta.get('runner')} · 반복 {meta.get('reps')} · 격리 {meta.get('isolation')} · "
              f"과제 해시 {meta.get('task_hash')} · {meta.get('created_at')} (UTC)") if ko else
             (f"- runner {meta.get('runner')} · reps {meta.get('reps')} · isolation {meta.get('isolation')} · "
              f"task hash {meta.get('task_hash')} · {meta.get('created_at')} (UTC)"), "",
             "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for arm, a in data["arms"].items():
        m = a["metrics"]
        rate = "-" if a["pass_rate"] is None else f"{a['pass_rate']:.0%} ({a['passed']}/{a['scored']})"
        cpp = "-" if a["cost_per_pass"] is None else f"{a['cost_per_pass']:.4f}"
        lines.append(f"| {arm} | {a['runs']} | {rate} | {_ms(m['tokens'])} | {_ms(m['cost_usd'], 4)} | {cpp} | "
                     f"{_ms(m['seconds'], 1)} | {_ms(m['turns'], 1)} |")
    d = data["delta"]
    if d:
        def pct(k):
            return "-" if d.get(k) is None else f"{d[k]:+.0%}"
        pp = "-" if d.get("pass_rate_points") is None else f"{d['pass_rate_points'] * 100:+.0f}%p"
        lines += ["", (f"with − without: 토큰 {pct('tokens')} · 비용 {pct('cost_usd')} · 시간 {pct('seconds')} · "
                       f"합격률 {pp}") if ko else
                  (f"with − without: tokens {pct('tokens')} · cost {pct('cost_usd')} · time {pct('seconds')} · "
                   f"pass rate {pp}")]
    if data["warnings"]:
        lines += [""] + [f"- {tr(WARN[w], lang)}" for w in data["warnings"]]
    return "\n".join(lines)


def run(args, ctx):
    if args.action == "run":
        return run_bench(ctx, args)
    if args.action == "report":
        data = report(args.results)
        print(json.dumps(data, ensure_ascii=False, indent=1) if args.json else markdown(data, ctx.lang))
        return 0
    print("habitree bench run <과제> | habitree bench report <결과 폴더>")
    return 2
