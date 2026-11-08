#!/usr/bin/env python3
"""Which `push` invocations does a Bash command run? The detection half of the push gate (backlog #428).

`.claude/hooks/block-default-branch-push.sh` refuses a push to the default branch, a bare `--force` / `-f`
or `+<refspec>`, `--no-verify`, and the plan-leak gate's off-switches. Until backlog #428 it decided WHETHER
a command was a push by matching the RAW text, so `git "push" origin master` and `git 'push' origin
HEAD:master` were not seen as pushes and every rule was skipped (a security-review finding, MEDIUM, parser
differential: bash deletes the quotes, the hook did not). This file is that decision, in Python so the
mutation harness can reach it (`check-plan-code.py --mutate` mutates `scripts/<stem>.py` only).

THE RULE — FAIL CLOSED, read from the NORMALISED text, one CHUNK at a time:
  * NORMALISE: a backslash-newline (bash's line continuation) becomes a space, THEN every `"`, `'` and `\\`
    is deleted — the same deletion the hook's rule 3 uses for `hookspath`. `git "push" origin "master"`
    becomes `git push origin master`, and `git push \\<newline> origin master` one line.
  * CHUNKS: the text between `;`, `&`, `|` and line ends. A segment never crosses one.
  * STRICT: a chunk with the WORD `git`, then global options (`-c`/`-C`/`--config-env`/`--git-dir`/
    `--work-tree`/`--namespace`/`--exec-path` take a separate value; any other `-flag` stands alone), then
    the word `push`. Scanned token by token, right to left, in ONE pass — never a regex with nested
    repetition (PR #542 round 1: `'-c ' * 60` before a failed match backtracked past any deadline).
  * NOT A PUSH: a chunk whose first git word is a bare `git` running `commit` or `stash`, with no further
    git word after that subcommand. Its `push` words are that command's arguments (`git stash push`,
    `git commit -m "push …"`). Any later git word (`$(git push …)`) voids this.
  * LOOSE (the fail-closed layer): any other chunk with a `push` word.
  THE MODE: `strict` if any chunk is STRICT. Its segments are the STRICT pushes plus every push word in a
  loose chunk that ALSO holds a git word (`/usr/bin/git push`, `git -C "my dir" push`); a push word in a
  chunk with no git word (`gh pr create --title "Do not push to master"`) is text, not a push. Otherwise
  `loose` if the word `git` appears anywhere: every loose push word is a segment. Otherwise `none`.
  A segment is `push` and the rest of its chunk, with REDIRECTIONS removed (`>f`, `2>`, `> f`, and the
  refspec part of `master>/dev/null`), since bash never passes them to git.
  ⏱ A DEADLINE: `segments` arms SIGALRM at `DEADLINE_S` with the DEFAULT action, so a run that stalls —
  even inside C code — is killed (the hook sees exit 142 and REFUSES, saying so). Never a pass.

⚠ THE BOUND, SAID PLAINLY — A HARMLESS COMMAND CAN BE REFUSED. Measured by `--self-test`, over a fixture
repository whose default branch is master:
  * on the DEFAULT branch, a LOOSE segment with fewer than two plain arguments reads as `git push
    [<remote>]`, which pushes the current branch: `git log --grep push`, `echo "git push later"` and
    `echo push; git status` are REFUSED;
  * on ANY branch, text that reads `push <x> <default-branch>` in a loose or strict chunk is REFUSED:
    `gh pr create --title "git push origin master"` (strict once quotes go) and
    `git log --oneline --grep "push to master"` (loose: `log` is not a recognised non-push subcommand);
  * on ANY branch, a push whose arguments keep unresolved shell syntax — `(`, `)`, a backtick, `$(`, `<`,
    `>` after redirections are removed — is REFUSED by the hook, so `(cd x && git push origin feat/x)` is.
  ALLOWED, and measured: `git commit -m "push the fix, not master" && git push origin feat/x`,
  `git stash push -m …` on ANY branch, a feature push followed by `--title "Do not push to master"`, and
  `git push -u origin feat/x 2>&1`. Put other such text in a file (`--body-file`, `git commit -F`).
  A false refusal costs a moment; a false pass costs a push to master. That trade is the rule.

⚠ OUT OF SCOPE, as for rule 3: shell expansions (`$'\\x70ush'`, `${…}`, `$g push` with `g=git` — in STRICT
mode a chunk with no git word is never a segment), an alias or a function that runs git, `git send-pack`
and other plumbing, and destinations set by config or by `--all`/`--mirror` (backlog #574). This reads
command TEXT; it is defence in depth against an ACCIDENT, not a boundary against a determined agent.
The hook is LAUNCHED by `.claude/settings.json`'s `if: Bash(*push*)`, which Claude Code matches against the
command AFTER shell unquoting: MEASURED on 2.1.316 with marker hooks, it fired for `echo git p"u"sh …`,
`echo git pu\\sh …` and `echo pu""sh`, so those forms reach this detector.

WHAT WOULD MAKE THIS FAIL (its falsifier): `git "push" origin master`, `git -c x=y push origin master`,
`git push \\<newline> origin master` or `git 'push' origin HEAD:master`, run through the hook over a
repository whose default branch is master, is allowed; or a feature-branch push is refused.

    python3 scripts/push-command.py segments < command.txt   # mode line, then one `push <args>` per segment
    python3 scripts/push-command.py --self-test  # 64 cases

`segments` prints `none`, `strict` or `loose` on the first line, then one line per segment, each
starting with the word `push` (so a bare `git push` is a non-empty line). Exit 0; 2 on a usage error.
⚡ Only `re` and `sys` load on that path (PR #542 round 1, C-F8): the self-test's imports are lazy.
"""
from __future__ import annotations

