#!/usr/bin/env python3
"""Rebuild every generated page after a command that MAY merge a PR, so no page describes a world that has moved on.

    python3 scripts/regen-pages.py --hook < payload.json   # what .claude/hooks/regen-pages.sh runs
    python3 scripts/regen-pages.py --all                   # every page, now
    python3 scripts/regen-pages.py --page backlog-table    # one page (the edit hooks, the Refresh button)
    python3 scripts/regen-pages.py --self-test             # 66 cases

WHY (owner decision D3, 2026-10-28, backlog #363). A merge moves the state every generated page reads —
the dashboard's PR list, the backlog's closed rows, the goals and features maps, the goal tree's leaves —
and before this only the goal tree was rebuilt on one. The others went stale until someone edited their
source file or pressed Refresh.

THE TRIGGER IS A SUBSTRING, DELIBERATELY OVER-EAGER (round 3, architecture review SPLIT): it fires when the
Bash command TEXT contains `gh pr merge`. It does not parse shell — three rounds of a tokenizer each found the
previous one's grammar wrong. A FALSE FIRE (`echo "gh pr merge"`, a comment, `gh pr merge-base`, `false && gh
pr merge`, a here-document body) costs one rebuild, about 18 s. A MISS needs `eval`, an alias, or a merge
spelled without that text (`"gh" pr merge`, two spaces between words); the page's build time and replay
notice make that staleness visible.

BOTH EVENTS (round 4 W1): the runner is registered under `PostToolUse` AND `PostToolUseFailure` for Bash, so
a merge followed by a failing command (`gh pr merge 433; false`, which exits non-zero) still rebuilds. Each
registration also carries `if: Bash(gh pr merge*)`, Claude Code's best-effort per-subcommand pre-filter.

WHAT IT RUNS: every page in `explainer-serve.REGENERABLE`, through each generator's existing entry point
(`python3 scripts/<generator>.py`, no arguments — exactly what the Refresh button runs). ONE list: a page
added there is rebuilt on merge without touching this file. After an edit of `docs/goal-threads.md` only
the goal tree is rebuilt, because nothing else reads that file.

⛔ ADVISORY AND BOUNDED. `--hook` exits 0 whatever happens: a page that failed to rebuild is stale, not a
reason to fail the merge that already happened. Each generator runs in its own process with its own
timeout (TIMEOUT s); they run concurrently, and one that fails, hangs or crashes never stops the others.
Every failure is NAMED in the report with its exit code — a timeout says it timed out — so the reader is
told which page is behind instead of reading silence as success.

⛔ EVERY PAGE IS BUILT FROM A FRESH `origin/master`, NEVER FROM THE CALLER'S WORKING TREE (backlog #408).
Measured 2026-11-07 20:15: the main checkout, which the hooks and the server ran from, stood 18 commits
behind `origin/master`, so every page the owner read described an old tree — and nothing on it said so
louder than a short sha. The main checkout also holds UNCOMMITTED owner and agent edits, so the fix may
NEVER pull, reset or check out there. Instead, under a lock (`LOCK_REL`):
  1. `git fetch origin master` in the main checkout — refs and objects only; its HEAD, index and files
     are never touched;
  2. `origin/master` is materialised in a GENERATOR-OWNED, git-ignored linked worktree, `TREE_REL` under
     the main checkout: created with `git worktree add --detach` the first time, moved with
     `git checkout --detach --force` + `git clean -fd` after that. ⛔ Those two mutate ONLY after the path
     is proven to be its OWN linked worktree (a `.git` FILE, its own top level, this repository's common
     dir) — run in a plain directory, git would walk up to the main checkout and discard its edits;
  3. the tree is READ BACK (its HEAD is that sha, its status clean), and only then does each generator
     run as `<tree>/scripts/<generator>.py` with `cwd=<tree>`, so the generator's CODE is master's too.
Output still goes to `~/explainers/` (each generator's own default). Live state is NOT in git and is not
read from the tree: the in-flight ledger, the goal-tree log and the plans are found through
`session-state.main_checkout`, which names the main checkout from the tree as from anywhere else. Every
page's chrome bar already carries `page_chrome.provenance` (`<when> · <sha>`), which now names master's
commit; this runner's report and `--page` add `built from origin/master <sha>`.
⛔ CANNOT RUN IS LOUD AND NEVER FALLS BACK: when the fetch, the worktree, the read-back or the lock fails,
NO generator runs, the reason is printed as `CANNOT RUN`, and the served pages are left as they were.

EXIT CODES: `--hook` is always 0. `--all` is 0 when every page rebuilt, 1 when any did not, 2 when the
fresh tree could not be produced. `--page` is the generator's own exit code, or 2 (CANNOT RUN / unknown).
"""
from __future__ import annotations

import argparse
import concurrent.futures
import contextlib
import fcntl
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
import time

SCRIPTS = pathlib.Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
TIMEOUT = 120          # seconds, per generator; the slowest measured 2026-10-28 was gen-backlog-page, 17s
THREADS_REL = "docs/goal-threads.md"
REMOTE, BRANCH = "origin", "master"
TREE_REL = ".claude/regen-tree"      # generator-owned, git-ignored, under the MAIN checkout (backlog #408)
LOCK_REL = ".claude/regen-tree.lock"
GIT_TIMEOUT = 120      # seconds, per git call; a fetch on a slow link is the long one
LOCK_WAIT = 150        # seconds a second rebuild waits for the first before saying CANNOT RUN
SHA = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")
_IN_SUITE = False      # set by `_self_test`; see `fresh`


class CannotRun(Exception):
    """The fresh `origin/master` tree could not be produced. Every caller SAYS so; none falls back."""


