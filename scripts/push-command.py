#!/usr/bin/env python3
"""Does a Bash command push somewhere the push gate refuses? ONE reader for every rule (backlog #428).

`.claude/hooks/block-default-branch-push.sh` refuses a push to the default branch (rule 1), a bare `--force` / `-f`
or `+<refspec>` and `--no-verify` (rule 2), and the plan-leak gate's off-switches (rule 3). The hook is now an
ADAPTER: it reads the payload, resolves the current and default branch and whether a remote exists, and asks
`decide` here. This file reads the command; nothing in bash does.

⟳ PR #542 round 3, Phase 6 (`docs/reviews/architecture-review-2026-11-08-push-detector.md`, design (b), level 1).
Three rounds had one class: the detector's reading of the command differed from bash's, and the difference reached
a step that DISCARDED a push word (an exemption, a dropped word, an early `none -> allow`). Round 1 read
quote-blind, round 2 read quote-aware without heredocs, and each round reproduced constructs neither reading
modelled. The r2 lexer, its loose layer and its four modes are DELETED. In their place:

THE RULE — `decide(command, current_branch, default_branch, has_remote)`:
  1. TRIGGER. The word `push` in the raw text, or in the text with quotes and backslashes deleted and a
     backslash-newline joined to nothing, or joined to a space. No trigger: `allow`.
  2. RULE 3 FIRST, before any lexing and never behind an allow: `hookspath` or `allow_plan_leak` in any of those
     views, lower-cased, refuses unless `ALLOW_DANGEROUS_PUSH=1` appears.
  3. LEX A CLOSED LANGUAGE EXACTLY, ELSE REFUSE (`outside`). Unquoted: `[A-Za-z0-9_./:=@+,%^-]`, blanks, newline,
     `;` `&` `|`, the redirections `<` `>` `>>` `>|` `&>` with a target word, and `N>&M` / `N<&M` with
     digits. Single quotes: anything. Double quotes: anything but a backtick or a backslash, and `$` only as a
     parameter. A parameter is `$NAME`, `${NAME}`, `$?` `$$` `$!` `$#` `$0`-`$9`, read as a word of UNKNOWN
     value; unquoted, its word COUNT is unknown too (bash splits it). Everything else is outside: `<<`, `<<<`,
     `<>`, `&>>` (bash 3.2 and 5 disagree), `>&` without digits, two redirections in a row, a redirection with no target, an unbalanced quote,
     `$'`, `$"`, `$(`, `${…op…}`, and any unquoted backtick, backslash, `#`, `{`, `}`, `*`, `?`, `[`, `]`, `~`,
     `!`, `(`, `)` or non-ASCII character. Inside this language bash does nothing but split words, remove quotes
     and substitute the parameters, so the lexer's commands ARE bash's commands. `--self-test` measures that
     against `/bin/bash` (the bash-agreement check).
  4. JUDGE EVERY COMMAND from closed tables (leading assignments and `if`/`then`/`do`/… skipped):
       - `git` (or `…/git`): global options from `GIT_VALUE_OPTS` / `GIT_EQ_OPTS` / `GIT_FLAG_OPTS`; an unknown
         one in a command holding a push word refuses. Subcommand `push`: options from `PUSH_FLAGS` /
         `PUSH_EQ` / `PUSH_VALUE`; `-f`/`--force`/`+<refspec>` and `--no-verify` are rule 2; any other option
         refuses. Each refspec's destination is the text after its last `:`, minus `refs/heads/` or `heads/`,
         with `HEAD`/`@` read as the current branch; the default branch is rule 1, and so is a push with fewer
         than two positionals on the default branch. A subcommand in `INERT_SUB` is text. Any other subcommand
         holding a push word refuses.
       - a CODE RUNNER (`CODE_RUNNERS`: `bash`, `eval`, `xargs`, `env`, `python3`, `timeout`, …) holding a push
         word, or taking code (`-c`, `-e`, `-`, or reading stdin), refuses; so does one that runs its arguments as
         a command (`ARGV_RUNNERS`: `env`, `xargs`, `timeout`, …) given a word of unknown value.
       - a command in `INERT_TEXT` (`echo`, `grep`, `gh`, `cd`, …) is text.
       - any other command holding a push word refuses.
       - a word of unknown value refuses as a command word; at or before a git command's subcommand (except a
         double-quoted `-C` value); and anywhere in a git command holding a push word.
  `decide` prints `allow`, or `deny <rule> <reason>` with rule one of `default-branch`, `force`, `no-verify`,
  `hookspath`, `plan-leak`, `outside`, `option`, `code-runner`, `unjudged`. Exit 0. The hook refuses any other
  exit or output.
  ⏱ A DEADLINE: `main` arms SIGALRM at `DEADLINE_S` with the DEFAULT action, so a run that stalls, even inside C
  code, is killed (the hook sees exit 142 and REFUSES, saying so). Never a pass.

⚠ THE BOUND, SAID PLAINLY: a command holding the word `push` is refused unless it is written in the closed language
above and every command in it is judged allowed. MEASURED on 1,634 unique transcript commands holding `git` and
`push` (the Phase 6 corpus, `feat/x` fixture, decided in-process): THIS FILE refuses 1,250 unique / 1,383
occurrences, against round 2's hook 1,166 / 1,292 (86 new, 2 relieved). The architecture review's level-1
prototype refused 1,241 / 1,374 (77 new, 2 relieved); the 9 beyond it are a parameter as a command word or before
a git subcommand (`$PY x.py`, `git -C $W push …`), which bash may expand into a push. The common refusals: a heredoc or a `$(` beside a push (`git commit -m
"$(cat <<'EOF' …)" && git push …`), `${S:?}`, `[ … ]`, `@{u}`, a backslash continuation, a `#` comment, a
backslash inside double quotes, `timeout`/`env` around a push. THE REMEDY, printed with every such refusal: run
the push as its own plain command, `git push -u origin <branch>`. A false refusal costs a moment; a false pass
costs a push to master. Widening the language (heredocs, `$( … )`) is filed, not built.

⚠ OUT OF SCOPE: values not in the text — an alias or a function that runs git, a git alias with no push word
(`git p`), destinations set by config (`push.default`, `remote.<r>.push`; backlog #574, re-scoped to rule 1 in
`.githooks/pre-push`), scripts run from files, a `core.hooksPath` set by an EARLIER call — and `$'\\x70ush'`,
which the hook's `if: Bash(*push*)` launch filter never sees. This reads command TEXT; it is defence in depth
against an ACCIDENT, not a boundary against a determined agent.

WHAT WOULD MAKE THIS FAIL (its falsifier): any of the round 1-3 repros in `--self-test` (`git "push" origin
master`, `git push \\<newline> origin master`, `cat <<EOF … EOF` then `git push origin master # '`, `git
--attr-source stash push origin master`, `git push origin {master,}`, `git push origin $"master"`, `git push -uf
origin feat/x`, `echo master | xargs git push origin`, `git push origin HEAD:heads/master`) decided `allow` on a
feature branch of a repository whose default branch is master; or the bash-agreement check finding a command bash
runs that the lexer did not report; or a feature-branch push refused.

    python3 scripts/push-command.py decide <current> <default> <has_remote 0|1> < command.txt
    python3 scripts/push-command.py --self-test  # 265 cases

⚡ Only `re` and `sys` load on the `decide` path (PR #542 round 1, C-F8): the self-test's imports are lazy.
"""
from __future__ import annotations

import re
import sys

