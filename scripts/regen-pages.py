#!/usr/bin/env python3
"""Rebuild every generated page after a command that MAY merge a PR, so no page describes a world that has moved on.

    python3 scripts/regen-pages.py --hook < payload.json   # what .claude/hooks/regen-pages.sh runs
    python3 scripts/regen-pages.py --all                   # every page, now
    python3 scripts/regen-pages.py --self-test             # 32 cases

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

EXIT CODES: `--hook` is always 0. `--all` is 0 when every page rebuilt, 1 when any did not.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import importlib.util
import json
import pathlib
import re
import subprocess
import sys
import time

SCRIPTS = pathlib.Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
TIMEOUT = 120          # seconds, per generator; the slowest measured 2026-10-28 was gen-backlog-page, 17s
THREADS_REL = "docs/goal-threads.md"
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


def launch(script: str, timeout: float) -> tuple[int, str]:
    """Run one generator. (rc, the tail of its output); 124 with a sentence when it timed out."""
    try:
        r = subprocess.run([sys.executable, str(SCRIPTS / script)], cwd=ROOT, capture_output=True,
                           text=True, timeout=timeout, stdin=subprocess.DEVNULL, errors="replace")
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout:.0f}s"
    return r.returncode, (r.stderr or r.stdout or "").strip()[-300:]


def regen(names: list[str], pages: dict[str, str], run=launch, timeout: float = TIMEOUT) -> list[dict]:
    """Run each page's generator concurrently. One result per page, in `names` order. NEVER RAISES: a
    generator that raises is a failed result like any other, and the rest still run."""
    def one(name):
        t0 = time.monotonic()
        try:
            rc, tail = run(pages[name], timeout)
        except Exception as exc:                      # noqa: BLE001 - named in the report, never swallowed
            rc, tail = -1, f"{type(exc).__name__}: {exc}"
        return {"page": name, "rc": rc, "secs": round(time.monotonic() - t0, 1), "tail": tail}
    if not names:
        return []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(names)) as pool:
        return list(pool.map(one, names))


def report(results: list[dict], wall: float) -> list[str]:
    """PURE. One summary line, then one line per page that did NOT rebuild."""
    ok = [r for r in results if r["rc"] == 0]
    bad = [r for r in results if r["rc"] != 0]
    out = [f"↻ pages rebuilt: {len(ok)} of {len(results)} in {wall:.1f}s ("
           + ", ".join(f"{r['page']} {r['secs']}s" for r in results) + ")"]
    out += [f"⚠  {r['page']} NOT rebuilt (exit {r['rc']}) — its page is STALE: "
            + " ".join(r["tail"].split())[-200:] for r in bad]
    return out


def main(argv: list[str] | None = None, *, stdin=None, run=launch, pages=None) -> int:
    ap = argparse.ArgumentParser(description="Rebuild every generated page (owner decision D3).")
    ap.add_argument("--hook", action="store_true", help="read a PostToolUse payload on stdin")
    ap.add_argument("--all", action="store_true", help="rebuild every page now")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(sys.argv[1:] if argv is None else argv)
    if a.self_test:
        return _self_test()
    try:
        table = pages if pages is not None else regenerable()
        if a.all:
            names = sorted(table)
        else:
            try:
                payload = json.loads((stdin or sys.stdin).read())
            except ValueError:
                payload = None
            names = pages_for(payload, table)
        if not names:
            return 0
        t0 = time.monotonic()
        results = regen(names, table, run)
        print("\n".join(report(results, time.monotonic() - t0)))
        if a.all and any(r["rc"] != 0 for r in results):
            return 1
    except Exception as exc:                          # noqa: BLE001 - advisory: say it, never fail the call
        print(f"⚠  pages NOT rebuilt — regen-pages.py could not run ({type(exc).__name__}: {exc}). "
              f"Every generated page may be STALE.")
        return 1 if a.all else 0
    return 0


def _self_test() -> int:
    """No generator runs: every launch is a fake. Wrapped per backlog #382's canonical entry."""
    import fixture_git
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

    def fake(script, timeout):
        calls.append((script, timeout))
        if script == "gen-dashboard.py":
            return 1, "boom\nlast line"
        if script == "gen-goals-page.py":
            raise OSError("no such interpreter")
        if script == "goal-tree.py":
            return 124, "timed out after 120s"
        return 0, ""
    res = regen(["dashboard", "goal-tree", "goals"], table, fake, timeout=7)
    case("⭐ one failing, one hung and one crashing generator: EVERY page is still attempted",
         sorted(c[0] for c in calls), ["gen-dashboard.py", "gen-goals-page.py", "goal-tree.py"])
    case("each generator gets its OWN timeout", sorted({c[1] for c in calls}), [7])
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
    case("a clean run reports no failure line",
         report(regen(["x"], {"x": "x.py"}, lambda s, t: (0, "")), 0.1)[1:], [])
    case("nothing to rebuild launches nothing", regen([], table, fake), [])

    def drive(argv, stdin_text, run=fake, pages=table):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(argv, stdin=io.StringIO(stdin_text), run=run, pages=pages)
        return rc, buf.getvalue()
    rc, said = drive(["--hook"], json.dumps(bash("gh pr merge 9")))
    case("⛔ --hook exits 0 even when every generator failed, and the report reaches stdout",
         (rc, "NOT rebuilt" in said), (0, True))
    case("--hook on an unrelated command is silent and launches nothing",
         drive(["--hook"], json.dumps(bash("ls")), run=lambda s, t: 1 / 0), (0, ""))
    case("⛔ --hook on garbage stdin exits 0 and launches nothing",
         drive(["--hook"], "not json", run=lambda s, t: 1 / 0), (0, ""))
    rc_f, said_f = drive(["--hook"], json.dumps({"hook_event_name": "PostToolUseFailure", "error": "x"}),
                         run=lambda s, t: 1 / 0)
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
        rc_ok = main(["--all"], stdin=io.StringIO(""), run=lambda s, t: (0, ""), pages={"x": "x.py"})
    case("--all exits 0 when every page rebuilt, and reports it",
         (rc_ok, _quiet.getvalue().startswith("↻ pages rebuilt: 1 of 1")), (0, True))
    case("the real page table is the server's REGENERABLE, goal tree and dashboard included",
         {"goal-tree", "dashboard", "backlog-table", "features", "goals"} <= set(regenerable()), True)

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
