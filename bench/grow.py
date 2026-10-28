"""규칙이 자라는지 두 세션으로 잰다. / Measure whether rules grow, across two sessions.

  python bench/grow.py <과제> [--arms with,without] [--reps 3] [--model sonnet] [--max-budget-usd 1] [--hooks] --yes

한 번의 흐름:
  1. 세션 1: 과제 A를 시킨다. with 갈래는 habitree init만 하고 과제 규칙은 넣지 않는다(규칙 0개).
  2. 세션 1이 채점에 떨어지면 같은 세션에서 평범하게 바로잡는다(task.json grow.correction).
     "기억해 줘" 같은 말은 하지 않는다. 시키지 않아도 규칙으로 남기는지를 보려는 것이다.
  3. 코드 파일만 처음 상태로 되돌리고, 같은 폴더에서 새 세션으로 비슷한 과제 B를 시킨다(grow.next).
     지침 파일, .habitree/, 도구가 남긴 기억은 그대로 이어진다. 실제로 프로젝트를 이어 쓰는 것과 같게.
  4. B를 채점한다. 두 갈래 모두 `habitree` 명령을 쓸 수 있게 허용한다(PATH에 있어야 한다).
--hooks면 with 갈래에 Claude Code 훅도 단다(habitree init --hooks). 플러그인을 쓰는 것과 같은 알림이 돈다.

결과는 bench/results/<UTC 날짜>-grow-<과제>/에 남는다(커밋하지 않음). 실제 사용량이 들어 --yes가 있어야 돈다.
"""
import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from habitree.commands import bench  # noqa: E402
from habitree.commands.verify import run_one  # noqa: E402
from habitree.core import io as hio  # noqa: E402
from habitree.core.config import Context  # noqa: E402
from habitree.core.i18n import tr  # noqa: E402
from habitree.core.timeutil import now_iso, now_utc  # noqa: E402
from habitree.sessions import claude as sessions  # noqa: E402

CODE = (".py", ".js", ".mjs", ".cjs", ".ts")


def call(task, prompt, arm, work, args, run_dir, resume=None):
    t = dict(task, prompt={task.get("lang", "ko"): prompt},
             allowed_tools=task.get("allowed_tools", []) + ["Bash(habitree *)"])
    argv, env = bench.claude_command(t, arm, work, args, run_dir)
    if resume:
        argv += ["--resume", resume]
    import subprocess
    import time
    start = time.monotonic()
    try:
        r = subprocess.run(argv, cwd=str(work), env=env, capture_output=True, timeout=task.get("timeout", 900))
        out, status = hio.read_bytes_text(r.stdout or b""), "ok"
    except subprocess.TimeoutExpired as e:
        out, status = hio.read_bytes_text(e.stdout or b""), "timeout"
    m = bench.parse_result(out)
    m["status"] = status
    m["seconds"] = round(time.monotonic() - start, 1)
    return m, out


def grade(task_dir, verify, work):
    checks = [run_one(SimpleNamespace(root=work), f"v{i + 1}", [bench._sub(a, task_dir) for a in v], 300)
              for i, v in enumerate(verify)]
    tail = [c["tail"] if isinstance(c["tail"], str) else "\n".join(c["tail"]) for c in checks]
    return all(c["ok"] for c in checks), "\n".join(tail)[-400:]


def own_rules(work):
    """세션 사이에 이 프로젝트에 생긴 규칙(꾸러미 규칙은 빼고). / Rules this project grew."""
    data = hio.load_json(work / ".habitree" / "rules.json", {}) or {}
    return [{"id": r["id"], "scope": r.get("scope"), "level": r.get("level"), "rule": r.get("rule")}
            for r in data.get("rules", []) if not r.get("origin")]


def memory_files(session_id, work):
    folder = sessions.transcript_dir(session_id, work) if session_id else None
    mem = folder / "memory" if folder else None
    return sorted(p.name for p in mem.glob("*.md")) if mem and mem.is_dir() else []


def snapshot(work):
    return {p.relative_to(work).as_posix(): p.read_bytes() for p in work.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts}


def reset_code(work, project):
    """코드 파일만 처음 상태로. 세션 1이 더한 코드 파일은 지운다. / Reset code files only."""
    for p in list(work.rglob("*")):
        if p.is_file() and p.suffix in CODE and not (project / p.relative_to(work)).exists():
            p.unlink()
    for p in project.rglob("*"):
        if p.is_file() and p.suffix in CODE:
            shutil.copy2(str(p), str(work / p.relative_to(project)))