# Under the hook's own timeout, with room for a loaded machine's interpreter start.
DEADLINE_S = 3.0
# A WORD: not glued to a name character, a path or a hyphen, so `--push-option` and the branch `push-hook-quoted`
# are not the word `push`.
PUSH_WORD = re.compile(r"(?<![\w./-])push(?![\w./-])")
# ── the closed language ──
SAFE_UNQUOTED = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_./:=@+,%^-")
BLANK = " \t"
SEPS = ";&|\n"
REDIR = re.compile(r"&>|>>|>\||>&|<&|>|<")
FD_DUP = re.compile(r"[0-9]+(?=[ \t;&|\n]|$)")
PARAM = re.compile(r"\$(?:\{[A-Za-z_][A-Za-z0-9_]*\}|[A-Za-z_][A-Za-z0-9_]*|[?$!#0-9])")
UNKNOWN = "\x00"   # in a word: a double-quoted parameter, one word of unknown value
SPLIT = "\x01"     # in a word: an UNQUOTED parameter, unknown value AND unknown word count
# ── judging ──
ASSIGN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
RESERVED = frozenset({"if", "then", "else", "elif", "do", "while", "until"})
GIT_VALUE_OPTS = frozenset({"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env",
                            "--super-prefix", "--attr-source"})
GIT_EQ_OPTS = ("--git-dir=", "--work-tree=", "--namespace=", "--exec-path=", "--config-env=", "--super-prefix=",
               "--attr-source=")
GIT_FLAG_OPTS = frozenset({"-p", "--paginate", "-P", "--no-pager", "--no-replace-objects", "--no-lazy-fetch",
                           "--no-optional-locks", "--no-advice", "--bare", "--literal-pathspecs",
                           "--glob-pathspecs", "--noglob-pathspecs", "--icase-pathspecs"})
PUSH_FLAGS = frozenset({"-u", "--set-upstream", "-n", "--dry-run", "-v", "--verbose", "-q", "--quiet",
                        "--porcelain", "--progress", "--no-progress", "--tags", "--follow-tags", "--no-follow-tags",
                        "--atomic", "--no-atomic", "--force-with-lease", "--force-if-includes",
                        "--no-force-if-includes", "-d", "--delete", "--signed", "--no-signed", "-4", "-6",
                        "--ipv4", "--ipv6", "--verify"})
PUSH_EQ = ("--force-with-lease=", "--push-option=", "--signed=", "--recurse-submodules=")
PUSH_VALUE = frozenset({"-o", "--push-option"})
FORCE_OPTS = frozenset({"-f", "--force"})
INERT_SUB = frozenset({"commit", "stash", "log", "show", "diff", "grep", "status", "add", "rev-parse", "branch",
                       "fetch", "ls-remote", "merge-base", "rev-list", "shortlog", "describe", "blame", "cat-file",
                       "ls-files", "ls-tree", "check-ignore", "reflog", "restore", "checkout", "switch", "reset",
                       "rm", "mv", "notes", "symbolic-ref", "show-ref", "for-each-ref", "cherry", "range-diff",
                       "format-patch", "worktree"})
INERT_TEXT = frozenset({"echo", "printf", "grep", "egrep", "fgrep", "rg", "gh", "cat", "head", "tail", "wc",
                        "sort", "uniq", "ls", "test", "true", "false", "cd", "pwd", "sleep", "jq", "date", "tee",
                        "tr", "cut", "diff", "mkdir", "touch", "basename", "dirname", "which", "type"})
CODE_RUNNERS = frozenset({"bash", "sh", "zsh", "dash", "ksh", "fish", "eval", "source", ".", "exec", "xargs",
                          "env", "command", "builtin", "nohup", "timeout", "gtimeout", "nice", "sudo", "watch",
                          "parallel", "time", "python", "python3", "perl", "ruby", "node", "osascript", "awk",
                          "sed", "find", "script", "make"})
# Code runners that run their ARGUMENTS as a command: a word of unknown value given to one may BE that command.
ARGV_RUNNERS = frozenset({"eval", "exec", "xargs", "env", "command", "builtin", "nohup", "timeout", "gtimeout",
                          "nice", "sudo", "watch", "parallel", "time"})
STDIN_CODE = frozenset({"bash", "sh", "zsh", "dash", "ksh", "fish", "python", "python3", "perl", "ruby", "node",
                        "osascript"})


class Outside(Exception):
    """The command uses a construct outside the closed language: it cannot be read exactly."""


def views(cmd: str) -> list[str]:
    """The quote-blind VIEWS the trigger and rule 3 read: raw; quotes and backslashes deleted with a
    backslash-newline joined to nothing (as bash joins it); the same joined to a space."""
    drop = {ord('"'): None, ord("'"): None, ord("\\"): None}
    return [cmd, cmd.replace("\\\n", "").translate(drop), cmd.replace("\\\n", " ").translate(drop)]