import re
import sys

# Under the hook's own timeout, with room for a loaded machine's interpreter start.
DEADLINE_S = 3.0
# The global options that take a SEPARATE value (backlog #393's list). Any other `-flag` stands alone.
VALUE_OPTS = frozenset({"-c", "-C", "--config-env", "--git-dir", "--work-tree", "--namespace",
                        "--exec-path"})
# Subcommands whose `push` arguments are never a push. Builtins cannot be aliased, so the name is the
# command. Kept SHORT on purpose: `rebase --exec`, `submodule foreach` and `bisect run` run commands.
NON_PUSH_SUBCOMMANDS = frozenset({"commit", "stash"})
# A WORD: not glued to a name character, a path or a hyphen, so `.git`, `legit`, `block-…-push.sh`,
# `--push-option` and the branch `push-hook-quoted` are not the words `git` / `push`. `/usr/bin/git` IS.
GIT_WORD = re.compile(r"(?<![\w.-])git(?![\w.-])")
PUSH_WORD = re.compile(r"(?<![\w./-])push(?![\w./-])")
CHUNK_SEP = re.compile(r"[;&|\n]")
TOKEN = re.compile(r"[^ \t]+")
REDIRECT = re.compile(r"[<>]")


def normalize(cmd: str) -> str:
    """Line continuations joined, then every double quote, single quote and backslash deleted."""
    cmd = cmd.replace("\\\n", " ")
    return cmd.translate({ord('"'): None, ord("'"): None, ord("\\"): None})


def _reach(toks: list[str]) -> list[int]:
    """`reach[i]`: the index of the `push` that global options starting at `i` lead to, else -1.

    One right-to-left pass, so a chunk of N tokens costs O(N) however its options nest."""
    n = len(toks)
    reach = [-1] * (n + 2)
    for i in range(n - 1, -1, -1):
        t = toks[i]
        if t == "push":
            reach[i] = i
        elif t in VALUE_OPTS:
            reach[i] = reach[i + 2]
        elif t.startswith("-") and len(t) > 1:
            reach[i] = reach[i + 1]
    return reach


def _strict_pushes(toks: list[str]) -> list[int]:
    """Token indexes of the `push` words that a bare `git` [options] reaches, in order."""
    reach = _reach(toks)
    found = {reach[i + 1] for i, t in enumerate(toks) if t == "git" and reach[i + 1] >= 0}
    return sorted(found)


