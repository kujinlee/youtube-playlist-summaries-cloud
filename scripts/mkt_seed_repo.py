#!/usr/bin/env python3
"""Build the tier-A seeded stranger repository and its known-facts file (marketplace-inventory plan, Task 13;
spec §6, pass condition 2).

    python3 scripts/mkt_seed_repo.py --self-test  # 13 cases
    python3 scripts/mkt_seed_repo.py --out DIR

seed(out) makes `out/repo` — a git repository with a FIXED history (fixed author, fixed dates through
GIT_AUTHOR_DATE / GIT_COMMITTER_DATE, host git config off through `fixture_git.env`), its own
`docs/roadmap-to-launch.md` and `docs/backlog.md` with known rows, one `scripts/check-docs.py` that prints a known
line, and NO `.claude/` — and writes `out/known-facts.json` BESIDE it (never inside, so the repository's own
`git status` stays clean). `out` must be absent or empty: anything else is CANNOT RUN (rc 2).

The known facts are `brief`'s ground-truth items (`.agents/skills/brief/SKILL.md` → *Step 1 — establish ground
truth*): 12 CHOSEN items, each with the answer THIS repository gives. Not one per command or file that step names:
`git diff --stat <boundary>..HEAD`, `docs/reviews/` and `docs/superpowers/` have no item, and the three absent ratchets
share one (`ratchets-absent`). An item whose seeded
fact is emptiness carries `"expected": ""` and `"empty_is_correct": true` (a clean `git status --short`, a ratchet
the repository does not have, a live release no stranger command can read), so pass condition 2 can fail both
ways: a page that invents content for an empty item is `wrong`, a page that returns nothing for a non-empty item is
`missing-capability`. Items read from git (the log, the branch, the ahead count) are DERIVED from the built
repository by running git, never typed; the fixed dates make them identical on every run. The other non-empty
items (roadmap status, deployed line, waiting decision, open backlog rows, the ratchet's output) ARE typed, so a
self-test case re-reads each from the COMMITTED file it names, by its own parse, and refuses any that disagrees.

What this cannot do: it seeds `brief`'s facts only. The other page skills have no seeded facts (plan Task 14
Step 4: their pass condition 2 is `argued`).
"""
from __future__ import annotations

import dataclasses
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

AUTHOR = {"GIT_AUTHOR_NAME": "Seed Author", "GIT_AUTHOR_EMAIL": "seed@example.invalid",
          "GIT_COMMITTER_NAME": "Seed Author", "GIT_COMMITTER_EMAIL": "seed@example.invalid"}
BRANCH = "master"

ROADMAP = """# Roadmap to launch

Status: milestone 2 of 3 — the import pipeline is half built.

Deployed: release v4 (2026-03-02)

## Waiting on the owner

- ⛔ Decision: choose the storage backend for imports — A: SQLite, B: Postgres.

## Steps

- [x] Milestone 1 — the reader
- [ ] Milestone 2 — the import pipeline
- [ ] Milestone 3 — the export
"""

BACKLOG = """# Backlog

| # | Item | Status |
|---|---|---|
| 1 | Reader crashes on an empty file | ✅ fixed |
| 2 | Import drops rows with a trailing comma | open |
| 3 | Export has no progress indicator | open |
"""

CHECK_DOCS_LINE = "check-docs: 2 documents checked, 0 problems"
CHECK_DOCS = f'''#!/usr/bin/env python3
"""The seeded repository's one ratchet: prints a known line and exits 0."""
print("{CHECK_DOCS_LINE}")
'''

APP = '''def read(path):
    """Read one file; an empty file gives an empty list."""
    with open(path) as f:
        return [line.rstrip("\\n") for line in f]
'''

# (files written, subject, date) — applied in order, one commit each. The dates are what make the SHAs fixed.
HISTORY = (
    ({"README.md": "# Seeded project\n\nA small reader/importer.\n"}, "Initial commit", "2026-03-01T09:00:00+0000"),
    ({"src/app.py": APP}, "Add the reader", "2026-03-02T09:00:00+0000"),
    ({"docs/roadmap-to-launch.md": ROADMAP}, "Write the roadmap", "2026-03-03T09:00:00+0000"),
    ({"docs/backlog.md": BACKLOG}, "File three backlog rows", "2026-03-04T09:00:00+0000"),
    ({"scripts/check-docs.py": CHECK_DOCS}, "Add the docs ratchet", "2026-03-05T09:00:00+0000"),
)

# brief's ratchets that this repository does NOT have (`brief` Step 1 names four; only check-docs is seeded).
ABSENT_RATCHETS = ("check-roadmap-consistency", "check-test-counts", "check-producer-enumeration")


