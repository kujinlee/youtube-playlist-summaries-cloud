#!/usr/bin/env python3
"""Which `push` invocations does a Bash command run? The detection half of the push gate (backlog #428).

`.claude/hooks/block-default-branch-push.sh` refuses a push to the default branch, a bare `--force` / `-f`,
`--no-verify`, and the plan-leak gate's off-switches. Until backlog #428 it decided WHETHER a command was a
push by matching the RAW text, so `git "push" origin master` and `git 'push' origin HEAD:master` were not
seen as pushes and every rule was skipped (a security-review finding, MEDIUM, parser differential: bash
deletes the quotes, the hook did not). This file is that decision, in Python so the mutation harness can
reach it (`check-plan-code.py --mutate` mutates `scripts/<stem>.py` only, never a shell file).

THE RULE — FAIL CLOSED, in two layers, both read from the NORMALISED text:
  * NORMALISE: delete every `"`, `'` and `\\` — the same normalisation the hook's rule 3 already uses for
    `hookspath`. `git "push" origin "master"` becomes `git push origin master`.
  * STRICT: a `git [global options] push` invocation, with the option pattern the hook used (`GITOPTS`).
  * LOOSE (the fail-closed layer): the WORDS `git` and `push` both appear but STRICT did not match — an
    option the pattern does not know (`git -C "my dir" push`), a path to git (`/usr/bin/git push`). The
    command is treated as a push anyway, and every rule runs.
  Either way the SEGMENTS are every word `push` with its arguments up to the next `;`, `&`, `|` or line
  end. Every STRICT segment is also a LOOSE segment, so the rules read the same arguments in both modes;
  the mode only changes what the refusal SAYS, so a reader of a loose refusal is told why.

⚠ THE BOUND, SAID PLAINLY — A HARMLESS COMMAND CAN BE REFUSED. Any Bash command containing the words `git`
and `push` is read as a push. Measured by `--self-test` over a fixture repository:
  * on a FEATURE branch, `git log --grep push` and `echo "git push later"` are ALLOWED — their segment
    names no default-branch refspec and no dangerous flag;
  * on the DEFAULT branch they are REFUSED, because a segment with fewer than two plain arguments reads as
    `git push [<remote>]`, which pushes the current branch;
  * on ANY branch, text that reads `git push <remote> <default-branch>` once quotes are deleted is
    refused even inside a string (`gh pr create --title "git push origin master"`). Put such text in a
    file (`--body-file`, `git commit -F`), which this repository requires for long text anyway.
  A false refusal costs a moment; a false pass costs a push to master. That trade is the rule.

⚠ OUT OF SCOPE, as for rule 3: shell expansions (`$'\\x70ush'`, `${…}`), an alias or a function that
runs git, `git send-pack` and other plumbing. This reads command TEXT; it is defence in depth against an
ACCIDENT, not a boundary against a determined agent.

WHAT WOULD MAKE THIS FAIL (its falsifier): `git "push" origin master`, `git -c x=y push origin master` or
`git 'push' origin HEAD:master`, run through the hook over a repository whose default branch is master,
is allowed; or a feature-branch push is refused.

    python3 scripts/push-command.py segments < command.txt   # mode line, then one `push <args>` per segment
    python3 scripts/push-command.py --self-test  # 39 cases

`segments` prints `none`, `strict` or `loose` on the first line, then one line per segment, each
starting with the word `push` (so a bare `git push` is a non-empty line). Exit 0; 2 on a usage error.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK = REPO_ROOT / ".claude" / "hooks" / "block-default-branch-push.sh"

# The global options a `git` invocation may carry before its subcommand: those that take a SEPARATE value,
# and any other `-flag`. The pattern the hook used (backlog #393), with `[ \t]` for bash's per-line
# `[[:space:]]`: `grep` read one line at a time, so a newline never joined two words.
GITOPTS = (r"(?:(?:-c|-C|--config-env|--git-dir|--work-tree|--namespace|--exec-path)[ \t]+\S+[ \t]+"
           r"|-\S+[ \t]+)*")
STRICT = re.compile(r"(?:^|(?<=[;&|\s]))git[ \t]+" + GITOPTS + r"push(?=[ \t]|$)", re.M)
# A WORD: not glued to a name character, a path or a hyphen, so `.git`, `legit`, `block-…-push.sh`,
# `--push-option` and the branch `push-hook-quoted` are not the words `git` / `push`. `/usr/bin/git` IS.
GIT_WORD = re.compile(r"(?<![\w.-])git(?![\w.-])")
PUSH_SEG = re.compile(r"(?<![\w./-])push(?![\w./-])([ \t]+[^;&|\n]*)?")


def normalize(cmd: str) -> str:
    """The command with every double quote, single quote and backslash deleted (the hook's rule 3 form)."""
    return cmd.translate({ord('"'): None, ord("'"): None, ord("\\"): None})


def segments(cmd: str) -> tuple[str, list[str]]:
    """`(mode, segments)`: mode is `none`, `strict` or `loose`; each segment is `push` and its arguments."""
    norm = normalize(cmd)
    segs = [("push " + (m.group(1) or "").strip()).rstrip() for m in PUSH_SEG.finditer(norm)]
    if STRICT.search(norm):
        return "strict", segs
    if GIT_WORD.search(norm) and segs:
        return "loose", segs
    return "none", []


def main(argv: list[str]) -> int:
    if argv == ["--self-test"]:
        return self_test()
    if argv != ["segments"]:
        print("usage: push-command.py segments < command  |  --self-test", file=sys.stderr)
        return 2
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


def _hook(cwd: Path, command: str, hook: Path = HOOK) -> tuple[str, str]:
    """`(decision, reason)` from running the delivered hook over the Claude Code stdin contract."""
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    r = subprocess.run(["bash", str(hook)], cwd=cwd, input=payload, capture_output=True, text=True,
                       timeout=60)
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

    # ── the CLI contract the hook reads ──
    r = subprocess.run([sys.executable, __file__, "segments"], input="/usr/bin/git push origin master",
                       capture_output=True, text=True)
    case("segments prints the mode, then one line per segment", (r.returncode, r.stdout),
         (0, "loose\npush origin master\n"))
    r = subprocess.run([sys.executable, __file__, "bogus"], capture_output=True, text=True)
    case("an unknown mode is a usage error", r.returncode, 2)

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
        ]:
            case(name, _hook(work, cmd)[0], want)
        # The detection cannot run -> REFUSED, never allowed (a hook copy beside no detector).
        lone = Path(td) / "lone" / ".claude" / "hooks"
        lone.mkdir(parents=True)
        (lone / HOOK.name).write_text(HOOK.read_text())
        d, why = _hook(work, "git push origin feat/x", hook=lone / HOOK.name)
        case("hook: a missing detector REFUSES and says NOT CHECKED", (d, "NOT CHECKED" in why),
             ("deny", True))

    print(f"\n{ran - failures}/{ran} self-test cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