def lex(cmd: str) -> list[list[str]]:
    """Each command's words, quotes removed, redirections dropped with their targets, split at UNQUOTED
    separators. Raises `Outside` naming the first construct outside the closed language.

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

    def param(j: int, marker: str) -> int:
        nonlocal started
        m = PARAM.match(cmd, j)
        if not m:
            raise Outside(f"a `$` construct outside the closed language (`{cmd[j:j + 3]}`)")
        buf.append(marker)
        started = True
        return m.end()

    while i < n:
        c = cmd[i]
        if q == "'":
            if c == "'":
                q = None
            else:
                buf.append(c)
            i += 1
            continue
        if q == '"':
            if c == "$":
                i = param(i, UNKNOWN)
                continue
            if c in "`\\":
                raise Outside(f"`{c}` inside double quotes")
            if c == '"':
                q = None
            else:
                buf.append(c)
            i += 1
            continue
        if c in "'\"":
            q = c
            started = quoted = True
            i += 1
            continue
        if c == "$":
            i = param(i, SPLIT)
            continue
        if cmd.startswith("<<", i) or cmd.startswith("<>", i):
            raise Outside(f"`{cmd[i:i + 2]}` (a heredoc, a here-string or a read-write redirection)")
        if cmd.startswith("&>>", i):
            raise Outside("`&>>` (bash 4 reads it as an append; bash 3.2 refuses it)")
        if c in "<>" or cmd.startswith("&>", i):
            if skip and not started:
                raise Outside("two redirections in a row")
            if started and not quoted and "".join(buf).isdigit():
                buf, started = [], False     # `2>`: the digits name a descriptor, not a word
            else:
                end_word()
            op = REDIR.match(cmd, i).group()
            i += len(op)
            if op in (">&", "<&"):
                m = FD_DUP.match(cmd, i)
                if not m:
                    raise Outside(f"`{op}` not followed by a file-descriptor number")
                i = m.end()
                continue
            skip = True
            continue
        if c in SEPS:
            if skip and not started:
                raise Outside("a redirection with no target")
            end_word()
            if cmds[-1]:
                cmds.append([])
            i += 1
            continue
        if c in BLANK:
            end_word()
            i += 1
            continue
        if c not in SAFE_UNQUOTED:
            raise Outside(f"an unquoted `{c}`")
        buf.append(c)
        started = True
        i += 1
    if q is not None:
        raise Outside("an unbalanced quote")
    if skip and not started:
        raise Outside("a redirection with no target")
    end_word()
    return [w for w in cmds if w]


def _has_push(words: list[str]) -> bool:
    return any(PUSH_WORD.search(w) for w in words)


def _unknown(word: str) -> bool:
    return UNKNOWN in word or SPLIT in word


def _judge_push(args: list[str], cur: str, default: str, rule1: bool, danger: bool) -> tuple[str, str] | None:
    """The arguments after `push`: options from a closed allowlist, then each destination."""
    pos, i = [], 0
    while i < len(args):
        a = args[i]
        if a.startswith("-") and a != "-":
            if a in PUSH_VALUE:
                i += 2
                continue
            if a in PUSH_FLAGS or a.startswith(PUSH_EQ):
                i += 1
                continue
            if a in FORCE_OPTS:
                if not danger:
                    return "force", f"`{a}`"
                i += 1
                continue
            if a == "--no-verify":
                if not danger:
                    return "no-verify", f"`{a}`"
                i += 1
                continue
            return "option", f"a push option the gate does not read: `{a}`"
        pos.append(a)
        i += 1
    for r in pos[1:]:
        if r.startswith("+") and not danger:
            return "force", f"the `+` refspec `{r}`"
        dest = r.lstrip("+").rsplit(":", 1)[-1]
        for p in ("refs/heads/", "heads/"):
            if dest.startswith(p):
                dest = dest[len(p):]
        if dest in ("HEAD", "@"):
            dest = cur
        if rule1 and dest == default:
            return "default-branch", f"the refspec `{r}` names `{default}`"
    if rule1 and len(pos) < 2 and cur == default:
        return "default-branch", f"a push with no refspec pushes the current branch, `{default}`"
    return None


def _judge(words: list[str], cur: str, default: str, rule1: bool, danger: bool) -> tuple[str, str] | None:
    """One command, in a text that mentions push: `(rule, reason)` to refuse, else None."""
    c = 0
    while c < len(words) and (words[c] in RESERVED or ASSIGN.match(words[c])):
        c += 1
    if c >= len(words):
        return None
    if _unknown(words[c]):
        return "unjudged", "a command word of unknown value (a parameter) in a text that mentions push"
    pushy = _has_push(words)
    name = words[c].rsplit("/", 1)[-1]
    if name == "git":
        s, quoted_c = c + 1, None
        while s < len(words) and words[s].startswith("-") and len(words[s]) > 1:
            w = words[s]
            if w in GIT_VALUE_OPTS:
                if w == "-C":
                    quoted_c = s + 1
                s += 2
            elif w in GIT_FLAG_OPTS or w.startswith(GIT_EQ_OPTS):
                s += 1
            else:
                if pushy:
                    return "option", f"a git option the gate does not read: `{w}`"
                return None
        for k in range(c + 1, min(s + 1, len(words))):
            if _unknown(words[k]) and not (k == quoted_c and SPLIT not in words[k]):
                return "unjudged", "a word of unknown value (a parameter) before a git subcommand"
        if pushy and any(_unknown(w) for k, w in enumerate(words) if k > s):
            return "unjudged", "a word of unknown value (a parameter) in a git command that mentions push"
        sub = words[s] if s < len(words) else ""
        if sub == "push":
            return _judge_push(words[s + 1:], cur, default, rule1, danger)
        if sub in INERT_SUB:
            return None
        if pushy:
            return "unjudged", f"git `{sub}` mentions push"
        return None
    if name in CODE_RUNNERS:
        rest = words[c + 1:]
        positional = [w for w in rest if not w.startswith("-")]
        if pushy or (name in ARGV_RUNNERS and any(_unknown(w) for w in rest)) \
                or (name in STDIN_CODE and not positional) \
                or any(w in ("-c", "-e", "-") for w in rest):
            return "code-runner", f"`{name}` runs code this gate cannot read, in a text that mentions push"
        return None
    if name in INERT_TEXT:
        return None
    if pushy:
        return "unjudged", f"`{name}` mentions push and is not a command this gate knows"
    return None


def decide(cmd: str, cur: str, default: str, has_remote: bool) -> tuple[str, str, str]:
    """`("allow", "", "")` or `("deny", rule, reason)`."""
    v = views(cmd)
    if not any(PUSH_WORD.search(t) for t in v):
        return "allow", "", ""
    danger = "ALLOW_DANGEROUS_PUSH=1" in cmd
    rule1 = has_remote and bool(default) and "ALLOW_DEFAULT_BRANCH_PUSH=1" not in cmd
    if not danger:
        low = " ".join(v).lower()
        if "hookspath" in low:
            return "deny", "hookspath", "the command mentions core.hooksPath"
        if "allow_plan_leak" in low:
            return "deny", "plan-leak", "the command mentions ALLOW_PLAN_LEAK"
    try:
        cmds = lex(cmd)
    except Outside as e:
        return "deny", "outside", str(e)
    for words in cmds:
        why = _judge(words, cur, default, rule1, danger)
        if why:
            return "deny", why[0], why[1]
    return "allow", "", ""


def _arm_deadline() -> None:
    """SIGALRM with its DEFAULT action at `DEADLINE_S`: the kernel ends a stalled run, even in C code."""
    import signal
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.setitimer(signal.ITIMER_REAL, DEADLINE_S)


def main(argv: list[str]) -> int:
    if argv == ["--self-test"]:
        return self_test()
    if len(argv) != 4 or argv[0] != "decide" or argv[3] not in ("0", "1"):
        print("usage: push-command.py decide <current> <default> <has_remote 0|1> < command  |  --self-test",
              file=sys.stderr)
        return 2
    _arm_deadline()
    verdict, rule, reason = decide(sys.stdin.read(), argv[1], argv[2], argv[3] == "1")
    print(verdict if verdict == "allow" else f"deny {rule} {reason}")
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


# ── the bash-agreement check (the Phase 6 oracle) ──
# `/bin/bash` runs each string with `git`, `echo` and `gh` replaced by functions that log their argv. PROPERTY:
# every invocation bash runs appears, argv identical, in the lexer's command list (a word holding UNKNOWN
# matches any text there; a word holding SPLIT matches any number of arguments). Only strings the lexer
# ACCEPTS are compared; a rejected string can only cost a refusal.
ORACLE_SHIMS = ("git", "echo", "gh")
ORACLE_SEPS = (";", "&&", "||", "|", "&", "\n")
ORACLE_ATOMS = (
    # words and quoting
    "git", "push", "origin", "master", "feat/x", "-u", "stash", "-m", "x", "2", "1", "A=1", "'", '"',
    "'a ; b'", '"c | d"', "''", '""', "a'b'c", "'>'", '"&&"', "'$X'", "pu'sh'",
    # redirections, the dangerous direction being a target or a descriptor read as an argument
    ">", "<", ">>", ">|", "&>", "&>>", "2>&1", "1>&2", "<&0", ">f", "<f", "2>f", "> f", ">&-", ">& -u", "3>",
    # parameters
    "$X", '"$X"', "${X}", "$?", "$1", "a$X", '"a $X b"', "$X$X",
    # outside the language (the lexer must refuse them; listed so a refusal is exercised)
    "$(git push o m)", "`git push b t`", "{", "*", "\\", "#", "$'x'", '$"y"', "${X:-z}", "<<<", "~", "(", ")",
)
# One input per accepted construct, each exercising the direction in which a wrong lexer UNDER-reports.
ORACLE_INPUTS = (
    ("plain words", "git push origin feat/x"),
    ("single quotes", "git 'push' 'a ; b' pu'sh'"),
    ("double quotes", 'git "push" "c | d" "a"b"c"'),
    ("`;`", "echo a; git push o m"),
    ("`&&` and `||`", "echo a && git push o m || git push p q"),
    ("`|`", "echo a | git push o m"),
    ("`&`", "git push o m & git push p q"),
    ("a newline", "echo a\ngit push o m"),
    ("a glued redirection", "git push o m>f x"),
    ("a spaced redirection", "git push o m > f x"),
    ("`>>`, `>|`, `<`", "git push o >>f m >|g n <f k"),
    ("`&>`", "git push o &>f m"),
    ("a descriptor duplication", "git push o m 2>&1 1>&2 <&0 n"),
    ("a descriptor redirection", "git push o 2>f m"),
    ("a quoted descriptor is a word", "git push o '2'>f m"),
    ("parameters", 'git push $X "$X" ${X} a$X "a $X b" $? $1'),
    ("an assignment prefix", "A=1 git push o m"),
    ("reserved words", "if git push o m; then git push p q; fi"),
)
# Each control breaks the lexer for one construct; the check must find an unsafe string for every one of them.
ORACLE_CONTROLS = (
    ("a redirection's target is kept as a word",
     "            if skip:\n                skip = False\n            else:\n                cmds[-1].append",
     "            if skip:\n                skip = False\n            if True:\n                cmds[-1].append"),
    ("`>&` without digits is read as a redirection with a target",
     "                if not m:\n                    raise Outside(f\"`{op}` not followed",
     "                if not m:\n                    skip = True\n                    continue\n"
     "                    raise Outside(f\"`{op}` not followed"),
    ("a descriptor's digits are kept as a word",
     "            if started and not quoted and \"\".join(buf).isdigit():",
     "            if False:"),
    ("single quotes are kept in the word",
     "        if q == \"'\":\n            if c == \"'\":\n                q = None\n            else:",
     "        if q == \"'\":\n            buf.append(c)\n            if c == \"'\":\n                q = None\n            else:"),
    ("a newline is a blank, not a separator", "SEPS = \";&|\\n\"", "SEPS = \";&|\"\nBLANK = \" \\t\\n\""),
    ("a parameter is read as its literal name",
     "        buf.append(marker)\n        started = True\n        return m.end()",
     "        buf.append(m.group())\n        started = True\n        return m.end()"),
)
ORACLE_SEEDS = (1, 2)
ORACLE_PER_SEED = 500


def _oracle_strings() -> list[str]:
    import random
    out = [s for _, s in ORACLE_INPUTS]
    for seed in ORACLE_SEEDS:
        rnd = random.Random(seed)
        for _ in range(ORACLE_PER_SEED):
            parts = [rnd.choice(ORACLE_SHIMS)]
            for _ in range(rnd.randint(1, 10)):
                if rnd.random() < 0.15:
                    parts.append(rnd.choice(ORACLE_SEPS) + rnd.choice(("", " ")) + rnd.choice(ORACLE_SHIMS))
                else:
                    parts.append(rnd.choice(ORACLE_ATOMS))
            out.append("".join(p + rnd.choice((" ", " ", " ", "")) for p in parts).rstrip(" "))
    return out


def _bash_runs(strings: list[str], td: str) -> list[list[str]] | None:
    """What `/bin/bash` runs for each string: a list of `name\\x1fargs…` per string. None: no `/bin/bash`."""
    import os
    if not os.path.exists("/bin/bash"):
        return None
    with open(os.path.join(td, "in"), "w") as f:
        f.write("".join(s + "\0" for s in strings))
    for name in ("f", "g"):
        open(os.path.join(td, name), "w").close()
    shim = "".join(f"{s}() {{ local r=$'\\036'{s} a; for a in \"$@\"; do r+=$'\\037'\"$a\"; done; "
                   f"printf '%s' \"$r\" >> \"$OLOG\"; }}\n" for s in ORACLE_SHIMS)
    script = shim + ("while IFS= read -r -d '' s; do printf '\\035' >> \"$OLOG\"; "
                     "( eval \"$s\"; wait ) </dev/null >/dev/null 2>&1; done < \"$OIN\"\n")
    log = os.path.join(td, "log")
    open(log, "w").close()
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "OLOG": log, "OIN": os.path.join(td, "in"),
           "X": "v w"}
    subprocess.run(["/bin/bash", "-c", script], cwd=td, env=env, capture_output=True, timeout=120)
    raw = open(log, encoding="utf-8", errors="replace").read().split("\x1d")[1:]
    return [[r for r in chunk.split("\x1e")[1:]] for chunk in raw]


def _oracle_patterns(cmds: list[list[str]]) -> list[re.Pattern]:
    pats = []
    for w in cmds:
        c = 0
        while c < len(w) and (w[c] in RESERVED or ASSIGN.match(w[c])):
            c += 1
        if c < len(w) and _unknown(w[c]):
            pats.append(re.compile(r"[^\x1e]*\Z"))   # a command of unknown name: `_judge` refuses it
        elif c < len(w) and w[c] in ORACLE_SHIMS:
            rx = re.escape(w[c])
            for a in w[c + 1:]:
                if SPLIT in a:
                    rx += "(?:\x1f[^\x1f]*)*"
                else:
                    rx += "\x1f" + "[^\x1f]*".join(re.escape(p) for p in a.split(UNKNOWN))
            pats.append(re.compile(rx + r"\Z"))
    return pats


def _oracle(lexer, strings: list[str], runs: list[list[str]]) -> tuple[int, int, list[str]]:
    """`(accepted, unsafe, first unsafe strings)` for one lexer over the strings bash ran."""
    accepted = unsafe = 0
    bad = []
    for s, ran in zip(strings, runs):
        try:
            cmds = lexer(s)
        except Exception:
            continue
        accepted += 1
        pats = _oracle_patterns(cmds)
        if any(not any(p.match(r) for p in pats) for r in ran):
            unsafe += 1
            bad.append(s)
    return accepted, unsafe, bad[:3]


def _variant_lexer(find: str, repl: str):
    """This file's `lex` with ONE edit applied (an anchor that matches once), for an oracle control."""
    src = Path(__file__).read_text()
    if src.count(find) != 1:
        return None
    ns: dict = {"__name__": "push_command_control"}
    exec(compile(src.replace(find, repl), "push-command-control", "exec"), ns)
    return ns["lex"]


