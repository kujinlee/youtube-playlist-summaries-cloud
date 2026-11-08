#!/usr/bin/env python3
"""Which `push` invocations does a Bash command run? The detection half of the push gate (backlog #428).

`.claude/hooks/block-default-branch-push.sh` refuses a push to the default branch, a bare `--force` / `-f`
or `+<refspec>`, `--no-verify`, and the plan-leak gate's off-switches. Until backlog #428 it decided WHETHER
a command was a push by matching the RAW text, so `git "push" origin master` and `git 'push' origin
HEAD:master` were not seen as pushes and every rule was skipped (a security-review finding, MEDIUM, parser
differential: bash deletes the quotes, the hook did not). This file is that decision, in Python so the
mutation harness can reach it (`check-plan-code.py --mutate` mutates `scripts/<stem>.py` only).

⟳ PR #542 round 2: round 1 DELETED every quote and backslash BEFORE splitting the command, so quoted text
became shell syntax — a quoted `>` ate the next flag (X-F2), a quoted `;git stash` made a fake exempt chunk
(X-F3), and one strict match hid every other push in its chunk (X-F1). The tokenizer was REPLACED: the
command is now LEXED the way bash reads it, knowing which characters were quoted.

THE RULE — FAIL CLOSED:
  * LEX (`lex`): words and operators as bash splits them. Quotes are removed from a word's VALUE but are
    known while lexing, so `;`, `&`, `|`, a line end, `<` and `>` are OPERATORS only when UNQUOTED. A
    backslash-newline joins two lines (C-F1); an unquoted backslash escapes the next character. An unquoted
    `#` that STARTS a word begins a comment to the line end (`a#b` is one word). A REDIRECTION (`>f`,
    `> f`, `2>&1`, `master>/dev/null` keeps `master`) is dropped with its target, since bash never passes
    it to git. Commands are the word lists between unquoted separators.
  * UNRESOLVED: a construct this lexer does not follow — `$(`, a backtick, `$'…'`, an unquoted `(` or `)`
    (a subshell, `<(…)`), an unbalanced quote, or a command run by `eval` or `sh -c` (and bash, zsh, dash,
    ksh). If the words `git` and `push` both appear anywhere, the mode is `unresolved` and the hook
    REFUSES; otherwise `none`.
  * EVERY COMMAND IS JUDGED, and none suppresses another. Leading assignments (`A=1`) and reserved words
    (`if`, `then`, `do`, `{`, `!`, …) are skipped to reach the command word.
      - STRICT: the command word is `git`; global options are skipped (`-c`, `-C`, `--config-env`,
        `--git-dir`, `--work-tree`, `--namespace`, `--exec-path` take a separate value; any other `-flag`
        stands alone); the next word — the SUBCOMMAND — is `push`. Its segment is `push` and the words after.
      - NOT A PUSH: the subcommand is `commit` or `stash`. Its arguments, whatever they say, are arguments
        (`git stash push -m "git push origin master"`). A substitution inside them is UNRESOLVED above.
      - LOOSE (the fail-closed layer): any other command. Its words are joined, quotes and backslashes in
        them deleted (a string such as `env bash -c "git push origin 'master'"` may be code), and every
        `push` WORD in that text starts a segment running to the command's end. The segment's kind is `git`
        if the text holds the word `git` (`/usr/bin/git push`, `env git push`, `git log --grep push`), else
        `bare` (`gh pr create --title "Do not push to master"`).
  THE MODE: `strict` if any command is STRICT; its segments are every STRICT and `git` segment (a `bare`
  one is text). Otherwise `loose` if the word `git` appears anywhere: every segment. Otherwise `none`.
  ⏱ A DEADLINE: `segments` arms SIGALRM at `DEADLINE_S` with the DEFAULT action, so a run that stalls —
  even inside C code — is killed (the hook sees exit 142 and REFUSES, saying so). Never a pass.

⚠ THE BOUND, SAID PLAINLY — A HARMLESS COMMAND CAN BE REFUSED. Measured by `--self-test`, over a fixture
repository whose default branch is master:
  * on the DEFAULT branch, a LOOSE segment with fewer than two plain arguments reads as `git push
    [<remote>]`, which pushes the current branch: `git log --grep push`, `echo "git push later"` and
    `echo push; git status` are REFUSED;
  * on ANY branch, a LOOSE segment is checked like a push: text reading `push <x> <default-branch>` is
    REFUSED (`gh pr create --title "git push origin master"`, `git log --oneline --grep "push to master"`),
    and so is a dangerous flag after a loose `push` word (`git log --grep "push --force"`, `--no-verify`);
  * on ANY branch, a command holding the words `git` and `push` and an UNRESOLVED construct is REFUSED,
    whatever it does: `(cd x && git push origin feat/x)`, `cd "$(git rev-parse --show-toplevel)" && git
    push origin feat/x`, `git push origin "feat/x` (an unbalanced quote) and `bash -c 'git push origin
    feat/x'`;
  * on ANY branch, a push argument holding `(`, `)`, a backtick, `$(`, `<` or `>` even QUOTED is REFUSED
    by the hook (`git push origin 'feat/(x)'`);
  * a heredoc's body is lexed as command lines, so a body line reading `push … master` or holding an
    unbalanced quote (`Don't`) is refused like the cases above. Use `git commit -F <file>`.
  ALLOWED, and measured: `git commit -m "push the fix, not master" && git push origin feat/x`, every bare
  `git stash push …` and `git commit …` on ANY branch (`git stash push -m "git push origin master"`
  included; a `/usr/bin/git` or `env git` one is LOOSE and not exempt), a feature push followed by
  `--title "Do not push to master"`, and `git push -u origin feat/x 2>&1`. Put other text in a file
  (`--body-file`, `git commit -F`). A false refusal costs a moment; a false pass costs a push to master.

⚠ OUT OF SCOPE, as for rule 3: parameter expansions (`${…}`, `$g push` with `g=git` — in STRICT mode a
command with no git word is never a segment), an alias or a function that runs git, `git send-pack` and
other plumbing, and destinations set by config or by `--all`/`--mirror` (backlog #574). This reads command
TEXT; it is defence in depth against an ACCIDENT, not a boundary against a determined agent.
The hook is LAUNCHED by `.claude/settings.json`'s `if: Bash(*push*)`, which Claude Code matches against the
command AFTER shell unquoting: MEASURED on 2.1.316 with marker hooks, it fired for `echo git p"u"sh …`,
`echo git pu\\sh …` and `echo pu""sh`, so those forms reach this detector.

WHAT WOULD MAKE THIS FAIL (its falsifier): `git "push" origin master`, `git -c x=y push origin master`,
`git push \\<newline> origin master`, `git 'push' origin HEAD:master`, `/usr/bin/git push origin master #
git push origin feat/x`, `git push origin feat/x --push-option='>' --force` or `git -c alias.x=';git stash'
push origin master`, run through the hook over a repository whose default branch is master, is allowed;
or a feature-branch push is refused.

    python3 scripts/push-command.py segments < command.txt   # mode line, then one `push <args>` per segment
    python3 scripts/push-command.py --self-test  # 112 cases

`segments` prints `none`, `strict`, `loose` or `unresolved` on the first line. After `strict` / `loose`,
one line per segment, each starting with the word `push` (so a bare `git push` is a non-empty line);
after `unresolved`, one line naming the construct. Exit 0; 2 on a usage error.
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
# bash's command separators and redirection operators, each recognised only when UNQUOTED.
SEPARATORS = ";&|\n"
REDIRECT_OP = re.compile(r"&>>?|<<<|<<-?|<>|>>|>\||>&|<&|>|<")
# Skipped to reach a command's command word.
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
RESERVED = frozenset({"!", "{", "}", "if", "then", "else", "elif", "do", "while", "until", "time"})
# Commands whose argument is CODE this lexer does not follow (with `-c`, for a shell).
SHELLS = frozenset({"sh", "bash", "zsh", "dash", "ksh"})
SHELL_C = re.compile(r"-[A-Za-z]*c[A-Za-z]*")


def normalize(cmd: str) -> str:
    """Line continuations joined, then every double quote, single quote and backslash deleted."""
    cmd = cmd.replace("\\\n", " ")
    return cmd.translate({ord('"'): None, ord("'"): None, ord("\\"): None})


def lex(cmd: str) -> tuple[list[list[str]], str | None]:
    """`(commands, unresolved)`: each command's words, quotes removed and redirections dropped, split at
    UNQUOTED separators; `unresolved` names the first construct this lexer does not follow, else None.

    One left-to-right pass with the quote state `q` (None, `'` or `"`), so N characters cost O(N)."""
    cmds: list[list[str]] = [[]]
    buf: list[str] = []
    started = quoted = skip = False   # a word is open / any of it was quoted / it is a redirection target
    q = None
    i, n = 0, len(cmd)

    def end_word() -> None:
        nonlocal buf, started, quoted, skip
        if started:
            if skip:
                skip = False
            else:
                cmds[-1].append("".join(buf))
        buf, started, quoted = [], False, False

    while i < n:
        c = cmd[i]
        if q is None and (c in "<>" or cmd.startswith("&>", i)):
            if started and not quoted and "".join(buf).isdigit():
                buf, started = [], False          # `2>`: a file-descriptor number, never a word
            else:
                end_word()                         # `master>/dev/null` keeps `master`
            i = REDIRECT_OP.match(cmd, i).end()
            skip = True                            # the next word is the redirection's target
            continue
        if q is None and c in SEPARATORS:
            end_word()
            skip = False
            if cmds[-1]:
                cmds.append([])
            i += 1
            continue
        if q is None and c in " \t":
            end_word()
            i += 1
            continue
        if q is None and c == "#" and not started:
            j = cmd.find("\n", i)                  # a comment runs to the line end, never past it
            i = n if j < 0 else j
            continue
        if q is None and c in "()":
            return cmds, "a subshell `(`…`)`"
        if q != "'" and c == "`":
            return cmds, "a backtick"
        if q != "'" and cmd.startswith("$(", i):
            return cmds, "a substitution `$(`"
        if q is None and cmd.startswith("$'", i):
            return cmds, "an ANSI-C string `$'…'`"
        if c == "\\" and q != "'":
            nxt = cmd[i + 1:i + 2]
            if nxt == "\n":                        # a line continuation joins the lines (C-F1)
                i += 2
                continue
            if q is None or nxt in '$`"\\':
                buf.append(nxt)
                started = quoted = True
                i += 2
                continue
        if q is None and c in "'\"":
            q = c
            started = quoted = True
            i += 1
            continue
        if c == q:
            q = None
            i += 1
            continue
        buf.append(c)
        started = True
        i += 1
    if q is not None:
        return cmds, "an unbalanced quote"
    end_word()
    return [w for w in cmds if w], None


def _command_word(words: list[str]) -> int:
    """The index of the command word: leading assignments and reserved words skipped."""
    i = 0
    while i < len(words) and (words[i] in RESERVED or ASSIGNMENT.match(words[i])):
        i += 1
    return i


def _subcommand(words: list[str], g: int) -> int:
    """The index of git's subcommand: the first word after `git` (at `g`) and its global options."""
    s = g + 1
    while s < len(words) and words[s].startswith("-") and len(words[s]) > 1:
        s += 2 if words[s] in VALUE_OPTS else 1
    return s