REPO_VARS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY",
             "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE", "GIT_PREFIX", "GIT_CEILING_DIRECTORIES")


def _env() -> dict[str, str]:
    """The environment for git and the generators, minus every inherited variable that changes WHICH
    repository or tree git acts on: a hook context can set `GIT_DIR`, which `cwd` does NOT override, and a
    `checkout --force` would then land on it. Config variables (the suite's isolation) pass through."""
    return {k: v for k, v in os.environ.items() if k not in REPO_VARS}


def _git(args: list[str], cwd: pathlib.Path, timeout: float = GIT_TIMEOUT) -> tuple[int, str]:
    """One git call. (rc, stdout) on success, (rc, the error text) on failure; 124 on a timeout."""
    try:
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=timeout,
                           stdin=subprocess.DEVNULL, env=_env(), errors="replace")
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout:.0f}s"
    except OSError as exc:
        return 127, f"{type(exc).__name__}: {exc}"
    return r.returncode, ((r.stdout if r.returncode == 0 else (r.stderr or r.stdout)) or "").strip()


def _brief(text: str) -> str:
    return " ".join(str(text).split())[:160]


def main_of(repo: pathlib.Path, git=_git) -> tuple[pathlib.Path, pathlib.Path]:
    """(the MAIN checkout, the repository's common git dir), named by `--git-common-dir` from any
    checkout of it — the rule `session-state.main_checkout` uses. CannotRun when git cannot say."""
    rc, common = git(["rev-parse", "--path-format=absolute", "--git-common-dir"], repo)
    if rc != 0 or not common or "\n" in common or not os.path.isabs(common):
        raise CannotRun(f"git cannot name this repository's common directory from {repo} "
                        f"(exit {rc}: {_brief(common)})")
    return pathlib.Path(common).parent, pathlib.Path(common)


def _own_worktree(tree: pathlib.Path, common: pathlib.Path, git) -> str | None:
    """None when `tree` is provably its OWN linked worktree of this repository, else why not. ⛔ This is
    the guard between `checkout --force` / `clean` and the main checkout's uncommitted edits: in a
    directory with no `.git`, git walks UP and acts on the main checkout instead."""
    if tree.is_symlink() or not (tree / ".git").is_file():
        return "it is not a linked worktree (no .git FILE in it)"
    rc, top = git(["rev-parse", "--show-toplevel"], tree)
    if rc != 0 or os.path.realpath(top) != os.path.realpath(tree):
        return f"git reads its top level as {_brief(top)!r} (exit {rc}), not the tree itself"
    rc, tc = git(["rev-parse", "--path-format=absolute", "--git-common-dir"], tree)
    if rc != 0 or os.path.realpath(tc) != os.path.realpath(common):
        return f"it belongs to another repository ({_brief(tc)!r}, exit {rc})"
    return None


def materialise(main: pathlib.Path, common: pathlib.Path, git=_git) -> tuple[pathlib.Path, str]:
    """Fetch, and put `origin/master` in the generator-owned tree. (tree, sha), or CannotRun naming the
    step. ⛔ The only commands run IN the main checkout are `fetch`, `rev-parse` and `worktree`."""
    tree = main / TREE_REL
    rc, out = git(["fetch", "--quiet", REMOTE, BRANCH], main)
    if rc != 0:
        raise CannotRun(f"`git fetch {REMOTE} {BRANCH}` failed (exit {rc}: {_brief(out)})")
    rc, sha = git(["rev-parse", "--verify", "--quiet", f"refs/remotes/{REMOTE}/{BRANCH}^{{commit}}"], main)
    if rc != 0 or not SHA.fullmatch(sha):
        raise CannotRun(f"{REMOTE}/{BRANCH} does not resolve to a commit after the fetch "
                        f"(exit {rc}: {_brief(sha)!r})")
    if os.path.lexists(tree):
        why = _own_worktree(tree, common, git)
        if why:
            raise CannotRun(f"{tree} exists but {why} — refusing to touch it; remove it by hand")
        steps = [(["checkout", "--quiet", "--detach", "--force", sha], tree), (["clean", "-fdq"], tree)]
    else:
        git(["worktree", "prune"], main)          # a deleted tree still registered; the add says what failed
        steps = [(["worktree", "add", "--quiet", "--detach", "--force", str(tree), sha], main)]
    for args, cwd in steps:
        rc, out = git(args, cwd)
        if rc != 0:
            raise CannotRun(f"`git {' '.join(args[:2])}` for {tree} failed (exit {rc}: {_brief(out)})")
    why = _own_worktree(tree, common, git)
    if why:
        raise CannotRun(f"after materialising, {tree}: {why}")
    rc, head = git(["rev-parse", "HEAD"], tree)
    if rc != 0 or head != sha:
        raise CannotRun(f"{tree} reads back HEAD {_brief(head)!r} (exit {rc}), not {REMOTE}/{BRANCH} {sha}")
    rc, dirty = git(["status", "--porcelain"], tree)
    if rc != 0 or dirty:
        raise CannotRun(f"{tree} is not clean after the checkout (exit {rc}: {_brief(dirty)})")
    return tree, sha


@contextlib.contextmanager
def tree_lock(main: pathlib.Path, wait: float = LOCK_WAIT):
    """Hold `LOCK_REL` for the materialise AND the generators: a second rebuild moving the tree under a
    running generator would hand it half of two commits. CannotRun when it is not free within `wait` s."""
    path = main / LOCK_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as fh:
        deadline = time.monotonic() + wait
        while True:
            try:
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise CannotRun(f"another page rebuild held {path} for {wait:.0f}s") from None
                time.sleep(0.2)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