def _not_a_push(toks: list[str]) -> bool:
    """A chunk run by `git commit` / `git stash` with no later git word: its `push` words are arguments."""
    g = next((i for i, t in enumerate(toks) if GIT_WORD.search(t)), None)
    if g is None or toks[g] != "git":
        return False
    s = g + 1
    while s < len(toks):
        if toks[s] in VALUE_OPTS:
            s += 2
        elif toks[s].startswith("-") and len(toks[s]) > 1:
            s += 1
        else:
            break
    if s >= len(toks) or toks[s] not in NON_PUSH_SUBCOMMANDS:
        return False
    return not any(GIT_WORD.search(t) for t in toks[s + 1:])


def _drop_redirections(rest: str) -> str:
    """The arguments bash passes on: `>f`, `2>`, `> f` removed; `master>/dev/null` keeps `master`."""
    out: list[str] = []
    skip_target = False
    for tok in rest.split():
        if skip_target:
            skip_target = False
            continue
        m = REDIRECT.search(tok)
        if not m:
            out.append(tok)
            continue
        head, tail = tok[:m.start()], tok[m.start():]
        if head and not head.isdigit():
            out.append(head)
        if not tail.strip("<>&"):
            skip_target = True
    return " ".join(out)


def _segment(chunk: str, at: int) -> str:
    """`push` and the rest of its chunk from character `at`, redirections removed."""
    return ("push " + _drop_redirections(chunk[at + 4:])).rstrip()


def segments(cmd: str) -> tuple[str, list[str]]:
    """`(mode, segments)`: mode is `none`, `strict` or `loose`; each segment is `push` and its arguments."""
    norm = normalize(cmd)
    found: list[tuple[str, str]] = []   # (segment, kind): kind is strict, git (loose, a git word) or bare
    for chunk in CHUNK_SEP.split(norm):
        words = list(PUSH_WORD.finditer(chunk))
        if not words:
            continue
        spans = list(TOKEN.finditer(chunk))
        toks = [m.group() for m in spans]
        strict = _strict_pushes(toks)
        if strict:
            found += [(_segment(chunk, spans[i].start()), "strict") for i in strict]
            continue
        if _not_a_push(toks):
            continue
        kind = "git" if GIT_WORD.search(chunk) else "bare"
        found += [(_segment(chunk, w.start()), kind) for w in words]
    if any(k == "strict" for _, k in found):
        return "strict", [s for s, k in found if k != "bare"]
    if GIT_WORD.search(norm) and found:
        return "loose", [s for s, _ in found]
    return "none", []


def _arm_deadline() -> None:
    """SIGALRM with its DEFAULT action at `DEADLINE_S`: the kernel ends a stalled run, even in C code."""
    import signal
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.setitimer(signal.ITIMER_REAL, DEADLINE_S)


def main(argv: list[str]) -> int:
    if argv == ["--self-test"]:
        return self_test()
    if argv != ["segments"]:
        print("usage: push-command.py segments < command  |  --self-test", file=sys.stderr)
        return 2
    _arm_deadline()
    mode, segs = segments(sys.stdin.read())
    print(mode)
    for s in segs:
        print(s)
    return 0


# ── --self-test ─────────────────────────────────────────────────────────────────────────────────────

def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _world(root: Path) -> Path:
    """A clone whose `origin/HEAD` is master, so the hook resolves `master` as the default branch."""
    seed, bare, work = root / "seed", root / "origin.git", root / "work"
    seed.mkdir()
    _git(seed, "init", "-q", "-b", "master")
    _git(seed, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q",
         "--allow-empty", "-m", "seed")
    _git(root, "clone", "-q", "--bare", str(seed), str(bare))
    _git(root, "clone", "-q", str(bare), str(work))
    return work


def _hook(cwd: Path, command: str, hook: Path | None = None, payload: str | None = None) -> tuple[str, str]:
    """`(decision, reason)` from running the delivered hook over the Claude Code stdin contract."""
    if payload is None:
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    r = subprocess.run(["bash", str(hook or HOOK)], cwd=cwd, input=payload, capture_output=True,
                       text=True, timeout=60)
    if not r.stdout.strip():
        return "allow", ""
    out = json.loads(r.stdout)["hookSpecificOutput"]
    return out["permissionDecision"], out["permissionDecisionReason"]