def flow(task_dir, task, arm, rep, args, out):
    lang = task.get("lang", "ko")
    run_dir = out / "runs" / f"{arm}-{rep}"
    run_dir.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="habitree-grow-"))
    work = tmp / "project"
    rec = {"arm": arm, "rep": rep, "at": now_iso()}
    try:
        shutil.copytree(str(task_dir / "project"), str(work))
        if arm == "with":
            bench.setup_with(work, dict(task, rules=[]), lang)
            if args.hooks:
                from habitree.guard import install
                install.merge_settings(work, False)
        before = snapshot(work)
        m1, raw = call(task, tr(task["prompt"], lang), arm, work, args, run_dir)
        hio.write_text(run_dir / "s1.out", raw)
        ok1, tail1 = grade(task_dir, task["verify"], work)
        rec["s1"] = {"pass": ok1, "tail": tail1, "tokens": m1.get("tokens"), "cost": m1.get("cost_usd"),
                     "session": m1.get("session_id")}
        if not ok1 and m1.get("session_id"):
            mc, raw = call(task, tr(task["grow"]["correction"], lang), arm, work, args, run_dir,
                           resume=m1["session_id"])
            hio.write_text(run_dir / "fix.out", raw)
            okc, tailc = grade(task_dir, task["verify"], work)
            rec["fix"] = {"pass": okc, "tail": tailc, "tokens": mc.get("tokens"), "cost": mc.get("cost_usd"),
                          "session": mc.get("session_id")}
        after = snapshot(work)
        rec["learned"] = {
            "rules": own_rules(work),
            "changed_files": sorted(k for k in after if not k.endswith(CODE) and before.get(k) != after[k]),
            "memory": memory_files(m1.get("session_id"), work)}
        reset_code(work, task_dir / "project")
        m2, raw = call(task, tr(task["grow"]["next"]["prompt"], lang), arm, work, args, run_dir)
        hio.write_text(run_dir / "s2.out", raw)
        ok2, tail2 = grade(task_dir, task["grow"]["next"]["verify"], work)
        rec["s2"] = {"pass": ok2, "tail": tail2, "tokens": m2.get("tokens"), "cost": m2.get("cost_usd"),
                     "session": m2.get("session_id")}
        hio.save_json(run_dir / "run.json", rec)
        fix = rec.get("fix")
        print(f"  {arm}-{rep}: s1 {'pass' if ok1 else 'fail'}"
              + (f" -> fix {'pass' if fix['pass'] else 'fail'}" if fix else "")
              + f" | rules {len(rec['learned']['rules'])} files {rec['learned']['changed_files']}"
              + f" memory {len(rec['learned']['memory'])} | s2 {'pass' if ok2 else 'fail'}", flush=True)
        return rec
    finally:
        shutil.rmtree(str(tmp), ignore_errors=True)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("task")
    p.add_argument("--arms", default="with,without")
    p.add_argument("--reps", type=int, default=3)
    p.add_argument("--model", default="sonnet")
    p.add_argument("--max-budget-usd", type=float, default=1.0)
    p.add_argument("--out")
    p.add_argument("--hooks", action="store_true", help="with 갈래에 Claude Code 훅 / hooks in the with arm")
    p.add_argument("--yes", action="store_true")
    args = p.parse_args(argv)
    args.isolation = "none"
    root = Path(__file__).resolve().parents[1]
    task_dir, task = bench.load_task(Context(root, {}, "ko"), args.task)
    if "grow" not in task:
        sys.exit(f"task.json has no grow section: {task_dir}")
    if not args.yes:
        sys.exit("claude -p runs use real usage; add --yes")
    out = Path(args.out) if args.out else root / "bench" / "results" / f"{now_utc():%Y-%m-%d}-grow-{task['name']}"
    (out / "runs").mkdir(parents=True, exist_ok=True)
    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    print(f"grow: {task['name']} · {', '.join(arms)} × {args.reps} · model {args.model}"
          + (" · hooks" if args.hooks else ""), flush=True)
    recs = [flow(task_dir, task, arm, rep, args, out) for rep in range(1, args.reps + 1) for arm in arms]
    summary = {}
    for arm in arms:
        rs = [r for r in recs if r["arm"] == arm]
        summary[arm] = {"s1_pass": sum(r["s1"]["pass"] for r in rs), "fixed": sum(1 for r in rs if r.get("fix")),
                        "rule_recorded": sum(1 for r in rs if r["learned"]["rules"]),
                        "s2_pass": sum(r["s2"]["pass"] for r in rs), "runs": len(rs)}
    hio.save_json(out / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