@contextlib.contextmanager
def fresh(repo: pathlib.Path = ROOT, git=_git, wait: float = LOCK_WAIT):
    """The ONE way a page is built: (tree, sha) of a fresh `origin/master`, locked for the block.
    ⛔ Refused inside the suite for THIS repository: measured while building this, one case that reached the
    default `tree_for` fetched and added `.claude/regen-tree` in the real main checkout. Not mutated, on
    purpose — a mutant that removed this guard would do exactly that to the real checkout."""
    if _IN_SUITE and os.path.realpath(repo) == os.path.realpath(ROOT):
        raise CannotRun("the self-test never materialises the real repository")
    main, common = main_of(repo, git)
    with tree_lock(main, wait):
        yield materialise(main, common, git)


def _fresh_once(repo: pathlib.Path) -> tuple[pathlib.Path, str]:
    """`fresh` entered and left: the (tree, sha) it produced. For the suite's real-git cases."""
    with fresh(repo) as got:
        return got


def may_merge(cmd: str) -> bool:
    """PURE. Does the Bash command TEXT contain `gh pr merge`? A substring test, deliberately over-eager:
    see the module docstring for what over-fires (one ~18 s rebuild) and what it misses."""
    return "gh pr merge" in cmd


def regenerable() -> dict[str, str]:
    """The page -> generator map the server's Refresh button uses. Imported, never copied."""
    spec = importlib.util.spec_from_file_location("_explainer_serve", SCRIPTS / "explainer-serve.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return dict(mod.REGENERABLE)


# ⛔ round 4 W1: BOTH events. A merge followed by a failing command (`gh pr merge 433; false`) exits non-zero,
# and Claude Code delivers a failed tool call to PostToolUseFailure, not PostToolUse. That event carries the
# same `tool_name` and `tool_input` (`tool_input.command` for Bash) plus `error`, per the Claude Code hooks
# reference, so `pages_for` reads it unchanged. `registered_events` lets the suite check settings.json.
EVENTS = ("PostToolUse", "PostToolUseFailure")
HOOK_NAME = "regen-pages.sh"


def registered_events(settings: object) -> list[str]:
    """PURE. The events under which a `Bash`-matched hook runs this runner, from a settings.json mapping."""
    hooks = settings.get("hooks") if isinstance(settings, dict) else None
    out = []
    for event, groups in (hooks.items() if isinstance(hooks, dict) else []):
        for g in groups if isinstance(groups, list) else []:
            if isinstance(g, dict) and g.get("matcher") == "Bash" and any(
                    isinstance(h, dict) and HOOK_NAME in str(h.get("command", "")) for h in g.get("hooks") or []):
                out.append(event)
    return sorted(set(out))


def pages_for(payload: object, pages: dict[str, str]) -> list[str]:
    """PURE. Which pages a PostToolUse or PostToolUseFailure payload asks to rebuild: all of them after a
    command containing `gh pr merge`, the goal tree alone after an edit of the threads file, nothing
    otherwise (including a payload that is not one, or one with no `tool_input.command`)."""
    if not isinstance(payload, dict):
        return []
    ti = payload.get("tool_input")
    ti = ti if isinstance(ti, dict) else {}
    cmd, fp = ti.get("command"), ti.get("file_path")
    if isinstance(cmd, str) and may_merge(cmd):
        return sorted(pages)
    if isinstance(fp, str) and (fp == THREADS_REL or fp.endswith("/" + THREADS_REL)):
        return [p for p in ("goal-tree",) if p in pages]
    return []


def launch(script: str, timeout: float, tree: pathlib.Path) -> tuple[int, str]:
    """Run one generator OUT OF THE FRESH TREE. (rc, its stdout then stderr); 124 when it timed out."""
    try:
        r = subprocess.run([sys.executable, str(tree / "scripts" / script)], cwd=tree, capture_output=True,
                           text=True, timeout=timeout, stdin=subprocess.DEVNULL, env=_env(), errors="replace")
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout:.0f}s"
    return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()


def regen(names: list[str], pages: dict[str, str], run=launch, timeout: float = TIMEOUT,
          tree: pathlib.Path = ROOT) -> list[dict]:
    """Run each page's generator concurrently. One result per page, in `names` order. NEVER RAISES: a
    generator that raises is a failed result like any other, and the rest still run."""
    def one(name):
        t0 = time.monotonic()
        try:
            rc, tail = run(pages[name], timeout, tree)
        except Exception as exc:                      # noqa: BLE001 - named in the report, never swallowed
            rc, tail = -1, f"{type(exc).__name__}: {exc}"
        return {"page": name, "rc": rc, "secs": round(time.monotonic() - t0, 1), "tail": tail}
    if not names:
        return []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(names)) as pool:
        return list(pool.map(one, names))


def built_from(sha: str) -> str:
    """PURE. The provenance line every report carries (backlog #408)."""
    return f"built from {REMOTE}/{BRANCH} {sha[:12]}"


def report(results: list[dict], wall: float, sha: str = "") -> list[str]:
    """PURE. One summary line (naming the commit when known), then one line per page that did NOT rebuild."""
    ok = [r for r in results if r["rc"] == 0]
    bad = [r for r in results if r["rc"] != 0]
    out = [f"↻ pages rebuilt: {len(ok)} of {len(results)} in {wall:.1f}s ("
           + ", ".join(f"{r['page']} {r['secs']}s" for r in results) + ")"
           + (f" — {built_from(sha)}" if sha else "")]
    out += [f"⚠  {r['page']} NOT rebuilt (exit {r['rc']}) — its page is STALE: "
            + " ".join(r["tail"].split())[-200:] for r in bad]
    return out


