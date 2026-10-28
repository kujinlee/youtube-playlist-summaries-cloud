#!/usr/bin/env python3
"""Rebuild every generated page after a command that MAY merge a PR, so no page describes a world that has moved on.

    python3 scripts/regen-pages.py --hook < payload.json   # what .claude/hooks/regen-pages.sh runs
    python3 scripts/regen-pages.py --all                   # every page, now
    python3 scripts/regen-pages.py --self-test             # 40 cases

WHY (owner decision D3, 2026-10-28, backlog #363). A merge moves the state every generated page reads —
the dashboard's PR list, the backlog's closed rows, the goals and features maps, the goal tree's leaves —
and before this only the goal tree was rebuilt on one. The others went stale until someone edited their
source file or pressed Refresh.

THE TRIGGER IS A STATIC MATCH (round 2 Y5): a Bash command in which `gh pr merge` appears as a command's
first words after a quote-aware split (`commands`, `may_merge`). It never claims the merge RAN: `false && gh
pr merge 1` over-fires (one needless rebuild), and a merge inside syntax it does not model may be missed —
the page's build time shows the staleness either way.

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
import shlex
import subprocess
import sys
import time

SCRIPTS = pathlib.Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
TIMEOUT = 120          # seconds, per generator; the slowest measured 2026-10-28 was gen-backlog-page, 17s
THREADS_REL = "docs/goal-threads.md"
SEPARATORS = ";&|()\n"
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
# Words that may precede a command inside compound syntax: `if true; then gh pr merge 1; fi`.
LEADERS = frozenset({"if", "then", "else", "elif", "do", "while", "until", "!", "{", "time"})
HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")


def _strip_heredocs(cmd: str) -> str:
    """The command text with every here-document BODY removed: a body is data, never a command."""
    out, delims = [], []
    for line in cmd.split("\n"):
        if delims:
            if line.strip() == delims[0]:
                delims.pop(0)
            continue
        out.append(line)
        delims += [m.group(2) for m in HEREDOC.finditer(line)]
    return "\n".join(out)


def _word(token: str) -> str:
    """A token with ONE layer of matching outer quotes removed (`"gh"` is the word gh)."""
    return token[1:-1] if len(token) >= 2 and token[0] == token[-1] and token[0] in "'\"" else token


def commands(cmd: str) -> list[list[str]]:
    """PURE. A STATIC reading of the simple commands in a Bash string, each as its argv words.

    Here-document bodies are dropped; the rest is tokenized by `shlex` in non-POSIX mode, which keeps a
    quoted token whole — so a quoted `";"` or `"gh pr merge 1"` stays text (round 2 Y5) — and honours `#`
    comments; it is split on UNQUOTED `;` `&&` `||` `|` `&`, parentheses and newlines. Leading `NAME=value`
    assignments and compound-syntax words (`if`, `then`, `do`, `!`, …) are dropped.

    ⚠ IT DOES NOT KNOW WHAT RUNS, and says so: `false && gh pr merge 1` reads as a merge though bash never
    runs it (an OVER-FIRE: one needless rebuild). It MAY MISS a merge inside syntax it does not model —
    a `case` arm, a function body, `bash -c '…'`, `eval`, `$(…)` — and unbalanced quotes yield no commands
    (a missed rebuild; the page's build time shows how stale it is). shlex reads `a#b` as a comment where
    bash reads one word, which can only hide a merge."""
    try:
        lex = shlex.shlex(_strip_heredocs(cmd), posix=False, punctuation_chars=SEPARATORS)
        lex.whitespace = " \t\r"
        lex.whitespace_split = True
        tokens = list(lex)
    except ValueError:
        return []
    out: list[list[str]] = [[]]
    for t in tokens:
        if t and set(t) <= set(SEPARATORS):
            out.append([])
        elif out[-1] or not (ASSIGNMENT.match(t) or t in LEADERS):
            out[-1].append(_word(t))
    return [c for c in out if c]


def may_merge(cmd: str) -> bool:
    """PURE. Is this Bash string a command that MAY merge a PR — does some command in `commands()` begin
    with exactly the words `gh`, `pr`, `merge`? A static match, not an observation of execution: see
    `commands()` for what it over- and under-reads. A false fire costs one rebuild."""
    return any(c[:3] == ["gh", "pr", "merge"] for c in commands(cmd))


def regenerable() -> dict[str, str]:
    """The page -> generator map the server's Refresh button uses. Imported, never copied."""
    spec = importlib.util.spec_from_file_location("_explainer_serve", SCRIPTS / "explainer-serve.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return dict(mod.REGENERABLE)


def pages_for(payload: object, pages: dict[str, str]) -> list[str]:
    """PURE. Which pages a PostToolUse payload asks to rebuild: all of them after `gh pr merge`, the goal
    tree alone after an edit of the threads file, nothing otherwise (including a payload that is not one)."""
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
    case("...also inside a compound command, after a cd",
         pages_for(bash("cd x && gh  pr merge 1"), table), ["dashboard", "goal-tree", "goals"])
    case("⛔ a command that is not a merge rebuilds nothing", pages_for(bash("gh pr view 425"), table), [])
    case("⛔ `gh pr merged` is not `gh pr merge`", pages_for(bash("echo gh pr merged"), table), [])
    case("⛔ X3: a QUOTED merge is text, not a command", pages_for(bash('echo "gh pr merge 433"'), table), [])
    case("⛔ X3: a COMMENTED merge is not executed", pages_for(bash("# gh pr merge 433"), table), [])
    case("⛔ X3: `gh pr merge-base` is not `gh pr merge`", pages_for(bash("gh pr merge-base 433"), table), [])
    case("⛔ X3: a merge mentioned AFTER a comment marker is not executed",
         pages_for(bash("ls # then gh pr merge 5"), table), [])
    case("X3: a compound `cd x && gh pr merge 5` IS a merge", may_merge("cd x && gh pr merge 5"), True)
    case("X3: after a pipe, a semicolon or a newline it is still a merge",
         [may_merge(c) for c in ("a | gh pr merge 2", "ls; gh pr merge 3", "ls\ngh pr merge 7")],
         [True, True, True])
    case("X3: separators INSIDE a quoted argument do not split the command",
         commands('gh pr merge 5 --body "a; b && c"'), [["gh", "pr", "merge", "5", "--body", "a; b && c"]])
    case("X3: a leading NAME=value assignment is not the command name",
         commands("GH_HOST=x gh pr merge 3"), [["gh", "pr", "merge", "3"]])
    case("⛔ Y5: a QUOTED separator is text, so `echo \";\" gh pr merge` is one echo",
         may_merge('echo ";" gh pr merge 433'), False)
    case("⛔ Y5: a here-document BODY is data, never a command",
         may_merge("cat <<'EOF'\ngh pr merge 433\nEOF"), False)
    case("...and the command after the here-document is still read",
         may_merge("cat <<EOF\nhi\nEOF\ngh pr merge 9"), True)
    case("Y5: a merge inside `if … then … fi` is seen", may_merge("if true; then gh pr merge 433; fi"), True)
    case("Y5: a quoted command word is still the word (`\"gh\" pr merge`)", may_merge('"gh" pr merge 5'), True)
    case("⚠ Y5, STATED OVER-FIRE: `false && gh pr merge` reads as a merge — the match is static",
         [may_merge(c) for c in ("false && gh pr merge 433", "true || gh pr merge 433")], [True, True])
    case("⛔ X3: unbalanced quotes yield no command — a missed rebuild, never a spurious one",
         commands('gh pr merge 5 --body "oops'), [])
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
