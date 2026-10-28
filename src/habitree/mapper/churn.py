"""git 기록: 자주 바뀌는 곳(핫스팟)과 파일별 마지막 커밋 시각. git이 없으면 None. / Git history helpers.

핫스팟 점수 = 변경 횟수 × 지금 줄 수. 자주 바뀌면서 큰 파일이 먼저 볼 곳이다.
"""
from collections import defaultdict

from ..core.paths import git, nfc

CHUNK = 100  # 명령줄 길이 한도(Windows) 때문에 경로를 나눠 보낸다


def _records(out):
    """git log -z 출력 → [(머리, [항목…])]. 커밋마다 \\x01로 시작한다."""
    for chunk in out.split(b"\x01")[1:]:
        head, _, rest = chunk.partition(b"\0")
        items = [x.strip(b"\n") for x in rest.split(b"\0")]
        yield head.decode("utf-8", errors="replace"), [x for x in items if x]


def commits(root, max_commits=2000):
    """[[(파일, 바뀐 줄), …] 커밋마다, 최근 것부터] 또는 None(git 없음). / Files per commit, newest first."""
    out = git(root, "-c", "core.quotepath=false", "log", "--relative", "--no-renames", "--numstat",
              f"--max-count={int(max_commits)}", "--format=%x01%H", "-z", timeout=120)
    if out is None:
        return None
    rows = []
    for _, items in _records(out):
        files = []
        for item in items:
            parts = item.split(b"\t", 2)
            if len(parts) != 3:
                continue
            added, deleted, path = parts
            files.append((nfc(path.decode("utf-8", errors="replace")),
                          (int(added) if added.isdigit() else 0) + (int(deleted) if deleted.isdigit() else 0)))
        rows.append(files)
    return rows


def history(root, max_commits=2000):
    """{파일: [변경 횟수, 바뀐 줄 합]} 또는 None(git 없음). / Per-file change counts, or None without git."""
    rows = commits(root, max_commits)
    if rows is None:
        return None
    stats = defaultdict(lambda: [0, 0])
    for files in rows:
        for path, changed in files:
            stats[path][0] += 1
            stats[path][1] += changed
    return dict(stats)


def hotspots(root, index, max_commits=2000, top=15):
    """[(점수, 파일, 변경 횟수, 줄 수, 바뀐 줄 합)] 또는 None. 지금 색인에 있는 파일만. / Hotspots or None."""
    hist = history(root, max_commits)
    if hist is None:
        return None
    files = index.get("files", {})
    rows = []
    for rel, (n, changed) in hist.items():
        rec = files.get(rel)
        if not rec or not rec.get("lines"):
            continue
        rows.append((n * rec["lines"], rel, n, rec["lines"], changed))
    rows.sort(key=lambda r: (-r[0], r[1]))
    return rows[:top] if top else rows


def last_commit_times(root, paths):
    """{파일: 마지막 커밋 시각(유닉스 초)} 또는 None(git 없음·리포 아님). / Last commit time per path."""
    paths = sorted(set(paths))
    result = {}
    for k in range(0, len(paths), CHUNK):
        part = paths[k:k + CHUNK]
        out = git(root, "--literal-pathspecs", "-c", "core.quotepath=false", "log", "--relative",
                  "--format=%x01%ct", "--name-only", "-z", "--", *part, timeout=120)
        if out is None:
            return None
        for head, items in _records(out):
            try:
                ts = int(head.strip())
            except ValueError:
                continue
            for item in items:
                p = nfc(item.decode("utf-8", errors="replace"))
                if p not in result:
                    result[p] = ts
    return result


def render(rows, lang):
    ko = lang == "ko"
    if rows is None:
        return ("git이 없거나 git 리포가 아니어서 건너뜁니다(변경 기록이 필요함)." if ko
                else "Skipped: git is not available or this is not a git repository.")
    if not rows:
        return "변경 기록이 있는 파일이 없습니다." if ko else "No files with change history."
    out = ["# 자주 바뀌는 곳 (점수 = 변경 횟수 × 줄 수)" if ko else "# Hotspots (score = changes × lines)",
           f"  {'점수':>8} {'변경':>5} {'줄':>6} {'바뀐 줄':>8}  {'파일'}" if ko
           else f"  {'score':>8} {'chg':>5} {'lines':>6} {'churn':>8}  file"]
    for score, rel, n, lines, changed in rows:
        out.append(f"  {score:>8} {n:>5} {lines:>6} {changed:>8}  {rel}")
    out.append("크고 자주 바뀌는 파일은 나누거나 시험을 먼저 더할 후보입니다." if ko
               else "Large files that change often are candidates for splitting or for more tests first.")
    return "\n".join(out)