def cannot_run_line(exc: Exception) -> str:
    """PURE. What every caller prints when the fresh tree could not be produced — never a fallback."""
    return (f"⚠  CANNOT RUN — pages NOT rebuilt: {exc}. Nothing was built from any other tree, so every "
            f"served page is unchanged and may be STALE (backlog #408).")


def main(argv: list[str] | None = None, *, stdin=None, run=launch, pages=None, tree_for=fresh) -> int:
    ap = argparse.ArgumentParser(description="Rebuild every generated page (owner decision D3).")
    ap.add_argument("--hook", action="store_true", help="read a PostToolUse payload on stdin")
    ap.add_argument("--all", action="store_true", help="rebuild every page now")
    ap.add_argument("--page", metavar="NAME", help="rebuild ONE page and print its generator's output")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(sys.argv[1:] if argv is None else argv)
    if a.self_test:
        return _self_test()
    loud = a.all or a.page is not None                # a command, not a hook: its exit code means something
    try:
        table = pages if pages is not None else regenerable()
        if a.page is not None:
            if a.page not in table:
                print(f"⚠  unknown page {a.page!r}; rebuildable pages are: {', '.join(sorted(table))}")
                return 2
            names = [a.page]
        elif a.all:
            names = sorted(table)
        else:
            try:
                payload = json.loads((stdin or sys.stdin).read())
            except ValueError:
                payload = None
            names = pages_for(payload, table)
        if not names:
            return 0
        try:
            with tree_for() as (tree, sha):
                t0 = time.monotonic()
                results = regen(names, table, run, tree=tree)
        except CannotRun as exc:
            print(cannot_run_line(exc))
            return 2 if loud else 0
        if a.page is not None:
            if results[0]["tail"]:
                print(results[0]["tail"])
            print(f"↻ {a.page} {built_from(sha)}" if results[0]["rc"] == 0 else
                  f"⚠  {a.page} NOT rebuilt (exit {results[0]['rc']}) from {REMOTE}/{BRANCH} {sha[:12]}")
            return results[0]["rc"]
        print("\n".join(report(results, time.monotonic() - t0, sha)))
        if a.all and any(r["rc"] != 0 for r in results):
            return 1
    except Exception as exc:                          # noqa: BLE001 - advisory: say it, never fail the call
        print(f"⚠  pages NOT rebuilt — regen-pages.py could not run ({type(exc).__name__}: {exc}). "
              f"Every generated page may be STALE.")
        return 1 if loud else 0
    return 0