def self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    # The suite's imports load HERE, never on the hook's `segments` path (PR #542 round 1, C-F8).
    global json, subprocess, tempfile, Path, HOOK
    import json
    import subprocess
    import tempfile
    from pathlib import Path
    HOOK = Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "block-default-branch-push.sh"
    ran = failures = 0

    def case(name: str, got, want) -> None:
        nonlocal ran, failures
        ran += 1
        if got == want:
            print(f"[PASS] {name}")
        else:
            failures += 1
            print(f"[FAIL] {name}: got {got!r} want {want!r}")

    # ── the detection, PURE ──
    case("an ordinary push is strict", segments("git push origin feat/x"),
         ("strict", ["push origin feat/x"]))
    case("⭐ a DOUBLE-QUOTED push is strict once quotes are deleted", segments('git "push" origin master'),
         ("strict", ["push origin master"]))
    case("⭐ a SINGLE-QUOTED push is strict too", segments("git 'push' origin HEAD:master"),
         ("strict", ["push origin HEAD:master"]))
    case("a quoted REFSPEC is read without its quotes", segments('git push origin "master"'),
         ("strict", ["push origin master"]))
    case("a backslash does not hide push", segments("git pu\\sh origin master"),
         ("strict", ["push origin master"]))
    case("⭐ -c x=y before push is strict", segments("git -c x=y push origin master"),
         ("strict", ["push origin master"]))
    case("-C dir before push is strict", segments("git -C /r push origin master"),
         ("strict", ["push origin master"]))
    case("a bare flag before push is strict", segments("git --no-pager push origin master"),
         ("strict", ["push origin master"]))
    case("⭐ a PATH to git is LOOSE — strict wants a separator before git",
         segments("/usr/bin/git push origin master"), ("loose", ["push origin master"]))
    case("⭐ an option value with a space is LOOSE", segments('git -C "my dir" push origin master'),
         ("loose", ["push origin master"]))
    case("the control `git log --grep push` is LOOSE, one bare segment", segments("git log --grep push"),
         ("loose", ["push"]))
    case("the control `echo \"git push later\"` is STRICT once its quotes are deleted",
         segments('echo "git push later"'), ("strict", ["push later"]))
    case("a non-push git command is none", segments("git status"), ("none", []))
    case("push without the word git is none", segments("echo push"), ("none", []))
    case("`legit` is not the word git", segments("legit push origin master"), ("none", []))
    case("`.git` is not the word git", segments("ls .git && echo push"), ("none", []))
    # A segment runs to its line end, so a decoy word AFTER a push is inside that segment and never a
    # match of its own. Each decoy below comes BEFORE the push, where an extra bare `push` segment would
    # read as `git push` of the current branch (a false refusal on the default branch).
    case("a branch NAMED push-… is not a segment",
         segments("git checkout push-hook-quoted && git push origin push-hook-quoted"),
         ("strict", ["push origin push-hook-quoted"]))
    case("a hyphenated word ending -push is not a segment",
         segments("git checkout fix-push && git push origin fix-push"),
         ("strict", ["push origin fix-push"]))
    case("a path ending /push is not a segment",
         segments("git checkout feat/push && git push origin feat/push"),
         ("strict", ["push origin feat/push"]))
    case("a segment stops at a separator", segments("git push origin feat/x; echo master"),
         ("strict", ["push origin feat/x"]))
    case("a segment stops at a line end", segments("git push origin feat/x\necho master"),
         ("strict", ["push origin feat/x"]))
    case("every push in a compound command is a segment",
         segments("git push origin feat/x && /usr/bin/git push origin master"),
         ("strict", ["push origin feat/x", "push origin master"]))
    case("a bare `git push` is the segment `push`", segments("git push"), ("strict", ["push"]))
    # ── PR #542 round 1 ──
    case("⭐ C-F1: a backslash-newline joins the refspec onto the push line",
         segments("git push \\\n  origin master"), ("strict", ["push origin master"]))
    case("⭐ C-F2: a commit message naming push and master is not a segment beside a real push",
         segments('git commit -m "push the fix, not master" && git push origin feat/x'),
         ("strict", ["push origin feat/x"]))
    case("C-F2: `git stash push` is never a push", segments('git stash push -m "before master merge"'),
         ("none", []))
    case("C-F2: `git stash push -m wip` is never a push", segments("git stash push -m wip"), ("none", []))
    case("C-F2: a push word in a chunk with no git word is text once a real push is recognised",
         segments('git push origin feat/x && gh pr create --title "Do not push to master" --body-file b'),
         ("strict", ["push origin feat/x"]))
    case("C-F2: a git word AFTER `git commit` voids the exemption",
         segments('git commit -m "$(git push origin master)"'), ("loose", ["push origin master)"]))
    case("C-F2: the exemption wants a bare `git` word, not `$(git`",
         segments("echo $(git stash push)"), ("loose", ["push )"]))
    case("C-F2: a stash chunk does not hide a push chunk beside it",
         segments("git stash push -m wip; git push origin master"), ("strict", ["push origin master"]))
    case("a glued redirection leaves the refspec", segments("git push origin master>/dev/null"),
         ("strict", ["push origin master"]))
    case("a separate redirection drops its target", segments("git push origin feat/x > out.log"),
         ("strict", ["push origin feat/x"]))
    case("`2>` before `&1` is not a refspec", segments("git push -u origin feat/x 2>&1"),
         ("strict", ["push -u origin feat/x"]))
    case("`-c` takes its value even when the value is `push`", segments("git -c push origin master"),
         ("loose", ["push origin master"]))

    # ── the CLI contract the hook reads ──
    r = subprocess.run([sys.executable, __file__, "segments"], input="/usr/bin/git push origin master",
                       capture_output=True, text=True)
    case("segments prints the mode, then one line per segment", (r.returncode, r.stdout),
         (0, "loose\npush origin master\n"))
    r = subprocess.run([sys.executable, __file__, "bogus"], capture_output=True, text=True)
    case("an unknown mode is a usage error", r.returncode, 2)
    # X-F1 (Codex's input): `-c ` sixty times before a failed match backtracked past every deadline under
    # the nested-repetition regex. The scan must finish well inside the deadline, with the right answer.
    xf1 = 'echo "git ' + "-c " * 60 + 'x y"; git push origin master'
    xf1_chunk = "git " + "-c " * 60 + "x y push origin master"
    try:
        r = subprocess.run([sys.executable, __file__, "segments"], input=xf1 + "\n" + xf1_chunk,
                           capture_output=True, text=True, timeout=10)
        got = (r.returncode, r.stdout)
    except subprocess.TimeoutExpired:
        got = "TIMED OUT after 10 s"
    case("⭐ X-F1: sixty `-c` before a failed match is scanned inside the deadline", got,
         (0, "strict\npush origin master\npush origin master\n"))
    # The deadline itself: a `segments` run whose stdin never closes stalls, and SIGALRM's DEFAULT action
    # must end it. Without the deadline this waits out the 15 s timeout and reports a stall.
    p = subprocess.Popen([sys.executable, __file__, "segments"], stdin=subprocess.PIPE,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        got = p.wait(timeout=15)
    except subprocess.TimeoutExpired:
        p.kill()
        p.wait()
        got = "STALLED past 15 s"
    finally:
        p.stdin.close()
    import signal
    case("⭐ X-F1: a stalled `segments` run is ended by its own deadline (SIGALRM)", got,
         -signal.SIGALRM)

    # ── the DELIVERED hook, over a repository whose default branch is master ──
    with tempfile.TemporaryDirectory() as td:
        work = _world(Path(td))
        _git(work, "checkout", "-q", "-b", "feat/x")
        for name, cmd, want in [
            ("⭐ hook: git \"push\" origin master is refused", 'git "push" origin master', "deny"),
            ("⭐ hook: git -c x=y push origin master is refused", "git -c x=y push origin master", "deny"),
            ("⭐ hook: git 'push' origin HEAD:master is refused", "git 'push' origin HEAD:master", "deny"),
            ("hook: /usr/bin/git push origin master is refused", "/usr/bin/git push origin master", "deny"),
            ("hook: a quoted --force is refused", 'git push "--force" origin feat/x', "deny"),
            ("hook: a feature-branch push is allowed", "git push origin feat/x", "allow"),
            ("hook: the control `git log --grep push` is allowed on a feature branch",
             "git log --grep push", "allow"),
            ("hook: the control `echo \"git push later\"` is allowed on a feature branch",
             'echo "git push later"', "allow"),
            ("⭐ hook: X-F1 — Codex's sixty `-c` input is REFUSED, not hung", xf1, "deny"),
            ("hook: C-F1 — a line continuation before master is refused", "git push \\\n  origin master",
             "deny"),
            ("hook: C-F2 — a commit message naming push and master, then a feature push, is allowed",
             'git commit -m "push the fix, not master" && git push origin feat/x', "allow"),
            ("hook: C-F2 — `git stash push` naming master is allowed",
             'git stash push -m "before master merge"', "allow"),
            ("hook: C-F2 — a feature push, then `--title \"Do not push to master\"`, is allowed",
             'git push origin feat/x && gh pr create --title "Do not push to master" --body-file b', "allow"),
            ("hook: `2>&1` after a feature push is allowed", "git push -u origin feat/x 2>&1", "allow"),
            ("⚠ hook: the BOUND — `git log --oneline --grep \"push to master\"` is REFUSED on a feature branch",
             'git log --oneline --grep "push to master"', "deny"),
            ("⚠ hook: the BOUND — a feature push in a subshell is REFUSED (unresolved `)`)",
             "(cd . && git push origin feat/x)", "deny"),
        ]:
            case(name, _hook(work, cmd)[0], want)
        d, why = _hook(work, 'git -C "my dir" push origin master')
        case("hook: a LOOSE refusal says it was read by the fail-closed rule",
             (d, "fail-closed" in why, "backlog #428" in why), ("deny", True, True))
        d, why = _hook(work, 'git "push" origin master')
        case("hook: a STRICT refusal does not claim the fail-closed rule", (d, "fail-closed" in why),
             ("deny", False))
        _git(work, "checkout", "-q", "master")
        for name, cmd, want in [
            ("⚠ hook: the BOUND — `git log --grep push` is REFUSED on the default branch",
             "git log --grep push", "deny"),
            ("⚠ hook: the BOUND — `echo \"git push later\"` is REFUSED on the default branch",
             'echo "git push later"', "deny"),
            ("hook: a command without the word push is untouched on the default branch",
             "git status", "allow"),
            ("⚠ hook: the BOUND — `echo push; git status` is REFUSED on the default branch",
             "echo push; git status", "deny"),
            ("hook: C-F2 — `git stash push -m wip` is allowed on the default branch",
             "git stash push -m wip", "allow"),
        ]:
            case(name, _hook(work, cmd)[0], want)
        # The detection cannot run -> REFUSED, never allowed (a hook copy beside no detector).
        lone = Path(td) / "lone" / ".claude" / "hooks"
        lone.mkdir(parents=True)
        (lone / HOOK.name).write_text(HOOK.read_text())
        d, why = _hook(work, "git push origin feat/x", hook=lone / HOOK.name)
        case("hook: a missing detector REFUSES and says NOT CHECKED", (d, "NOT CHECKED" in why),
             ("deny", True))
        # A detector ended by its deadline (SIGALRM, exit 142) -> REFUSED, and the reason says so.
        slow = Path(td) / "slow"
        (slow / ".claude" / "hooks").mkdir(parents=True)
        (slow / "scripts").mkdir()
        (slow / ".claude" / "hooks" / HOOK.name).write_text(HOOK.read_text())
        (slow / "scripts" / Path(__file__).name).write_text(
            "import os, signal\nos.kill(os.getpid(), signal.SIGALRM)\n")
        d, why = _hook(work, "git push origin feat/x", hook=slow / ".claude" / "hooks" / HOOK.name)
        case("hook: a detector ended by its deadline REFUSES and says so",
             (d, "NOT CHECKED" in why, "deadline" in why), ("deny", True, True))

    print(f"\n{ran - failures}/{ran} self-test cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