class CannotRun(Exception):
    """The seed cannot be built; the CLI prints `CANNOT RUN: <why>` and exits 2."""


@dataclasses.dataclass
class KnownFacts:
    repo: str
    head: str
    items: list[dict]


def _item(item_id: str, source: str, expected: str) -> dict:
    return {"id": item_id, "source": source, "expected": expected, "empty_is_correct": expected == ""}


def _git(repo: Path, *args: str, date: str | None = None) -> str:
    import fixture_git
    extra = dict(AUTHOR)
    if date is not None:
        extra.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    r = subprocess.run(["git", *args], cwd=repo, env=fixture_git.env(**extra), capture_output=True, text=True,
                       timeout=60)
    if r.returncode != 0:
        raise CannotRun(f"git {' '.join(args)} exited {r.returncode}: {r.stderr.strip()}")
    return r.stdout


def known_facts(repo: Path) -> list[dict]:
    """brief's ground-truth items, with the answer `repo` gives. Git items are read from git, never typed."""
    return [
        _item("git-log", "git log --oneline -15", _git(repo, "log", "--oneline", "-15").strip()),
        _item("git-status", "git status --short", _git(repo, "status", "--short").strip()),
        _item("branch", "git branch --show-current", _git(repo, "branch", "--show-current").strip()),
        _item("ahead-count", "git rev-list --count master..HEAD",
              _git(repo, "rev-list", "--count", f"{BRANCH}..HEAD").strip()),
        _item("roadmap-status", "docs/roadmap-to-launch.md", ROADMAP.splitlines()[2]),
        _item("roadmap-deployed", "grep 'Deployed: release' docs/roadmap-to-launch.md", ROADMAP.splitlines()[4]),
        _item("decision-waiting", "docs/roadmap-to-launch.md",
              "choose the storage backend for imports — A: SQLite, B: Postgres"),
        _item("backlog-open", "docs/backlog.md",
              "#2 Import drops rows with a trailing comma; #3 Export has no progress indicator"),
        _item("ratchet-check-docs", "python3 scripts/check-docs.py", f"rc 0: {CHECK_DOCS_LINE}"),
        # Emptiness, seeded on purpose: none of these exists or is reachable in the stranger's world.
        _item("ratchets-absent", " ".join(f"scripts/{n}.py" for n in ABSENT_RATCHETS), ""),
        _item("live-release", "flyctl releases", ""),
        _item("task-list", "TaskList", ""),
    ]


def seed(out: Path) -> KnownFacts:
    """Build `out/repo` and write `out/known-facts.json`; return the facts. `out` must be absent or empty."""
    out = Path(out)
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise CannotRun(f"{out} exists and is not an empty directory")
    repo = out / "repo"
    repo.mkdir(parents=True)
    _git(repo, "init", "-q", "-b", BRANCH)
    for files, subject, date in HISTORY:
        for rel, text in files.items():
            p = repo / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", subject, date=date)
    facts = KnownFacts(str(repo), _git(repo, "rev-parse", "HEAD").strip(), known_facts(repo))
    (out / "known-facts.json").write_text(json.dumps(dataclasses.asdict(facts), indent=2, ensure_ascii=False) + "\n")
    return facts


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--self-test"]:
        return _self_test()
    if len(argv) != 2 or argv[0] != "--out":
        print("usage: mkt_seed_repo.py --out DIR | --self-test", file=sys.stderr)
        return 2
    try:
        facts = seed(Path(argv[1]))
    except CannotRun as e:
        print(f"CANNOT RUN: {e}", file=sys.stderr)
        return 2
    print(f"seeded {facts.repo} at {facts.head}; {len(facts.items)} ground-truth items")
    return 0