def _self_test() -> int:
    """No generator runs: every launch is a fake. Wrapped per backlog #382's canonical entry."""
    import fixture_git
    global _IN_SUITE
    _IN_SUITE = True
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    import contextlib
    import io
    cases = failures = 0

    def case(name, got, want):
        nonlocal cases, failures
        cases += 1
        if got != want:
            failures += 1
            print(f"  [FAIL] {name}\n    got:  {got!r}\n    want: {want!r}")

    table = {"dashboard": "gen-dashboard.py", "goal-tree": "goal-tree.py", "goals": "gen-goals-page.py"}
    _SHA = "ab" * 20

    def bash(cmd):
        return {"tool_input": {"command": cmd}}

    case("a merge rebuilds EVERY page", pages_for(bash("gh pr merge 425 --squash"), table),
         ["dashboard", "goal-tree", "goals"])
    case("⛔ a command that is not a merge rebuilds nothing", pages_for(bash("gh pr view 425"), table), [])
    # Z3: every input rounds 2 and 3 raised, with the verdict the substring test gives and why.
    case("⭐ Z3: real merges FIRE, however the shell around them is written",
         [may_merge(c) for c in ("cd x && gh pr merge 5", "a | gh pr merge 2", "ls; gh pr merge 3",
                                 "ls\ngh pr merge 7", "if true; then gh pr merge 433; fi",
                                 "echo '<<EOF'\ngh pr merge 433", 'X="a b" gh pr merge 433',
                                 'gh pr merge 5 --body "a; b && c"', "GH_HOST=x gh pr merge 3")],
         [True] * 9)
    case("⚠ Z3, STATED OVER-FIRE: text that only MENTIONS a merge fires too (one ~18 s rebuild each)",
         [may_merge(c) for c in ('echo "gh pr merge 433"', "# gh pr merge 433", "gh pr merge-base 433",
                                 "echo gh pr merged", 'echo ";" gh pr merge 433', "echo \\; gh pr merge 433",
                                 "false && gh pr merge 433", "true || gh pr merge 433",
                                 "cat <<'EOF'\ngh pr merge 433\nEOF", "cat <<'END DOC'\ngh pr merge 433\nEND DOC",
                                 "ls # then gh pr merge 5")],
         [True] * 11)
    case("an empty command does not fire", may_merge(""), False)
    # W1: a merge followed by a failing command reaches PostToolUseFailure, in the documented shape.
    failed = {"hook_event_name": "PostToolUseFailure", "tool_name": "Bash",
              "tool_input": {"command": "gh pr merge 433; false", "description": "merge"},
              "error": "Exit code 1", "is_interrupt": False}
    case("⭐ W1: a PostToolUseFailure payload for `gh pr merge 433; false` rebuilds every page",
         pages_for(failed, table), ["dashboard", "goal-tree", "goals"])
    case("⛔ W1: a failure payload with no tool_input.command rebuilds nothing",
         [pages_for({"hook_event_name": "PostToolUseFailure", "tool_name": "Bash", "error": "x"}, table),
          pages_for({"hook_event_name": "PostToolUseFailure", "tool_input": {}}, table)], [[], []])
    case("W1: registration is read per event, Bash matcher only",
         registered_events({"hooks": {"PostToolUse": [{"matcher": "Bash", "hooks": [
             {"command": "bash x/run-hook.sh regen-pages.sh"}]}], "PostToolUseFailure": [{"matcher": "Edit",
             "hooks": [{"command": "bash x/run-hook.sh regen-pages.sh"}]}]}}), ["PostToolUse"])
    # ⚠ The real settings are read wherever `.claude/settings.json` exists — the repository, and CI. The
    # mutation harness stages `.claude/hooks/` but not settings.json, and only there is this case not run
    # (said on stdout). A MISSING settings.json in the real repository is refused by check-hook-commands
    # (CANNOT RUN), so a deleted file cannot pass for a registered one; a deleted ENTRY reddens this case.
    _settings = ROOT / ".claude" / "settings.json"
    if _settings.is_file():
        try:
            _real = registered_events(json.loads(_settings.read_text()))
        except (OSError, ValueError) as exc:
            _real = f"CANNOT RUN — {exc}"
        case("⭐ W1: the REAL settings.json registers the runner under BOTH events", _real, sorted(EVENTS))
    else:
        print("  NOT RUN (no .claude/settings.json in this tree): the real-settings registration case")
    case("⚠ Z3, STATED MISS: a merge spelled without the text `gh pr merge` does not fire",
         [may_merge(c) for c in ('"gh" pr merge 5', "gh  pr merge 1", 'eval "gh pr $verb 5"')],
         [False, False, False])
    case("an edit of the threads file rebuilds the goal tree alone",
         pages_for({"tool_input": {"file_path": "/x/y/docs/goal-threads.md"}}, table), ["goal-tree"])
    case("...also when the path is repo-relative",
         pages_for({"tool_input": {"file_path": "docs/goal-threads.md"}}, table), ["goal-tree"])
    case("⛔ another file named goal-threads.md elsewhere does not",
         pages_for({"tool_input": {"file_path": "/x/mydocs/goal-threads.md"}}, table), [])
    case("⛔ a payload that is not a dict rebuilds nothing", pages_for(["gh pr merge"], table), [])
    case("a threads edit rebuilds nothing when no goal-tree page is registered",
         pages_for({"tool_input": {"file_path": "docs/goal-threads.md"}}, {"dashboard": "d.py"}), [])
    case("⛔ a tool_input that is not a dict rebuilds nothing",
         pages_for({"tool_input": "gh pr merge 1"}, table), [])

    calls = []

    def fake(script, timeout, tree):
        calls.append((script, timeout, tree))
        if script == "gen-dashboard.py":
            return 1, "boom\nlast line"
        if script == "gen-goals-page.py":
            raise OSError("no such interpreter")
        if script == "goal-tree.py":
            return 124, "timed out after 120s"
        return 0, ""
    res = regen(["dashboard", "goal-tree", "goals"], table, fake, timeout=7, tree=pathlib.Path("/fresh/t"))
    case("⭐ one failing, one hung and one crashing generator: EVERY page is still attempted",
         sorted(c[0] for c in calls), ["gen-dashboard.py", "gen-goals-page.py", "goal-tree.py"])
    case("each generator gets its OWN timeout", sorted({c[1] for c in calls}), [7])
    case("⭐ backlog #408: every generator is handed the FRESH tree, never this checkout",
         sorted({str(c[2]) for c in calls}), ["/fresh/t"])
    case("results come back in the order asked, each with its exit code",
         [(r["page"], r["rc"]) for r in res], [("dashboard", 1), ("goal-tree", 124), ("goals", -1)])
    case("a generator that raises is a named failure, not an exception",
         res[2]["tail"], "OSError: no such interpreter")
    lines = report(res, 3.2)
    case("the report counts what rebuilt and times every page",
         lines[0].startswith("↻ pages rebuilt: 0 of 3 in 3.2s (dashboard "), True)
    case("⛔ every failure is NAMED with its exit code, and says the page is stale",
         [ln.split(" — ")[0] for ln in lines[1:]],
         ["⚠  dashboard NOT rebuilt (exit 1)", "⚠  goal-tree NOT rebuilt (exit 124)",
          "⚠  goals NOT rebuilt (exit -1)"])
    case("the report names the commit it was built from when it knows one, and nothing when it does not",
         [report(res, 1.0, _SHA)[0].endswith(f" — built from origin/master {_SHA[:12]}"),
          " — built from" in report(res, 1.0)[0]], [True, False])
    case("a clean run reports no failure line",
         report(regen(["x"], {"x": "x.py"}, lambda s, t, w: (0, "")), 0.1)[1:], [])
    case("nothing to rebuild launches nothing", regen([], table, fake), [])

    @contextlib.contextmanager
    def fake_tree():
        yield pathlib.Path("/fresh/t"), _SHA

    def drive(argv, stdin_text, run=fake, pages=table, tree_for=fake_tree):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(argv, stdin=io.StringIO(stdin_text), run=run, pages=pages, tree_for=tree_for)
        return rc, buf.getvalue()
    rc, said = drive(["--hook"], json.dumps(bash("gh pr merge 9")))
    case("⛔ --hook exits 0 even when every generator failed, and the report reaches stdout",
         (rc, "NOT rebuilt" in said), (0, True))
    case("--hook on an unrelated command is silent and launches nothing",
         drive(["--hook"], json.dumps(bash("ls")), run=lambda s, t, w: 1 / 0), (0, ""))
    case("⛔ --hook on garbage stdin exits 0 and launches nothing",
         drive(["--hook"], "not json", run=lambda s, t, w: 1 / 0), (0, ""))
    rc_f, said_f = drive(["--hook"], json.dumps({"hook_event_name": "PostToolUseFailure", "error": "x"}),
                         run=lambda s, t, w: 1 / 0)
    case("⛔ W1: W1: --hook on a failure payload with no command exits 0 silently", (rc_f, said_f), (0, ""))

    class Broken(dict):
        def __iter__(self):
            raise RuntimeError("table unreadable")
    rc, said = drive(["--hook"], json.dumps(bash("gh pr merge 9")), pages=Broken(a="a.py"))
    case("⛔ --hook that cannot run at all still exits 0, and SAYS the pages may be stale",
         (rc, "may be STALE" in said), (0, True))
    case("--all exits 1 when a page did not rebuild (it is a command, not a hook)",
         drive(["--all"], "", pages={"dashboard": "gen-dashboard.py"})[0], 1)
    with contextlib.redirect_stdout(io.StringIO()) as _quiet:
        rc_ok = main(["--all"], stdin=io.StringIO(""), run=lambda s, t, w: (0, ""), pages={"x": "x.py"},
                     tree_for=fake_tree)
    case("--all exits 0 when every page rebuilt, and reports it",
         (rc_ok, _quiet.getvalue().startswith("↻ pages rebuilt: 1 of 1")), (0, True))
    case("the real page table is the server's REGENERABLE, goal tree and dashboard included",
         {"goal-tree", "dashboard", "backlog-table", "features", "goals"} <= set(regenerable()), True)

    # ── backlog #408: every page is built from a FRESH origin/master, never this checkout ──────────────
    import tempfile
    tmp = pathlib.Path(os.path.realpath(tempfile.mkdtemp(prefix="regen-fresh-")))
    main_dir = tmp / "main"
    (main_dir / ".git").mkdir(parents=True)
    common = main_dir / ".git"
    tree = main_dir / TREE_REL
    SAFE_IN_MAIN = {"fetch", "rev-parse", "worktree"}
    in_main: set[str] = set()

    def fake_git(*, fetch_rc=0, sha=_SHA, head=None, dirty="", top=None, tree_common=None, m=None):
        calls = []
        m = m or main_dir
        common, tree = m / ".git", m / TREE_REL

        def g(args, cwd, timeout=0):
            cwd = pathlib.Path(cwd)
            calls.append((tuple(args), cwd))
            if cwd == m:
                in_main.add(args[0])
            if args[0] == "fetch":
                return fetch_rc, "" if fetch_rc == 0 else "fatal: unable to access origin"
            if args[:2] == ["rev-parse", "--verify"]:
                return (0, sha) if sha else (1, "")
            if "--git-common-dir" in args:
                return 0, str(common if cwd == m else (tree_common or common))
            if "--show-toplevel" in args:
                return 0, str(top or cwd)
            if args[:2] == ["worktree", "add"]:
                tree.mkdir(parents=True, exist_ok=True)
                (tree / ".git").write_text(f"gitdir: {common}/worktrees/regen-tree\n")
                return 0, ""
            if args[:2] == ["rev-parse", "HEAD"]:
                return 0, head or sha
            if args[0] == "status":
                return 0, dirty
            return 0, ""
        g.calls = calls
        return g

    def outcome(fn):
        try:
            return ("ok", fn())
        except CannotRun as exc:
            return ("CANNOT RUN", str(exc))

    def verbs(g):
        return [" ".join(a[:2]) for a, _ in g.calls]

    def reset_tree():
        import shutil
        shutil.rmtree(tree, ignore_errors=True)

    reset_tree()
    g0 = fake_git()
    got = outcome(lambda: materialise(main_dir, common, g0))
    case("⭐ backlog #408: no tree yet — fetch, then `worktree add --detach` of origin/master's sha",
         (got, [a for a, c in g0.calls if a[:2] == ("worktree", "add")]),
         (("ok", (tree, _SHA)), [("worktree", "add", "--quiet", "--detach", "--force", str(tree), _SHA)]))
    case("...and the fetch comes FIRST, before anything resolves origin/master",
         verbs(g0)[:2], ["fetch --quiet", "rev-parse --verify"])
    g1 = fake_git()
    case("an existing own tree is MOVED in place: checkout --detach --force <sha>, then clean, both IN the tree",
         (outcome(lambda: materialise(main_dir, common, g1))[0],
          [(a, c) for a, c in g1.calls if a[0] in ("checkout", "clean")]),
         ("ok", [(("checkout", "--quiet", "--detach", "--force", _SHA), tree), (("clean", "-fdq"), tree)]))
    g2 = fake_git(fetch_rc=128)
    got = outcome(lambda: materialise(main_dir, common, g2))
    case("⛔ a failed fetch is CANNOT RUN, and nothing after it runs (no stale-tree fallback)",
         (got[0], "git fetch origin master" in got[1], verbs(g2)), ("CANNOT RUN", True, ["fetch --quiet"]))
    g3 = fake_git(sha="")
    case("⛔ origin/master that does not resolve is CANNOT RUN, before any tree is touched",
         (outcome(lambda: materialise(main_dir, common, g3))[0],
          [v for v in verbs(g3) if v.split()[0] in ("worktree", "checkout", "clean")]), ("CANNOT RUN", []))
    (tree / ".git").unlink()
    g4 = fake_git()
    got = outcome(lambda: materialise(main_dir, common, g4))
    case("⛔⛔ a tree path that is a PLAIN directory is refused, and NO checkout or clean runs at all",
         (got[0], "no .git FILE" in got[1], [v for v in verbs(g4) if v.split()[0] in ("checkout", "clean")]),
         ("CANNOT RUN", True, []))
    (tree / ".git").write_text("gitdir: x\n")
    g5 = fake_git(top=main_dir)
    case("⛔⛔ a tree whose top level git reads as the MAIN checkout is refused before checkout --force",
         (outcome(lambda: materialise(main_dir, common, g5))[0],
          [v for v in verbs(g5) if v.split()[0] in ("checkout", "clean")]), ("CANNOT RUN", []))
    g6 = fake_git(tree_common=tmp / "other" / ".git")
    case("⛔ a tree that belongs to ANOTHER repository is refused",
         outcome(lambda: materialise(main_dir, common, g6))[0], "CANNOT RUN")
    g7 = fake_git(head="cd" * 20)
    got = outcome(lambda: materialise(main_dir, common, g7))
    case("⛔ a tree that reads back a different HEAD is CANNOT RUN — never built from",
         (got[0], "reads back HEAD" in got[1]), ("CANNOT RUN", True))
    g8 = fake_git(dirty=" M docs/backlog.md")
    got = outcome(lambda: materialise(main_dir, common, g8))
    case("⛔ a tree that is not clean after the checkout is CANNOT RUN",
         (got[0], "not clean" in got[1]), ("CANNOT RUN", True))
    main2 = tmp / "second"
    (main2 / ".git").mkdir(parents=True)
    g9 = fake_git(m=main2)
    case("the tree is placed under the main checkout it is GIVEN, and its common dir is the one checked",
         (outcome(lambda: materialise(main2, main2 / ".git", g9)),
          outcome(lambda: materialise(main2, common, fake_git(m=main2)))[0]),
         (("ok", (main2 / TREE_REL, _SHA)), "CANNOT RUN"))
    case("⛔⛔ across every scenario above, the ONLY git verbs run in the main checkout are fetch, rev-parse, worktree",
         sorted(in_main), sorted(SAFE_IN_MAIN))
    case("main_of names the main checkout from the common dir; a relative answer is CANNOT RUN",
         [outcome(lambda: main_of(tree, lambda a, c, t=0: (0, str(common)))),
          outcome(lambda: main_of(tree, lambda a, c, t=0: (0, "rel/.git")))[0]],
         [("ok", (main_dir, common)), "CANNOT RUN"])
    _saved = dict(os.environ)
    os.environ.update(GIT_DIR="/elsewhere/.git", GIT_WORK_TREE="/elsewhere", GIT_CONFIG_NOSYSTEM="1")
    try:
        _e = _env()
    finally:
        os.environ.clear()
        os.environ.update(_saved)
    case("an inherited GIT_DIR / GIT_WORK_TREE is DROPPED for git and the generators; config vars pass",
         ("GIT_DIR" in _e, "GIT_WORK_TREE" in _e, _e.get("GIT_CONFIG_NOSYSTEM")), (False, False, "1"))

    def try_lock(wait):
        with tree_lock(main_dir, wait=wait):
            return "entered"
    with tree_lock(main_dir, wait=5):
        got = outcome(lambda: try_lock(0.3))
    case("⛔ a second rebuild while the first holds the lock waits, then says CANNOT RUN",
         (got[0], "held" in str(got[1])), ("CANNOT RUN", True))
    case("...and the lock is free again once the first is done", outcome(lambda: try_lock(0.3)), ("ok", "entered"))
    with tree_lock(main_dir, wait=5):
        with tree_lock(main2, wait=0.3):
            _other = "entered"
    case("the lock is per main checkout: another repository's rebuild is not held up", _other, "entered")

    # The generator runs OUT OF the tree, with the tree as its cwd — a real child, a two-line script.
    (tmp / "gt" / "scripts").mkdir(parents=True)
    (tmp / "gt" / "scripts" / "g.py").write_text(
        "import os, sys\nprint(os.path.realpath(__file__)); print(os.path.realpath(os.getcwd()))\n"
        "print('to stderr', file=sys.stderr); sys.exit(3)\n")
    rc_l, out_l = launch("g.py", 30, tmp / "gt")
    case("⭐ launch runs <tree>/scripts/<generator> with cwd=<tree>, stdout then stderr, its own exit code",
         (rc_l, out_l.splitlines()),
         (3, [os.path.realpath(tmp / "gt" / "scripts" / "g.py"), os.path.realpath(tmp / "gt"), "to stderr"]))

    (tmp / "gt2" / "scripts").mkdir(parents=True)
    (tmp / "gt2" / "scripts" / "slow.py").write_text("import time\ntime.sleep(30)\n")
    case("launch kills a generator at ITS timeout and says so (124)",
         launch("slow.py", 0.5, tmp / "gt2"), (124, "timed out after 0s"))

    @contextlib.contextmanager
    def no_tree():
        raise CannotRun("`git fetch origin master` failed (exit 128: offline)")
        yield
    seen: list = []

    def rec(s, t, w):
        seen.append(w)
        return 0, "⚠  WITHOUT the Ask tray\n   missing token: x\nwrote /x"
    rc_h, said_h = drive(["--hook"], json.dumps(bash("gh pr merge 9")), run=rec, tree_for=no_tree)
    case("⛔ backlog #408: --hook with no fresh tree exits 0, says CANNOT RUN, and runs NO generator",
         (rc_h, "CANNOT RUN — pages NOT rebuilt" in said_h, "offline" in said_h, seen), (0, True, True, []))
    case("⛔ ...--all and --page with no fresh tree exit 2 (a command: CANNOT RUN is a failure, never a pass)",
         [drive(["--all"], "", run=rec, tree_for=no_tree)[0],
          drive(["--page", "goals"], "", run=rec, tree_for=no_tree)[0], seen], [2, 2, []])
    rc_a, said_a = drive(["--all"], "", run=rec)
    case("--all hands the fresh tree to every generator and names the commit it was built from",
         (rc_a, sorted({str(w) for w in seen}), f"built from origin/master {_SHA[:12]}" in said_a),
         (0, ["/fresh/t"], True))
    rc_p, said_p = drive(["--page", "goals"], "", run=rec)
    case("--page prints the generator's own output (its ⚠ lines intact) and the commit, with its exit code",
         (rc_p, said_p.splitlines()),
         (0, ["⚠  WITHOUT the Ask tray", "   missing token: x", "wrote /x",
              f"↻ goals built from origin/master {_SHA[:12]}"]))
    rc_pf, said_pf = drive(["--page", "dashboard"], "")
    case("--page returns a failed generator's exit code and says NOT rebuilt",
         (rc_pf, said_pf.splitlines()[-1].startswith("⚠  dashboard NOT rebuilt (exit 1)")), (1, True))
    rc_u, said_u = drive(["--page", "gen-goals-page.py"], "", run=rec)
    case("--page refuses a name that is not a page KEY, naming the legal set",
         (rc_u, "goal-tree" in said_u), (2, True))

    case("⛔ the suite refuses to materialise THIS repository, whatever a case passes for tree_for",
         (outcome(lambda: _fresh_once(ROOT))[0], drive(["--all"], "", run=rec, tree_for=fresh)[0]), ("CANNOT RUN", 2))

    # ⭐ THE REAL THING, against real git: a bare origin, a main clone with an UNCOMMITTED edit, master
    # moving on twice. The tree follows origin/master; the main checkout's HEAD and edit are untouched.
    def sh(*a, cwd=tmp):
        r = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "init.defaultBranch=master",
                            *a], cwd=cwd, capture_output=True, text=True, env=_env())
        return r.stdout.strip() if r.returncode == 0 else f"ERR {r.returncode}: {r.stderr.strip()}"
    sh("init", "--bare", "-q", "origin.git")
    sh("clone", "-q", "origin.git", "seed")
    seed, real_main = tmp / "seed", tmp / "realmain"
    (seed / "page.txt").write_text("v1\n")
    sh("add", "page.txt", cwd=seed); sh("commit", "-qm", "v1", cwd=seed); sh("push", "-q", "origin", "HEAD:master", cwd=seed)
    sh("clone", "-q", "origin.git", "realmain")
    (real_main / ".gitignore").write_text(".claude/\n")
    (real_main / "page.txt").write_text("v1 + an UNCOMMITTED owner edit\n")
    main_head = sh("rev-parse", "HEAD", cwd=real_main)
    (seed / "page.txt").write_text("v2\n")
    sh("commit", "-qam", "v2", cwd=seed); sh("push", "-q", "origin", "HEAD:master", cwd=seed)
    v2 = sh("rev-parse", "HEAD", cwd=seed)
    r1 = outcome(lambda: _fresh_once(real_main))
    rt = real_main / TREE_REL
    case("⭐⭐ REAL git: the tree is origin/master AFTER a fetch, though the main checkout never moved",
         (r1, (rt / "page.txt").read_text() if rt.is_dir() else "no tree"), (("ok", (rt, v2)), "v2\n"))
    (seed / "page.txt").write_text("v3\n")
    sh("commit", "-qam", "v3", cwd=seed); sh("push", "-q", "origin", "HEAD:master", cwd=seed)
    v3 = sh("rev-parse", "HEAD", cwd=seed)
    (rt / "page.txt").write_text("a generator scribbled here\n")
    r2 = outcome(lambda: _fresh_once(real_main))
    case("⭐⭐ REAL git: the next rebuild MOVES the same tree to the new master, discarding scribbles in it",
         (r2, (rt / "page.txt").read_text()), (("ok", (rt, v3)), "v3\n"))
    case("⛔⛔ REAL git: the main checkout's HEAD and its uncommitted edit are exactly as they were",
         (sh("rev-parse", "HEAD", cwd=real_main) == main_head, (real_main / "page.txt").read_text(),
          sh("status", "--porcelain", "--untracked-files=no", cwd=real_main)),
         (True, "v1 + an UNCOMMITTED owner edit\n", "M page.txt"))
    sh("worktree", "add", "-q", "--detach", str(tmp / "linked"), cwd=real_main)
    with fresh(tmp / "linked", wait=2) as r_l:
        pass
    case("⭐ REAL git: run from a LINKED worktree, the tree is still the MAIN checkout's, at origin/master",
         (r_l, outcome(lambda: main_of(tmp / "linked"))), ((rt, v3), ("ok", (real_main, real_main / ".git"))))
    busy_calls: list = []

    def only_names_main(args, cwd, timeout=GIT_TIMEOUT):
        busy_calls.append(args[:2])
        return _git(args, cwd, timeout) if "--git-common-dir" in args else (1, "must not run")
    with tree_lock(real_main, wait=5):
        r_busy = outcome(lambda: fresh(real_main, git=only_names_main, wait=0.3).__enter__())
    case("⛔ REAL lock: fresh() waits for a running rebuild's lock and says CANNOT RUN; only main_of ran git",
         (r_busy[0], "held" in str(r_busy[1]), busy_calls), ("CANNOT RUN", True, [["rev-parse", "--path-format=absolute"]]))
    sh("remote", "set-url", "origin", str(tmp / "gone.git"), cwd=real_main)
    r3 = outcome(lambda: _fresh_once(real_main))
    case("⛔ REAL git: an unreachable origin is CANNOT RUN, not a build from the tree already there",
         (r3[0], "git fetch" in r3[1]), ("CANNOT RUN", True))
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