def _runs_code(words: list[str]) -> bool:
    """`eval …` or `sh -c …`: the argument is code, which this lexer does not follow."""
    c = _command_word(words)
    if c >= len(words):
        return False
    name = words[c].rsplit("/", 1)[-1]
    return name == "eval" or (name in SHELLS and any(SHELL_C.fullmatch(w) for w in words[c + 1:]))


def _segment(rest: str) -> str:
    """`push` and the arguments after it, whitespace collapsed (a quoted newline never ends a line)."""
    return " ".join(["push", *rest.split()])


def _judge(words: list[str]) -> list[tuple[str, str]]:
    """One command's segments, each with its kind: `strict`, `git` (loose, a git word) or `bare`."""
    c = _command_word(words)   # the command word, never a wrapper's argument
    if c < len(words) and words[c] == "git":
        s = _subcommand(words, c)
        sub = words[s] if s < len(words) else ""
        if sub == "push":
            return [(_segment(" ".join(words[s + 1:])), "strict")]
        if sub in NON_PUSH_SUBCOMMANDS:
            return []
    flat = normalize(" ".join(words))
    kind = "git" if GIT_WORD.search(flat) else "bare"
    return [(_segment(flat[m.end():]), kind) for m in PUSH_WORD.finditer(flat)]


def segments(cmd: str) -> tuple[str, list[str]]:
    """`(mode, lines)`: mode is `none`, `strict`, `loose` or `unresolved`. For `strict` / `loose` each line
    is `push` and its arguments; for `unresolved`, the one line names the construct."""
    norm = normalize(cmd)
    cmds, unresolved = lex(cmd)
    if unresolved is None and any(_runs_code(w) for w in cmds):
        unresolved = "`eval` or `sh -c`"
    if unresolved is not None:
        if GIT_WORD.search(norm) and PUSH_WORD.search(norm):
            return "unresolved", [unresolved]
        return "none", []
    found: list[tuple[str, str]] = []
    for words in cmds:
        found += _judge(words)
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
    # ⟳ round 2: was LOOSE, when quotes were deleted before splitting; a lexed `"my dir"` is ONE word.
    case("⭐ an option value with a space is STRICT once quotes are lexed",
         segments('git -C "my dir" push origin master'), ("strict", ["push origin master"]))
    case("the control `git log --grep push` is LOOSE, one bare segment", segments("git log --grep push"),
         ("loose", ["push"]))
    # ⟳ round 2: was STRICT; `echo` is the command word, so its string is read by the fail-closed layer.
    case("the control `echo \"git push later\"` is LOOSE: echo's string is read as text",
         segments('echo "git push later"'), ("loose", ["push later"]))
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
    # ⟳ round 2: these two were LOOSE (`push origin master)`, `push )`); a `$(` is now UNRESOLVED outright.
    case("C-F2: a git word AFTER `git commit` voids the exemption",
         segments('git commit -m "$(git push origin master)"'), ("unresolved", ["a substitution `$(`"]))
    case("C-F2: `echo $(git stash push)` is unresolved, never exempt",
         segments("echo $(git stash push)"), ("unresolved", ["a substitution `$(`"]))
    case("C-F2: the exemption wants git as the COMMAND word, not a wrapper's argument",
         segments('env git stash push -m "push to master"'),
         ("loose", ["push -m push to master", "push to master"]))
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
    # ── PR #542 round 2: the command is LEXED, quotes known; every repro in the Codex review ──
    case("⭐ X-F1 r2: a real push BEFORE a `#` is judged; the comment's push is not",
         segments("/usr/bin/git push origin master # git push origin feat/x"),
         ("loose", ["push origin master"]))
    case("X-F1 r2: a `--force` before a `#` is kept",
         segments("/usr/bin/git push --force origin feat/x # git push origin feat/x"),
         ("loose", ["push --force origin feat/x"]))
    case("X-F1 r2: a `--no-verify` before a `#` is kept",
         segments("/usr/bin/git push --no-verify origin feat/x # git push origin feat/x"),
         ("loose", ["push --no-verify origin feat/x"]))
    case("⭐ X-F1 r2: a quoted `;` in a `-c` value does not split the invocation",
         segments("git push origin feat/x; git -c alias.x=';' push origin master"),
         ("strict", ["push origin feat/x", "push origin master"]))
    case("X-F1 r2: a comment's push is text, not a push", segments("git status # git push origin master"),
         ("none", []))
    case("X-F1 r2: a `#` inside a word starts no comment", segments("echo issue#1; git push origin master"),
         ("strict", ["push origin master"]))
    case("⭐ X-F2 r2: a quoted `>` in an option value eats no `--force`",
         segments("git push origin feat/x --push-option='>' --force"),
         ("strict", ["push origin feat/x --push-option=> --force"]))
    case("X-F2 r2: a quoted `>` in an option value eats no `--no-verify`",
         segments("git push origin feat/x --push-option='>' --no-verify"),
         ("strict", ["push origin feat/x --push-option=> --no-verify"]))
    case("⭐ X-F2 r2: a quoted `>` in an option value eats no destination",
         segments("git push origin --push-option='>' master"),
         ("strict", ["push origin --push-option=> master"]))
    case("⭐ X-F3 r2: a quoted `;git stash` in a `-c` value does not exempt the push",
         segments("git -c alias.x=';git stash' push origin master"), ("strict", ["push origin master"]))
    case("X-F3 r2: ... nor hide its `--force`",
         segments("git -c alias.x=';git stash' push --force origin feat/x"),
         ("strict", ["push --force origin feat/x"]))
    case("X-F3 r2: ... nor a quoted `;git commit` hide `--no-verify`",
         segments("git -c alias.x=';git commit' push --no-verify origin feat/x"),
         ("strict", ["push --no-verify origin feat/x"]))
    case("X-F3 r2: ... nor hide a second `-c`",
         segments("git -c alias.x=';git stash' -c core.hooksPath=/tmp push origin feat/x"),
         ("strict", ["push origin feat/x"]))
    case("X-F3 r2: an assignment before git is skipped, so the push is strict",
         segments("A_B=1 git -c alias.x=';git stash' push origin feat/x"), ("strict", ["push origin feat/x"]))
    case("a reserved word before git is skipped, so the push is strict",
         segments("if true; then git push origin master; fi"), ("strict", ["push origin master"]))
    case("⭐ X-F4 r2: the SUBCOMMAND decides — a stash message naming a push is not a push",
         segments('git stash push -m "git push origin master"'), ("none", []))
    case("X-F4 r2: the BOUND — a dangerous flag after a loose push word is a segment",
         segments('git log --grep "push --force"'), ("loose", ["push --force"]))
    case("the loose reading deletes the quotes inside a string that may be code",
         segments('env bash -c "git push origin \'master\'"'), ("loose", ["push origin master"]))
    case("⭐ UNRESOLVED: a backtick inside a commit message is never exempt",
         segments('git commit -m "`git push origin master`"'), ("unresolved", ["a backtick"]))
    case("UNRESOLVED: a subshell", segments("(cd . && git push origin feat/x)"),
         ("unresolved", ["a subshell `(`…`)`"]))
    case("UNRESOLVED: an unbalanced quote", segments('git push origin "feat/x'),
         ("unresolved", ["an unbalanced quote"]))
    case("UNRESOLVED: an ANSI-C string", segments("git push origin $'master'"),
         ("unresolved", ["an ANSI-C string `$'…'`"]))
    case("UNRESOLVED: `sh -c`", segments("sh -c 'git push origin feat/x'"),
         ("unresolved", ["`eval` or `sh -c`"]))
    case("UNRESOLVED: `eval`", segments("eval git push origin feat/x"), ("unresolved", ["`eval` or `sh -c`"]))
    case("an unresolved construct with no git and push words is none", segments("echo $(date)"),
         ("none", []))

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
            # ── PR #542 round 2: each Codex repro, through the delivered hook, on a FEATURE branch ──
            ("⭐ hook: X-F1 r2 — a push to master before a `#` decoy is refused",
             "/usr/bin/git push origin master # git push origin feat/x", "deny"),
            ("hook: X-F1 r2 — a --force before a `#` decoy is refused",
             "/usr/bin/git push --force origin feat/x # git push origin feat/x", "deny"),
            ("hook: X-F1 r2 — a --no-verify before a `#` decoy is refused",
             "/usr/bin/git push --no-verify origin feat/x # git push origin feat/x", "deny"),
            ("⭐ hook: X-F1 r2 — a quoted `;` in -c does not hide the second push",
             "git push origin feat/x; git -c alias.x=';' push origin master", "deny"),
            ("⭐ hook: X-F2 r2 — a quoted `>` does not eat --force",
             "git push origin feat/x --push-option='>' --force", "deny"),
            ("hook: X-F2 r2 — a quoted `>` does not eat --no-verify",
             "git push origin feat/x --push-option='>' --no-verify", "deny"),
            ("hook: X-F2 r2 — a quoted `>` does not eat master",
             "git push origin --push-option='>' master", "deny"),
            ("⭐ hook: X-F3 r2 — a quoted `;git stash` does not exempt a push to master",
             "git -c alias.x=';git stash' push origin master", "deny"),
            ("hook: X-F3 r2 — ... nor a --force",
             "git -c alias.x=';git stash' push --force origin feat/x", "deny"),
            ("hook: X-F3 r2 — ... nor a quoted `;git commit` a --no-verify",
             "git -c alias.x=';git commit' push --no-verify origin feat/x", "deny"),
            ("hook: X-F3 r2 — ... nor a core.hooksPath",
             "git -c alias.x=';git stash' -c core.hooksPath=/tmp push origin feat/x", "deny"),
            ("hook: X-F3 r2 — ... nor ALLOW_PLAN_LEAK",
             "ALLOW_PLAN_LEAK=1 git -c alias.x=';git stash' push origin feat/x", "deny"),
            ("⚠ hook: X-F4 r2, the BOUND — `git log --grep \"push --force\"` is REFUSED on a feature branch",
             'git log --grep "push --force"', "deny"),
            ("hook: X-F4 r2 — `git stash push -m \"git push origin master\"` is allowed",
             'git stash push -m "git push origin master"', "allow"),
            ("hook: a quoted `>` in a feature push's option value is allowed",
             "git push origin feat/x --push-option='>'", "allow"),
            ("hook: a feature push with a comment naming master is allowed",
             "git push origin feat/x # not master", "allow"),
            ("⚠ hook: the BOUND — an UNRESOLVED `$(` beside a feature push is REFUSED",
             'cd "$(git rev-parse --show-toplevel)" && git push origin feat/x', "deny"),
            ("⚠ hook: the BOUND — an unbalanced quote beside a push is REFUSED",
             'git push origin "feat/x', "deny"),
            ("⚠ hook: the BOUND — `bash -c` running a feature push is REFUSED",
             "bash -c 'git push origin feat/x'", "deny"),
            ("hook: the coordinator's push line is allowed",
             "python3 s.py . | tail -1 | grep -q 'hits: 0' && git push -q origin HEAD:feat/x", "allow"),
        ]:
            case(name, _hook(work, cmd)[0], want)
        d, why = _hook(work, 'cd "$(pwd)" && git push origin feat/x')
        case("hook: an UNRESOLVED refusal names the construct and says NOT CHECKED",
             (d, "NOT CHECKED" in why, "`$(`" in why), ("deny", True, True))
        # ⟳ round 2: this input was `git -C "my dir" push origin master`, which is now STRICT (one lexed word).
        d, why = _hook(work, "/usr/bin/git push origin master")
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
            ("hook: X-F4 r2 — `git stash push -m \"git push origin master\"` is allowed on the default branch",
             'git stash push -m "git push origin master"', "allow"),
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