def self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    # The suite's imports load HERE, never on the hook's `decide` path (PR #542 round 1, C-F8).
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

    def d(cmd: str, cur: str = "feat/x", default: str = "master", has_remote: bool = True) -> str:
        """The decision and its rule: `allow`, or `deny <rule>`."""
        v, rule, _ = decide(cmd, cur, default, has_remote)
        return v if v == "allow" else f"deny {rule}"

    F, M = "feat/x", "master"
    # ── the Phase 6 case matrix: every round 1-3 repro (DENY) and the documented ALLOWED list ──
    matrix = [
        # backlog #428's own forms
        ("428-dq", 'git "push" origin master', F, "deny default-branch"),
        ("428-sq", "git 'push' origin HEAD:master", F, "deny default-branch"),
        ("428-c", "git -c x=y push origin master", F, "deny default-branch"),
        ("428-cont", "git push \\\norigin master", F, "deny outside"),
        ("428-cont2", "git pu\\\nsh origin master", F, "deny outside"),
        ("428-C", "git -C /tmp push origin master", F, "deny default-branch"),
        ("428-env", "env git push origin master", F, "deny code-runner"),
        ("428-shc", "sh -c 'git push origin master'", F, "deny code-runner"),
        ("428-eval", "eval git push origin master", F, "deny code-runner"),
        ("428-gitdir", "GIT_DIR=.git git push origin master", F, "deny default-branch"),
        # round 1
        ("r1-plus", "git push origin +master", F, "deny force"),
        ("r1-plusfeat", "git push origin +feat/x", F, "deny force"),
        ("r1-HEAD-on-master", "git push origin HEAD", M, "deny default-branch"),
        ("r1-at-on-master", "git push origin @", M, "deny default-branch"),
        ("r1-redir", "git push origin master>/dev/null", F, "deny default-branch"),
        # ⚠ the round 1 review expected DENY here, and that was wrong: bash's word is `HEAD:master2`, then `>&1`.
        ("r1-redir2 is ALLOWED: bash's refspec is HEAD:master2", "git push origin 'HEAD:master'2>&1", F, "allow"),
        ("r1-all", "git push --all origin", F, "deny option"),
        ("r1-mirror", "git push --mirror origin", F, "deny option"),
        # round 2 (Codex X-F1..X-F3)
        ("r2-F1a", "/usr/bin/git push origin master # git push origin feat/x", F, "deny outside"),
        ("r2-F1b", "/usr/bin/git push --force origin feat/x # git push origin feat/x", F, "deny outside"),
        ("r2-F1c", "/usr/bin/git push --no-verify origin feat/x # git push origin feat/x", F, "deny outside"),
        ("r2-F1d", "git push origin feat/x; git -c alias.x=';' push origin master", F, "deny default-branch"),
        ("r2-F2a", "git push origin feat/x --push-option='>' --force", F, "deny force"),
        ("r2-F2b", "git push origin feat/x --push-option='>' --no-verify", F, "deny no-verify"),
        ("r2-F2c", "git push origin --push-option='>' master", F, "deny default-branch"),
        ("r2-F3a", "git -c alias.x=';git stash' push origin master", F, "deny default-branch"),
        ("r2-F3b", "git -c alias.x=';git stash' push --force origin feat/x", F, "deny force"),
        ("r2-F3c", "git -c alias.x=';git commit' push --no-verify origin feat/x", F, "deny no-verify"),
        ("r2-F3d", "git -c alias.x=';git stash' -c core.hooksPath=/tmp push origin feat/x", F, "deny hookspath"),
        ("r2-F3e", "ALLOW_PLAN_LEAK=1 git -c alias.x=';git stash' push origin feat/x", F, "deny plan-leak"),
        # round 3 (Claude C-F1..C-F7)
        ("r3-F1a", "cat <<EOF\ngit stash list '\nEOF\ngit push origin master # '", F, "deny outside"),
        ("r3-F1b", "cat <<EOF\ngit stash list '\nEOF\ngit push --force origin feat/x\ncat <<EOF\n'\nEOF", F,
         "deny outside"),
        ("r3-F1c", "cat <<EOF\ngit commit -m '\nEOF\nALLOW_PLAN_LEAK=1 git -c core.hooksPath=/dev/null push "
         "--no-verify origin master # '", F, "deny hookspath"),
        ("r3-F1d", "cat <<'EOF'\ngit stash list \"\nEOF\ngit push origin HEAD:master # \"", F, "deny outside"),
        ("r3-F1e", "cat <<EOF\ngit stash list '\nEOF\ngit push --no-verify origin feat/x # '", F, "deny outside"),
        ("r3-F2a", "git --attr-source stash push origin master", F, "deny default-branch"),
        ("r3-F2b", "git --attr-source commit push --force origin feat/x", F, "deny force"),
        ("r3-F2c", "git --attr-source stash push --no-verify origin feat/x", F, "deny no-verify"),
        ("r3-F3a", "git push origin {master,}", F, "deny outside"),
        ("r3-F3b", "git push origin HEAD:{master,}", F, "deny outside"),
        ("r3-F3c", "git {push,origin,master}", F, "deny outside"),
        ("r3-F3d", "git push {--force,origin} feat/x", F, "deny outside"),
        ("r3-F3e", "/usr/bin/gi? push origin master", F, "deny outside"),
        ("r3-F3f", "git push origin feat/x; /usr/bin/g?t push origin master", F, "deny outside"),
        ("r3-F3g", "git push origin mas[t]er", F, "deny outside"),
        ("r3-F4a", 'git push origin $"master"', F, "deny outside"),
        ("r3-F4b", 'git push $"master" origin', F, "deny outside"),
        ("r3-F5a", "git push -uf origin feat/x", F, "deny option"),
        ("r3-F5b", "git push -fu origin feat/x", F, "deny option"),
        ("r3-F5c", "git push --no-veri origin feat/x", F, "deny option"),
        ("r3-F6a", "git push origin feat/x; echo master | xargs git push origin", F, "deny code-runner"),
        ("r3-F6b", "git push origin HEAD:heads/master", F, "deny default-branch"),
        ("r3-F7", "git push origin feat/x --push-option='>'", F, "allow"),
        # the documented ALLOWED list
        ("ok-1", 'git commit -m "push the fix, not master" && git push origin feat/x', F, "allow"),
        ("ok-2", 'git stash push -m "git push origin master"', F, "allow"),
        ("ok-2m", 'git stash push -m "git push origin master"', M, "allow"),
        ("ok-3", 'git push origin feat/x && gh pr create --title "Do not push to master"', F, "allow"),
        ("ok-4", "git push -u origin feat/x 2>&1", F, "allow"),
        ("ok-5", "git -C /some/worktree push -u origin feat/x", F, "allow"),
        ("ok-6", "cd /some/worktree && git push -u origin feat/x", F, "allow"),
        ("ok-7", "git push --force-with-lease origin feat/x", F, "allow"),
        ("ok-8", "git push origin HEAD:refs/heads/feat/x", F, "allow"),
        ("ok-9", "git log --grep push", M, "allow"),
        ("ok-10", 'echo "git push later"', M, "allow"),
        # the review's four extras
        ("x-1 piping text into bash is refused", "echo 'git push origin feat/x' | bash", F, "deny code-runner"),
        ("x-2 ⚠ the documented cost: a `$(cat <<'EOF' …)` commit beside a feature push is REFUSED",
         "git commit -m \"$(cat <<'EOF'\nmsg\nEOF\n)\" && git push origin feat/x", F, "deny outside"),
        ("x-3 a double-quoted $S path in cd beside a feature push is allowed",
         'cd "$S/wt" && git push -u origin feat/x', F, "allow"),
        ("x-4 a script run before a feature push is allowed",
         "python3 scripts/x.py && git push -u origin feat/x", F, "allow"),
    ]
    for name, cmd, cur, want in matrix:
        case(f"matrix {name}", d(cmd, cur), want)

    # ── each decision branch, PURE ──
    # the trigger
    case("trigger: no push word is allowed without lexing", d("echo $(date) `x` {a,b}"), "allow")
    case("⭐ trigger: a push word spelled with quotes is seen", d('git p"u"sh origin master'), "deny default-branch")
    case("trigger: a push word spelled with a backslash is seen", d("git pu\\sh origin master"), "deny outside")
    case("⭐ trigger: a push word split by a backslash-newline is seen (joined to NOTHING, as bash joins it)",
         decide("git pu\\\nsh origin master", F, M, True)[0], "deny")
    case("trigger: `--push-option` alone is not the word push", d("git log --push-option"), "allow")
    case("trigger: a branch NAMED push-… is not the word push", d("git checkout push-hook-quoted"), "allow")
    # rule 3, before lexing
    case("⭐ rule 3 runs BEFORE the lexer: a heredoc with -c core.hooksPath is rule 3, not outside",
         d("cat <<E\nE\ngit -c core.hooksPath=/x push origin feat/x"), "deny hookspath")
    case("rule 3: quotes do not hide hooksPath", d("git -c \"core.hooks\"Path=/x push origin feat/x"),
         "deny hookspath")
    case("rule 3: ALLOW_PLAN_LEAK in any form", d("ALLOW_PLAN_LEAK=0 git push origin feat/x"), "deny plan-leak")
    case("rule 3: the owner's ALLOW_DANGEROUS_PUSH=1 lifts it",
         d("ALLOW_DANGEROUS_PUSH=1 ALLOW_PLAN_LEAK=1 git push origin feat/x"), "allow")
    case("rule 3 needs the trigger: hooksPath with no push word is allowed",
         d("git config core.hooksPath .githooks"), "allow")
    # the lexer: one per OUTSIDE class
    # Three of these are ALSO refused as two redirections in a row; the reason names the construct, so each check
    # is load-bearing for the message the refusal prints.
    for name, cmd, says in [("`<<`", "cat <<E\nx\nE\ngit push origin feat/x", "heredoc"),
                            ("`<>`", "git push origin feat/x <>f", "read-write"),
                            ("`&>>`", "git push origin feat/x &>>f", "bash 3.2")]:
        v, rule, why = decide(cmd, F, M, True)
        case(f"outside: {name} is refused and named", (v, rule, says in why), ("deny", "outside", True))
    for name, cmd in [("`<<<`", "cat <<<x; git push origin feat/x"),
                      ("`{` `}`", "git push origin feat/{x}"),
                      ("`*`", "git push origin feat/*"), ("`?`", "git push origin feat/?"),
                      ("`[`", "git push origin feat/[x]"), ("`#`", "git push origin feat/x #c"),
                      ("a backslash", "git push origin feat/\\x"), ("`$\"`", 'git push origin $"feat/x"'),
                      ("`$'`", "git push origin $'feat/x'"), ("`$(`", "git push origin $(echo feat/x)"),
                      ("`${…op…}`", "git push origin ${B:-feat/x}"),
                      ("a backtick inside double quotes", 'git push origin "`echo feat/x`"'),
                      ("a backslash inside double quotes", 'git push origin "feat\\/x"'),
                      ("`>&` with a non-digit", "git push origin feat/x >&-"),
                      ("`>&` with a word", "git push origin feat/x >&f"),
                      ("two redirections in a row", "git push origin feat/x > >f"),
                      ("a redirection with no target", "git push origin feat/x >"),
                      ("a redirection with no target before a separator", "git push origin feat/x >; echo"),
                      ("`~`", "git push origin ~/x"), ("`!`", "! git push origin feat/x"),
                      ("`(`", "(git push origin feat/x)"), ("non-ASCII", "git push origin feat/é"),
                      ("an unbalanced quote", "git push origin 'feat/x")]:
        case(f"outside: {name} is refused", d(cmd), "deny outside")
    # the lexer: what it accepts, read exactly
    case("lex: quotes are removed and quoted separators are text",
         lex("git 'a ; b' \"c | d\" e'f'g"), [["git", "a ; b", "c | d", "efg"]])
    case("⭐ lex: a quoted `;` does not split", d("git -c alias.x='; git status' push origin master"),
         "deny default-branch")
    case("lex: a newline separates commands", d("git push origin feat/x\necho master"), "allow")
    case("lex: every separator splits", lex("a;b&c|d\ne&&f||g"),
         [["a"], ["b"], ["c"], ["d"], ["e"], ["f"], ["g"]])
    case("⭐ lex: a redirection's target is dropped, never a word", lex("git push o m >f x 2>g <h"),
         [["git", "push", "o", "m", "x"]])
    case("lex: a glued redirection leaves the word before it", lex("git push o master>/dev/null"),
         [["git", "push", "o", "master"]])
    case("lex: `2>&1` names descriptors, not words", lex("git push o m 2>&1"), [["git", "push", "o", "m"]])
    case("lex: a QUOTED digit before `>` is a word", lex("git push o '2'>f"), [["git", "push", "o", "2"]])
    case("lex: `&>`, `>>`, `>|` take a target", lex("a &>f b >>h d >|i e"), [["a", "b", "d", "e"]])
    case("lex: parameters are words of unknown value", lex('a $X "b $Y" ${Z}'),
         [["a", SPLIT, "b " + UNKNOWN, SPLIT]])
    # judging: git's global options
    case("⭐ judge: an unknown git global option in a push command is refused",
         d("git --frobnicate push origin feat/x"), "deny option")
    case("judge: an unknown git global option with no push word is allowed", d("git --frobnicate status; echo push"),
         "allow")
    case("⭐ judge: --attr-source takes a value (C-F2)", d("git --attr-source stash push origin master"),
         "deny default-branch")
    case("judge: `-c` takes its value even when it is `push`", d("git -c push origin master"), "deny unjudged")
    case("judge: an `=` global option is one word", d("git --git-dir=.git push origin master"),
         "deny default-branch")
    case("judge: a bare global flag stands alone", d("git --no-pager push origin master"), "deny default-branch")
    # judging: push's own options
    case("⭐ judge: an unknown push option is refused, not skipped", d("git push --repo=x origin feat/x"),
         "deny option")
    case("judge: --force is rule 2", d("git push --force origin feat/x"), "deny force")
    case("judge: -f is rule 2", d("git push -f origin feat/x"), "deny force")
    case("judge: --no-verify is rule 2", d("git push --no-verify origin feat/x"), "deny no-verify")
    case("judge: --force-with-lease=… is allowed", d("git push --force-with-lease=feat/x origin feat/x"), "allow")
    case("judge: -o takes its value", d("git push -o x master"), "allow")
    case("judge: the force escape allows --force", d("ALLOW_DANGEROUS_PUSH=1 git push --force origin feat/x"),
         "allow")
    case("judge: the force escape allows --no-verify",
         d("ALLOW_DANGEROUS_PUSH=1 git push --no-verify origin feat/x"), "allow")
    case("judge: the force escape does not allow an unknown option",
         d("ALLOW_DANGEROUS_PUSH=1 git push --mirror origin"), "deny option")
    case("judge: the BRANCH escape does not grant a force", d("ALLOW_DEFAULT_BRANCH_PUSH=1 git push -f origin feat/x"),
         "deny force")
    # judging: destinations
    case("⭐ judge: a `+` refspec is a force", d("git push origin +feat/x"), "deny force")
    case("judge: +master is rule 1 even with the force escape", d("ALLOW_DANGEROUS_PUSH=1 git push origin +master"),
         "deny default-branch")
    case("judge: the destination is after the LAST `:`", d("git push origin feat/x:master"), "deny default-branch")
    case("judge: a delete of the default branch is rule 1", d("git push origin :master"), "deny default-branch")
    case("judge: refs/heads/ is stripped", d("git push origin HEAD:refs/heads/master"), "deny default-branch")
    case("⭐ judge: heads/ is stripped (C-F6)", d("git push origin HEAD:heads/master"), "deny default-branch")
    case("⭐ judge: HEAD is the current branch", d("git push origin HEAD", M), "deny default-branch")
    case("judge: @ is the current branch", d("git push origin @", M), "deny default-branch")
    case("judge: HEAD on a feature branch is allowed", d("git push origin HEAD"), "allow")
    case("⭐ judge: a bare `git push` on the default branch is rule 1", d("git push", M), "deny default-branch")
    case("judge: `git push origin` on the default branch is rule 1", d("git push -u origin", M),
         "deny default-branch")
    case("judge: a bare `git push` on a feature branch is allowed", d("git push"), "allow")
    case("judge: the branch escape lifts rule 1", d("ALLOW_DEFAULT_BRANCH_PUSH=1 git push origin master"), "allow")
    case("⭐ judge: no remote lifts rule 1", d("git push origin master", has_remote=False), "allow")
    case("judge: no default branch lifts rule 1", d("git push origin master", default=""), "allow")
    case("judge: no default branch lifts rule 1 even when the current branch is unknown", d("git push", "", ""),
         "allow")
    case("judge: no remote does not lift rule 2", d("git push -f origin feat/x", has_remote=False), "deny force")
    # judging: subcommands and commands
    case("⭐ judge: `push` is not inert — every push is judged", d("git stash list; git push origin master"),
         "deny default-branch")
    case("judge: an INERT subcommand's push words are text", d('git commit -m "git push origin master"'), "allow")
    case("judge: another subcommand holding a push word is refused", d("git rebase --exec 'git push' master"),
         "deny unjudged")
    case("judge: a TEXT command's words are text", d('gh pr create --title "push to master"'), "allow")
    case("⭐ judge: a code runner holding a push word is refused (C-F6)", d("echo m | xargs git push origin"),
         "deny code-runner")
    case("judge: a code runner reading stdin is refused", d("echo 'git push o m' | python3"), "deny code-runner")
    case("judge: a code runner given -c is refused", d("bash -c x; echo push"), "deny code-runner")
    case("judge: a code runner given a script is allowed", d("bash scripts/x.sh && git push origin feat/x"), "allow")
    case("judge: an unknown command holding a push word is refused", d("legit push origin master"), "deny unjudged")
    case("judge: a PATH to git is read as git", d("/usr/bin/git push origin feat/x"), "allow")
    case("judge: an unknown command with no push word is allowed", d("make-thing; git push origin feat/x"), "allow")
    case("judge: leading assignments and reserved words are skipped", d("if true; then A=1 git push origin master; fi"),
         "deny default-branch")
    # judging: words of unknown value
    case("⭐ judge: a parameter as a destination is refused", d("git push origin $B"), "deny unjudged")
    case("judge: a quoted parameter as a destination is refused", d('git push origin "$B"'), "deny unjudged")
    case("judge: a parameter as the command word is refused", d("X=x; $X; echo push"), "deny unjudged")
    case("judge: a parameter as a git subcommand is refused", d("git $P origin master; echo push"), "deny unjudged")
    case("judge: a parameter given to a runner of its arguments is refused", d("env $C; echo push"),
         "deny code-runner")
    case("judge: a parameter given to a script runner is allowed (a script path)",
         d('python3 "$S/x.py" && git push origin feat/x'), "allow")
    case("judge: a double-quoted -C value is allowed", d('git -C "$W" push origin feat/x'), "allow")
    case("⭐ judge: an UNQUOTED -C value is refused (bash may split it into more words)",
         d("git -C $W push origin feat/x"), "deny unjudged")
    case("judge: a parameter in an inert git command is allowed", d('git commit -m "$M" && git push origin feat/x'),
         "allow")

    # ── the CLI contract the hook reads ──
    r = subprocess.run([sys.executable, __file__, "decide", "feat/x", "master", "1"],
                       input="git push origin master", capture_output=True, text=True)
    case("decide prints `deny <rule> <reason>`", (r.returncode, r.stdout.split(" ", 2)[:2]), (0, ["deny", "default-branch"]))
    r = subprocess.run([sys.executable, __file__, "decide", "feat/x", "master", "1"],
                       input="git push origin feat/x", capture_output=True, text=True)
    case("decide prints exactly `allow`", (r.returncode, r.stdout), (0, "allow\n"))
    r = subprocess.run([sys.executable, __file__, "decide", "feat/x", "master", "0"],
                       input="git push origin master", capture_output=True, text=True)
    case("decide reads has_remote", r.stdout, "allow\n")
    r = subprocess.run([sys.executable, __file__, "bogus"], capture_output=True, text=True)
    case("an unknown mode is a usage error", r.returncode, 2)
    # X-F1 (Codex's input): `-c ` sixty times. The read must finish well inside the deadline, with the right answer.
    xf1 = 'echo "git ' + "-c " * 60 + 'x y"; git push origin master'
    try:
        r = subprocess.run([sys.executable, __file__, "decide", "feat/x", "master", "1"], input=xf1,
                           capture_output=True, text=True, timeout=10)
        got = (r.returncode, r.stdout.split(" ", 2)[:2])
    except subprocess.TimeoutExpired:
        got = "TIMED OUT after 10 s"
    case("⭐ X-F1: sixty `-c` is decided inside the deadline", got, (0, ["deny", "default-branch"]))
    # The deadline itself: a `decide` run whose stdin never closes stalls, and SIGALRM's DEFAULT action must end it.
    p = subprocess.Popen([sys.executable, __file__, "decide", "feat/x", "master", "1"], stdin=subprocess.PIPE,
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
    case("⭐ X-F1: a stalled `decide` run is ended by its own deadline (SIGALRM)", got, -signal.SIGALRM)

    # ── the bash-agreement check: the lexer against /bin/bash, and each control must redden it ──
    strings = _oracle_strings()
    with tempfile.TemporaryDirectory() as td:
        runs = _bash_runs(strings, td)
    if runs is None or len(runs) != len(strings):
        case("⛔ the bash-agreement check RAN (/bin/bash present, one record per string) — else NOT RUN",
             None if runs is None else len(runs), len(strings))
    else:
        case("the bash-agreement check RAN (/bin/bash present, one record per string)", len(runs), len(strings))
        for (name, s), ran_ in zip(ORACLE_INPUTS, runs):
            try:
                cmds = lex(s)
            except Outside as e:
                cmds = f"OUTSIDE: {e}"
            agree = not isinstance(cmds, str) and bool(ran_) and \
                all(any(p.match(x) for p in _oracle_patterns(cmds)) for x in ran_)
            case(f"agreement: {name} is accepted, bash ran something, and the lexer reported all of it", agree, True)
        acc, unsafe, bad = _oracle(lex, strings, runs)
        case("⭐ agreement: every invocation bash ran was reported by the lexer (0 unsafe)", (unsafe, bad), (0, []))
        case("agreement: the generator is not vacuous (over 150 accepted strings)", acc > 150, True)
        for name, find, repl in ORACLE_CONTROLS:
            broken = _variant_lexer(find, repl)
            got = "anchor not found once" if broken is None else _oracle(broken, strings, runs)[1] > 0
            case(f"⭐ control: the check REDDENS when {name}", got, True)

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
            ("hook: `git log --grep push` is allowed on a feature branch", "git log --grep push", "allow"),
            ("hook: `echo \"git push later\"` is allowed on a feature branch", 'echo "git push later"', "allow"),
            ("⭐ hook: X-F1 — Codex's sixty `-c` input is REFUSED, not hung", xf1, "deny"),
            ("hook: C-F1 r1 — a line continuation before master is refused", "git push \\\n  origin master", "deny"),
            ("hook: C-F2 — a commit message naming push and master, then a feature push, is allowed",
             'git commit -m "push the fix, not master" && git push origin feat/x', "allow"),
            ("hook: C-F2 — `git stash push` naming master is allowed", 'git stash push -m "before master merge"',
             "allow"),
            ("hook: C-F2 — a feature push, then `--title \"Do not push to master\"`, is allowed",
             'git push origin feat/x && gh pr create --title "Do not push to master" --body-file b', "allow"),
            ("hook: `2>&1` after a feature push is allowed", "git push -u origin feat/x 2>&1", "allow"),
            ("hook: `git log --oneline --grep \"push to master\"` is allowed (log is inert)",
             'git log --oneline --grep "push to master"', "allow"),
            ("⚠ hook: the BOUND — a feature push in a subshell is REFUSED (outside)",
             "(cd . && git push origin feat/x)", "deny"),
            ("⭐ hook: X-F1 r2 — a push to master before a `#` decoy is refused",
             "/usr/bin/git push origin master # git push origin feat/x", "deny"),
            ("⭐ hook: X-F1 r2 — a quoted `;` in -c does not hide the second push",
             "git push origin feat/x; git -c alias.x=';' push origin master", "deny"),
            ("⭐ hook: X-F2 r2 — a quoted `>` does not eat --force",
             "git push origin feat/x --push-option='>' --force", "deny"),
            ("hook: X-F2 r2 — a quoted `>` does not eat --no-verify",
             "git push origin feat/x --push-option='>' --no-verify", "deny"),
            ("hook: X-F2 r2 — a quoted `>` does not eat master", "git push origin --push-option='>' master", "deny"),
            ("⭐ hook: X-F3 r2 — a quoted `;git stash` does not exempt a push to master",
             "git -c alias.x=';git stash' push origin master", "deny"),
            ("hook: X-F3 r2 — ... nor a core.hooksPath",
             "git -c alias.x=';git stash' -c core.hooksPath=/tmp push origin feat/x", "deny"),
            ("hook: X-F3 r2 — ... nor ALLOW_PLAN_LEAK",
             "ALLOW_PLAN_LEAK=1 git -c alias.x=';git stash' push origin feat/x", "deny"),
            ("hook: `git log --grep \"push --force\"` is allowed (log is inert)", 'git log --grep "push --force"',
             "allow"),
            ("hook: X-F4 r2 — `git stash push -m \"git push origin master\"` is allowed",
             'git stash push -m "git push origin master"', "allow"),
            ("hook: a quoted `>` in a feature push's option value is allowed",
             "git push origin feat/x --push-option='>'", "allow"),
            ("⚠ hook: the BOUND — a `#` comment beside a feature push is REFUSED (outside)",
             "git push origin feat/x # not master", "deny"),
            ("⚠ hook: the BOUND — a `$(` beside a feature push is REFUSED",
             'cd "$(git rev-parse --show-toplevel)" && git push origin feat/x', "deny"),
            ("⚠ hook: the BOUND — an unbalanced quote beside a push is REFUSED", 'git push origin "feat/x', "deny"),
            ("⚠ hook: the BOUND — `bash -c` running a feature push is REFUSED", "bash -c 'git push origin feat/x'",
             "deny"),
            ("hook: the coordinator's push line is allowed",
             "python3 s.py . | tail -1 | grep -q 'hits: 0' && git push -q origin HEAD:feat/x", "allow"),
            # round 3: each Claude repro, through the delivered hook
            ("⭐ hook: C-F1 r3 — a heredoc body does not hide a push to master",
             "cat <<EOF\ngit stash list '\nEOF\ngit push origin master # '", "deny"),
            ("⭐ hook: C-F2 r3 — --attr-source does not make stash the subcommand",
             "git --attr-source stash push origin master", "deny"),
            ("⭐ hook: C-F3 r3 — brace expansion is refused", "git push origin {master,}", "deny"),
            ("hook: C-F3 r3 — a glob is refused", "/usr/bin/gi? push origin master", "deny"),
            ("⭐ hook: C-F4 r3 — `$\"…\"` is refused", 'git push origin $"master"', "deny"),
            ("⭐ hook: C-F5 r3 — `-uf` is refused", "git push -uf origin feat/x", "deny"),
            ("hook: C-F5 r3 — `--no-veri` is refused", "git push --no-veri origin feat/x", "deny"),
            ("hook: C-F6 r3 — xargs is refused", "git push origin feat/x; echo master | xargs git push origin", "deny"),
            ("hook: C-F6 r3 — heads/master is refused", "git push origin HEAD:heads/master", "deny"),
        ]:
            case(name, _hook(work, cmd)[0], want)
        dd, why = _hook(work, 'cd "$(pwd)" && git push origin feat/x')
        case("hook: an OUTSIDE refusal names the construct, says NOT CHECKED and gives the remedy",
             (dd, "NOT CHECKED" in why, "`$`" in why or "$(" in why, "git push -u origin <branch>" in why),
             ("deny", True, True, True))
        dd, why = _hook(work, "git push -uf origin feat/x")
        case("hook: an OPTION refusal names the option", (dd, "`-uf`" in why), ("deny", True))
        dd, why = _hook(work, 'git "push" origin master')
        case("hook: a default-branch refusal names the branch", (dd, "'master'" in why), ("deny", True))
        dd, why = _hook(work, "git push --force origin feat/x")
        case("hook: a force refusal offers --force-with-lease", (dd, "--force-with-lease" in why), ("deny", True))
        _git(work, "checkout", "-q", "master")
        for name, cmd, want in [
            ("hook: `git log --grep push` is allowed on the default branch", "git log --grep push", "allow"),
            ("hook: `echo \"git push later\"` is allowed on the default branch", 'echo "git push later"', "allow"),
            ("hook: a command without the word push is untouched on the default branch", "git status", "allow"),
            ("hook: `echo push; git status` is allowed on the default branch", "echo push; git status", "allow"),
            ("hook: C-F2 — `git stash push -m wip` is allowed on the default branch", "git stash push -m wip",
             "allow"),
            ("hook: a bare `git push` on the default branch is refused", "git push", "deny"),
            ("hook: `git push origin HEAD` on the default branch is refused", "git push origin HEAD", "deny"),
        ]:
            case(name, _hook(work, cmd)[0], want)
        _git(work, "checkout", "-q", "--detach")
        case("hook: a detached HEAD pushing HEAD to a feature branch is allowed",
             _hook(work, "git push origin HEAD:feat/y")[0], "allow")
        case("hook: a detached HEAD pushing HEAD:master is refused", _hook(work, "git push origin HEAD:master")[0],
             "deny")
        # The detector cannot run, or dies -> REFUSED, never allowed.
        lone = Path(td) / "lone" / ".claude" / "hooks"
        lone.mkdir(parents=True)
        (lone / HOOK.name).write_text(HOOK.read_text())
        dd, why = _hook(work, "git push origin feat/x", hook=lone / HOOK.name)
        case("hook: a missing detector REFUSES and says NOT CHECKED", (dd, "NOT CHECKED" in why), ("deny", True))
        for label, body, rc in [
            ("ended by its deadline (SIGALRM, 142)", "import os, signal\nos.kill(os.getpid(), signal.SIGALRM)\n",
             "deadline"),
            ("not found (127)", "import sys\nsys.exit(127)\n", "exited 127"),
            ("killed (SIGKILL, 137)", "import os, signal\nos.kill(os.getpid(), signal.SIGKILL)\n", "exited 137"),
            ("crashed (SIGSEGV, 139)", "import os, signal\nos.kill(os.getpid(), signal.SIGSEGV)\n", "exited 139"),
            ("terminated (SIGTERM, 143)", "import os, signal\nos.kill(os.getpid(), signal.SIGTERM)\n", "exited 143"),
            ("printing nothing, rc 0", "pass\n", "printed ''"),
            ("printing a bare `deny`, rc 0", "print('deny')\n", "printed 'deny'"),
            ("printing an unknown verdict, rc 0", "print('allowed')\n", "printed 'allowed'"),
        ]:
            stub = Path(tempfile.mkdtemp(dir=td))
            (stub / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)
            (stub / "scripts").mkdir(exist_ok=True)
            (stub / ".claude" / "hooks" / HOOK.name).write_text(HOOK.read_text())
            (stub / "scripts" / Path(__file__).name).write_text(body)
            dd, why = _hook(work, "git push origin feat/x", hook=stub / ".claude" / "hooks" / HOOK.name)
            case(f"hook: a detector {label} REFUSES and says so", (dd, "NOT CHECKED" in why, rc in why),
                 ("deny", True, True))

    print(f"\n{ran - failures}/{ran} self-test cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