def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    ok = fail = 0

    def case(name, got_fn, want):
        nonlocal ok, fail
        try:
            got = got_fn()
        except Exception as e:      # a crash is a red case, named, never a pass
            got = f"RAISED {type(e).__name__}: {e}"
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"[FAIL] {name}: got {got!r} want {want!r}")

    def tree(repo: Path) -> list[str]:
        return sorted(str(p.relative_to(repo)) for p in repo.rglob("*") if ".git" not in p.relative_to(repo).parts)

    base = Path(tempfile.mkdtemp(prefix="mkt-seed-"))
    # b is seeded over a second later, so a wall-clock date would give a different SHA: the determinism case
    # cannot pass for the ambient reason that both seeds ran within one second.
    a = seed(base / "a")
    time.sleep(1.1)
    b = seed(base / "b")
    ids = [i["id"] for i in a.items]

    case("two seeds give identical trees", lambda: (a.head == b.head, tree(Path(a.repo)) == tree(Path(b.repo))),
         (True, True))
    case("two seeds give identical known facts", lambda: a.items == b.items, True)
    case("every ground-truth item has an expected answer",
         lambda: all(isinstance(i.get("expected"), str) and i.get("source") for i in a.items), True)
    case("item ids are unique", lambda: len(ids) == len(set(ids)), True)
    case("at least one item is correctly empty and one is non-empty",
         lambda: (any(i["empty_is_correct"] for i in a.items), any(not i["empty_is_correct"] for i in a.items)),
         (True, True))
    case("empty_is_correct is true exactly when the expected answer is empty",
         lambda: all(i["empty_is_correct"] == (i["expected"] == "") for i in a.items), True)
    case("a clean git status is a correctly-empty item",
         lambda: [i["empty_is_correct"] for i in a.items if i["id"] == "git-status"], [True])
    case("the git log fact names every seeded commit, newest first",
         lambda: [ln.split(" ", 1)[1] for ln in a.items[0]["expected"].splitlines()],
         [h[1] for h in reversed(HISTORY)])
    case("the seeded repository has no .claude directory", lambda: (Path(a.repo) / ".claude").exists(), False)
    case("known-facts.json is written beside the repository, and matches what seed returned",
         lambda: json.loads((base / "a" / "known-facts.json").read_text())["items"] == a.items, True)
    case("the seeded check-docs prints its known line",
         lambda: subprocess.run([sys.executable, str(Path(a.repo) / "scripts/check-docs.py")], capture_output=True,
                                text=True, timeout=60).stdout.strip(), CHECK_DOCS_LINE)

    def typed_facts_disagreeing_with_the_committed_files():
        # An independent parse of what the repository COMMITTED — never the module's ROADMAP/BACKLOG constants — so
        # a typed fact that drifts from its file (a wrong line index, a hand-edited row) goes red here.
        repo = Path(a.repo)
        roadmap = _git(repo, "show", "HEAD:docs/roadmap-to-launch.md").splitlines()
        backlog = _git(repo, "show", "HEAD:docs/backlog.md").splitlines()
        rows = [[c.strip() for c in ln.strip("|").split("|")] for ln in backlog if ln.startswith("| ")]
        open_rows = "; ".join(f"#{r[0]} {r[1]}" for r in rows if r[0].isdigit() and r[2] == "open")
        decisions = [ln.split("Decision: ", 1)[1].rstrip(".") for ln in roadmap if ln.startswith("- ⛔ Decision: ")]
        ran = subprocess.run([sys.executable, str(repo / "scripts/check-docs.py")], capture_output=True, text=True,
                             timeout=60)
        by = {i["id"]: i["expected"] for i in a.items}
        src = {i["id"]: i["source"] for i in a.items}
        # The file (or command) each answer above was parsed from, written out independently: a fact whose `source`
        # names a different file is a false pairing even when its answer is right (r2 Codex m1).
        parsed_from = {"roadmap-status": "docs/roadmap-to-launch.md", "roadmap-deployed": "docs/roadmap-to-launch.md",
                       "decision-waiting": "docs/roadmap-to-launch.md", "backlog-open": "docs/backlog.md",
                       "ratchet-check-docs": "scripts/check-docs.py"}
        held = {
            "roadmap-status": by["roadmap-status"] in [ln for ln in roadmap if ln.startswith("Status: ")],
            "roadmap-deployed": by["roadmap-deployed"] in [ln for ln in roadmap if "Deployed: release" in ln],
            "decision-waiting": by["decision-waiting"] in decisions,
            "backlog-open": open_rows != "" and by["backlog-open"] == open_rows,
            "ratchet-check-docs": by["ratchet-check-docs"] == f"rc {ran.returncode}: {ran.stdout.strip()}",
        }
        held = {k: ok_ and parsed_from[k] in src[k].split() + [src[k]] for k, ok_ in held.items()}
        return sorted(k for k, ok_ in held.items() if not ok_)
    case("every typed fact is what the committed file it names says", typed_facts_disagreeing_with_the_committed_files,
         [])

    def refused():
        try:
            seed(base / "a")
        except CannotRun as e:
            return f"CANNOT RUN: {'not an empty directory' in str(e)}"
        return "RETURNED"
    case("a non-empty out is CANNOT RUN", refused, "CANNOT RUN: True")
    shutil.rmtree(base, ignore_errors=True)
    print(f"{ok}/{ok + fail} self-test cases passed")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
