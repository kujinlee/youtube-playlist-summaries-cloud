#!/usr/bin/env python3
"""Back up what a Bash `rm` would delete BEFORE it runs, or refuse the call (backlog #685).

WHY THIS EXISTS. The owner's rule (11-20 09:08, the `no-command-approval-ceremony` memory): before an `rm`, make a
temporary backup instead of asking for approval — asking is ceremony, a backup is a gate. The same day the session ran
11 `rm`s of its own temp files (`../b.tmp`, `../e.txt` under `.claude/worktrees/`) and backed up none, with the rule
in the always-loaded memory index. MEASURED from the session transcript, so it was not a recall failure: each `rm` was
cleanup appended to a longer command and never registered as a delete. A convention catches only what is read; this
hook reads every Bash call.

THE DESIGN: the hook MAKES the backup (it does not ask the agent for one). For each `rm` it can see, every target that
exists is copied — a symlink as the link, a directory whole — to

    $RM_BACKUP_ROOT (default ~/.claude/rm-backups) / <session_id> / <stamp> / <the target's absolute path>

and one line is appended to `<root>/log.jsonl` (the command, the cwd, each target and its copy). Then the call is
allowed. Restoring is a `cp -a` back from that tree. Backups older than KEEP_DAYS are pruned on each run.

THE DECISION, for a PreToolUse payload (the first that applies wins):

    allow        the tool is not Bash, or the command has no `rm` in a command position
    NOT CHECKED  the payload or command cannot be read (stderr, exit 1: allowed, and said)
    deny         an `rm` whose targets the hook cannot SEE: `xargs rm`, `-exec rm`, `find -delete`, `find -L`, a target
                 holding `$(`, a backtick, a brace list or a variable with no known value, a RELATIVE target after a
                 `cd` the hook cannot follow (a `$(mktemp …)` value is unknown: r2 S21); and a command substitution the lexer cannot split (an unquoted heredoc body, a
                 double-quoted string) whose text holds an `rm` word; a command NAME that is a glob or brace list
                 that may expand to `rm`/`find`/`xargs` (`/bin/r? v`, `{rm,v}`); after `eval`/`source`/`.`, any
                 relative or variable target
    deny         the targets total more than MAX_BYTES or MAX_FILES (too large to copy on every call)
    deny         a copy failed (the `rm` must not run without its backup)
    allow        every visible target is backed up, needs none (missing, inside this session's scratchpad or the
                 backup root), and the copies are logged

WHAT IS READ. Heredoc bodies are removed first (their text is data, not commands). The rest is split into words by
`shlex` with the shell operators as punctuation; a word is in a COMMAND POSITION at the start and after `;`, `&`,
`&&`, `|`, `||`, `(`, a newline, or `then`/`do`/`else`/`{`. Leading `NAME=value` words are skipped (and remembered:
a later `$NAME` expands to it — but not past the subshell or pipeline part that set it). `$'…'` is decoded as bash
decodes it, and a backtick substitution is read as the `$(…)` it is. `\\rm` and `/bin/rm` count. Any command NOT in
NOT_RUNNERS (`echo`, `grep`, `git`, …) is read as a possible runner: a later standalone `rm` word in it starts an
`rm` call (`sudo -u root rm x`, `timeout 5 rm x`) — too wide costs an extra backup. `git rm` is not an `rm` (git
holds a tracked file). The working directory starts at the payload's `cwd` (so does `$PWD`) and
follows a top-level `cd <literal>`, moving `$PWD`/`$OLDPWD`; any other `cd` (inside `(…)` or a compound, `cd -`, after
`||`, unresolvable) makes it UNKNOWN. A `cd` into a directory that does not exist now, or after a command in its own
`&&` chain, is followed only to the end of that chain (r2 R2-4). A variable set by `for`, `read`, `printf -v`,
`getopts`, `mapfile`, `unset`, `declare -n/-a/-A/-i/-l/-u/-c` (then and on every later `X=v`, r2 S22), or under a guard that may not run
unless it already held that value (r2 S20), is UNKNOWN; a nameref's assignment makes EVERY variable unknown (r2 S15); `export`/`declare`/`local` X=v set it. A `)`
is a `case` pattern only after `case W in` or `;;`/`;&`/`;;&` (r2 S16). Targets are expanded for `~`,
`$VAR`/`${VAR}`, `${V:-x}`/`${V-x}`/`${V:=x}` (assigned earlier in the command, else the hook's environment) and
globs; a variable's value holding blanks is backed up whole AND word by word (the quotes are gone). A glob matching
nothing, like a missing file, needs no backup. `T=$(mktemp …)` is UNKNOWN — no exemption, it is a taint the hook cannot track
(r2 S13/S14/R2-5/S17/S21) — except `T=$(mktemp [-d] /literal/scratchpad/x.XXXX)`, which is the glob of the names it
can make, inside the scratchpad, so needs no backup: make temp dirs there.

⚠ BOUNDS, stated: an `rm` the shell builds at run time is not seen and not backed up — inside a quoted string
(`trap 'rm -f "$T"' EXIT`, `bash -c "rm x"`, `eval`), in a script file the command runs, or by another language
(`python -c 'os.remove(…)'`). `unlink` and `rmdir` are not gated (`rmdir` removes only an empty directory). A heredoc
whose delimiter is not on a line of its own takes the rest of the command as its body, as bash does: at worst an extra
backup or a refusal, never a missed `rm` in real command text. A command NAME from an unknown variable (`$X v`) is
not seen, nor is a glob word found after a runner's options (`timeout 5 /bin/r? v`). Containment in an exempt place is
judged on the ENTRY `rm` removes (its last link not followed). The environment is the HOOK's, not the shell's after
earlier commands ran (a `source` is not followed).

EXIT CODES: `--hook` 0 = allowed (silent) or denied (the decision on stdout as JSON) · 1 = NOT CHECKED (allowed,
said on stderr). `--self-test` 0 = every case passed, 1 = a case failed.

    python3 scripts/check-rm-backup.py --self-test  # 112 cases
"""
from __future__ import annotations

import datetime as _dt
import fnmatch
import glob
import json
import os
import re
import shlex
import shutil
import sys
import tempfile
from pathlib import Path

MAX_BYTES = 256 * 1024 * 1024
MAX_FILES = 20_000
KEEP_DAYS = 14
SEPARATORS = {";", "&", "&&", "|", "||", "|&", "(", ")", "\n", ";;", ";&", ";;&"}
KEYWORDS = {"then", "do", "else", "elif", "{", "}", "!", "if", "while", "until"}
LOOK_THROUGH = {"sudo", "command", "env", "nice", "time", "nohup", "exec", "builtin"}     # r2 R2-7: `builtin cd`
# commands that never run their arguments: a later word `rm` is data to them. Every OTHER command is read as a
# possible runner (`timeout 5 rm x`, `sudo -u root rm x`): a later standalone `rm` word starts an `rm` call. Too
# wide costs an extra backup; too narrow would miss a deletion (r1 R1-6 and the push-time review).
NOT_RUNNERS = {"echo", "printf", "grep", "egrep", "fgrep", "rg", "git", "gh", "man", "which", "type", "whatis",
               "apropos", "help", "alias", "unalias", "hash", "cd", "pushd", "popd", "test", "[", "[[", "cat",
               "ls", "head", "tail", "wc", "sort", "uniq", "diff", "sed", "awk", "jq", "tr", "cut", "less", "more",
               "tee", "export", "declare", "local", "readonly", "unset", "set", "shift", "read", "return", "exit",
               "true", "false", ":"}     # never `for`/`case`/`function`: their bodies run (push-time review)
# `rm` as a word in text the lexer does not split into commands, after quote characters are dropped (`r\m`, `"r"m`)
RM_WORD = re.compile(r"(?<![A-Za-z0-9_.-])(?:[A-Za-z0-9_./-]*/)?rm(?![A-Za-z0-9_.-])")
ANSI_ESCAPE = re.compile(r"\\(x[0-9A-Fa-f]{1,2}|u[0-9A-Fa-f]{1,4}|U[0-9A-Fa-f]{1,8}|[0-7]{1,3}|c.|.)", re.S)
ANSI_SIMPLE = {"n": "\n", "t": "\t", "r": "\r", "a": "\a", "b": "\b", "e": "\x1b", "E": "\x1b", "f": "\f",
               "v": "\v", "\\": "\\", "'": "'", '"': '"', "?": "?"}
REDIRECTS = {"<", ">", ">>", "<<", "<<<", ">&", "<&", "&>", "&>>", ">|"}
WORD_START = " \t\r\n;&|()<>"     # a `#` after one of these opens a comment
ASSIGN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", re.S)
OPERATOR = re.compile(r"&>>|<<<|&&|\|\||;;&|;;|;&|\|&|>>|<<|&>|>&|<&|>\||[;&|()<>\n]")
VAR = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))")
DEFAULT = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(:?)([-=?])([^}]*)\}")      # `${S:-x}` `${S-x}` `${S:=x}` `${S:?}`
PUNCT = ";&|()<>\n"
PROTECT = {ord(c): chr(0xE000 + k) for k, c in enumerate(PUNCT)}     # a QUOTED operator character (r2 R2-11)
UNPROTECT = {ord(v): k for k, v in PROTECT.items()}     # r2 R2-11 fold: keyed by code point, or nothing is restored
BRACE = re.compile(r"(?<!\$)\{[^}]*(,|\.\.)[^}]*\}")
SETTERS = {"export", "declare", "local", "readonly", "typeset"}
COMPOUND_OPEN, COMPOUND_CLOSE = {"if", "while", "until", "{"}, {"fi", "done", "esac", "}"}


HEREDOC_RM = ("an unquoted heredoc body runs a command substitution with an `rm` the hook does not read; quote the "
              "delimiter (`<<'EOF'`)")
FIND = "\0find"     # marks a `find … -delete` / `-exec rm` call: its start paths follow


class Unreadable(Exception):
    """The call cannot be judged: NOT CHECKED, allowed, and said."""


class Refuse(Exception):
    """The `rm` must not run: its targets cannot be seen or backed up."""


class PatternName(Refuse):
    """A command NAME that is a glob or brace list and may expand to `rm`, `find` or `xargs` (r2 R2-9)."""


def _subst_end(text: str, j: int) -> int:
    """The index just past the `)` closing a `$(` whose body starts at `j`; its quotes are its own. Unclosed: the end."""
    depth, quote, n = 1, None, len(text)
    while j < n:
        c = text[j]
        if c == "\\" and quote != "'":
            j += 2
            continue
        if quote:
            quote = None if c == quote else quote
        elif c in "'\"":
            quote = c
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    return n


def substitutions(text: str) -> list[str]:
    """The body of every `$(…)` and backtick substitution in `text`, read as bash reads one in double quotes."""
    bodies, i, n = [], 0, len(text)
    while i < n:
        if text[i] == "\\":
            i += 2
        elif text.startswith("$(", i):
            j = _subst_end(text, i + 2)
            bodies.append(text[i + 2:j - 1] if text[j - 1:j] == ")" else text[i + 2:])
            i = j
        elif text[i] == "`":
            j = i + 1
            while j < n and text[j] != "`":
                j += 2 if text[j] == "\\" else 1
            bodies.append(text[i + 1:j])
            i = j + 1
        else:
            i += 1
    return bodies


def runs_rm(text: str) -> bool:
    """A substitution body holds an `rm` call, read by `rm_calls` itself (push-time review: a word search is
    defeated by `r$X`, and a quote inside the body ends no outer string). Unreadable counts as yes."""
    try:
        return bool(rm_calls(text, "/", {}))
    except Refuse:
        return True


def mentions_rm(text: str) -> bool:
    """`rm` appears as a word once quoting is dropped (`r\\m`, `"r"m`, `$'\\x72m'` all run `rm`)."""
    try:
        text = decode_ansi_c(text)
    except Refuse:
        return True
    return bool(RM_WORD.search(re.sub(r"[\\'\"]", "", text))) or "$'" in text


def decode_ansi_c(text: str) -> str:
    """Every `$'…'` outside quotes replaced by the word bash makes of it, single-quoted (r1 push-time review)."""
    out, i, n, quote = [], 0, len(text), None
    while i < n:
        c = text[i]
        if quote:
            if c == "\\" and quote == '"' and i + 1 < n:
                out.append(text[i:i + 2])
                i += 2
                continue
            quote = None if c == quote else quote
            out.append(c)
            i += 1
        elif c == "\\" and i + 1 < n:
            out.append(text[i:i + 2])
            i += 2
        elif c == "$" and text.startswith("$'", i):
            j = i + 2
            while j < n and text[j] != "'":
                j += 2 if text[j] == "\\" else 1
            if j >= n:
                raise Refuse("an unterminated `$'…'` string cannot be read")
            out.append(shlex.quote(ANSI_ESCAPE.sub(_ansi_char, text[i + 2:j])))
            i = j + 1
        elif c == "$" and text.startswith('$"', i):
            i += 1          # `$"…"` is a translated string: without a catalogue it is `"…"`
        else:
            if c in "'\"":
                quote = c
            out.append(c)
            i += 1
    return "".join(out)


def _ansi_char(m: re.Match) -> str:
    s = m.group(1)
    if s[0] in "xuU" and len(s) > 1:
        code = int(s[1:], 16)
        return chr(code) if code < 0x110000 else "\\" + s     # r2 R2-12: out of range stays literal, as bash 3.2
    if s[0] in "01234567":
        return chr(int(s, 8))
    if s[0] == "c" and len(s) == 2:
        return chr(ord(s[1]) & 31)
    return ANSI_SIMPLE.get(s, "\\" + s)


def _heredoc_word(command: str, i: int) -> tuple[int, bool, str, bool]:
    """At a `<<`: (end, `<<-`, the delimiter after quote removal, quoted?). The delimiter is the WHOLE shell word
    (r2 R2-1: `END-X`, `E"OF"`, `\\EOF`); a word that cannot be read refuses."""
    j = i + 2
    strip = command.startswith("-", j)
    j += strip
    while j < len(command) and command[j] in " \t":
        j += 1
    word, quoted, n, start = [], False, len(command), j
    while j < n and command[j] not in " \t\r\n;&|()<>":
        c = command[j]
        if c == "\\" and j + 1 < n:
            word.append(command[j + 1])
            quoted, j = True, j + 2
        elif c in "'\"":
            end = command.find(c, j + 1)
            if end < 0:
                raise Refuse("a heredoc delimiter with an unterminated quote cannot be read")
            word.append(command[j + 1:end])
            quoted, j = True, end + 1
        else:
            word.append(c)
            j += 1
    if j == start:
        raise Refuse("a heredoc with no delimiter word cannot be read")
    return j, strip, "".join(word), quoted


def _brace_end(text: str, j: int) -> int:
    """The index just past the `}` closing a `${` whose body starts at `j`. Unclosed: the end."""
    depth, quote, n = 1, None, len(text)
    while j < n:
        c = text[j]
        if c == "\\" and quote != "'":
            j += 2
            continue
        if quote:
            quote = None if c == quote else quote
        elif c in "'\"":
            quote = c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    return n


def strip_heredocs(command: str) -> str:
    """The command with every comment and every heredoc BODY removed, read the way bash reads them.

    One scan that tracks quoting, because both rules depend on it: `#` opens a comment only at the START of a
    word and outside quotes (`a#b` is one word), and `<<` opens a heredoc only outside quotes and never as part
    of `<<<` (a here-string). A heredoc whose delimiter never comes takes the rest of the command as its body,
    as bash does, so nothing after it runs."""
    out, pending = [], []
    i, n, quote, escaped = 0, len(command), None, -1
    while i < n:
        c = command[i]
        if quote == "'":
            quote = None if c == "'" else quote
            out.append(c)
            i += 1
        elif c == "\\" and i + 1 < n:
            out.append(command[i:i + 2])
            escaped = i + 1     # an escaped blank is part of a word: a `#` after it opens no comment (r1 R1-1)
            i += 2
        elif quote == '"' and (command.startswith("$(", i) or c == "`"):
            j = _subst_end(command, i + 2) if c == "$" else command.find("`", i + 1) + 1 or n
            if runs_rm(command[i + 2:j - 1] if c == "$" else command[i + 1:j - 1]):
                raise Refuse("a command substitution inside a double-quoted string runs an `rm` the hook does not "
                             "back up")
            out.append(command[i:j])
            i = j
        elif quote == '"':
            quote = None if c == '"' else quote
            out.append(c)
            i += 1
        elif c in "'\"":
            quote = c
            out.append(c)
            i += 1
        elif c == "$" and command.startswith("$'", i):
            j = i + 2       # `$'…'`: a backslash escapes its quote; decoded after the bodies are gone
            while j < n and command[j] != "'":
                j += 2 if command[j] == "\\" else 1
            out.append(command[i:j + 1])
            i = j + 1
        elif command.startswith("${", i):
            j = _brace_end(command, i + 2)      # r2 R2-10: a subscript's `<<` is a shift; copied whole
            out.append(command[i:j])
            i = j
        elif c == "`":
            j = i + 1
            while j < n and command[j] != "`":
                j += 2 if command[j] == "\\" else 1
            if j >= n:
                raise Refuse("an unterminated backtick substitution cannot be read")
            out.append("$(" + command[i + 1:j] + ")")    # read it as the `$(…)` it is
            i = j + 1
        elif command.startswith("((", i) or command.startswith("$[", i):
            opener, close = ("[", "]") if c == "$" else ("(", ")")
            depth, j = 0, i + (c == "$")
            while j < n:     # arithmetic: its `<<` is a shift, never a heredoc (r1 Claude probe); copied whole
                depth += (command[j] == opener) - (command[j] == close)    # its own bracket only: `a[1]` (push-time review)
                j += 1
                if depth == 0:
                    break
            if any(runs_rm(b) for b in substitutions(command[i:j])):    # unclosed: the rest, all of it read here
                raise Refuse("an arithmetic expression runs a command substitution with an `rm`")
            out.append(command[i:j])
            i = j
        elif c == "#" and (i == 0 or (command[i - 1] in WORD_START and i - 1 != escaped)):
            nl = command.find("\n", i)
            i = n if nl < 0 else nl
        elif (command.startswith("<<", i) and (i == 0 or command[i - 1] != "<")    # `<<<` is a here-string
              and not command.startswith("<<<", i)):
            end, strip, word, literal = _heredoc_word(command, i)
            pending.append((strip, word, literal))
            out.append(command[i:end])
            i = end
        elif c == "\n" and pending:
            out.append(c)
            i += 1
            body: list[str] = []
            while pending and i < n:
                nl = command.find("\n", i)
                line = command[i:] if nl < 0 else command[i:nl]
                i = n if nl < 0 else nl + 1
                strip, word, literal = pending[0]
                if (line.lstrip("\t") if strip else line) == word:
                    pending.pop(0)
                    text = "\n".join(body)     # one `$(` may span lines (push-time review): read the WHOLE body
                    if not literal and any(runs_rm(b) for b in substitutions(text)):
                        raise Refuse(HEREDOC_RM)
                    body = []
                else:
                    body.append(line)
            if pending and not pending[0][2] and any(runs_rm(b) for b in substitutions("\n".join(body))):
                raise Refuse(HEREDOC_RM)     # a body whose delimiter never comes
            if not pending and i <= n and i > 0 and command[i - 1] == "\n":
                i -= 1      # the newline that ends the delimiter line separates commands: keep it
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _protect(text: str) -> str:
    """An operator character that shlex will read as QUOTED or escaped becomes a placeholder, so only an unquoted
    run is an operator (r2 R2-11: `echo ")"`). A backslash-newline outside single quotes is a line continuation,
    removed as bash removes it (`rm a \\<newline>b` names `b`). The quote state mirrors shlex's own."""
    out, i, n, quote = [], 0, len(text), None
    while i < n:
        c = text[i]
        if c == "\\" and quote != "'" and i + 1 < n:
            if text[i + 1] != "\n":
                out.append(c + text[i + 1].translate(PROTECT))
            i += 2
            continue
        if quote:
            quote = None if c == quote else quote
            out.append(c if quote is None else c.translate(PROTECT))
        else:
            quote = c if c in "'\"" else None
            out.append(c)
        i += 1
    return "".join(out)


def words(command: str) -> list[str]:
    """Shell words and operators; a newline is its own operator."""
    text = _protect(decode_ansi_c(strip_heredocs(command)))
    lex = shlex.shlex(text, posix=True, punctuation_chars=PUNCT)
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    lex.commenters = ""     # comments are removed by `strip_heredocs`, which knows where a word starts
    try:
        toks = list(lex)
    except ValueError as exc:
        raise Unreadable(f"the command does not split into shell words ({exc})")
    out = []
    for t in toks:
        # a run of punctuation such as `);` or `;\n` arrives as ONE token: split it into shell operators, longest first
        if t and set(t) <= set(PUNCT):
            out.extend(OPERATOR.findall(t))
        else:
            out.append(t)     # a quoted operator character stays a placeholder until `expand` (r2 S18)
    return out


def expand(word: str, env: dict[str, str | None]) -> str:
    """`~` and `$VAR`; raises Refuse when the value cannot be known."""
    if "$(" in word or "`" in word:
        raise Refuse(f"the target `{word}` is built by a command substitution")

    def default(m: re.Match) -> str:     # r2 R2-8: the default replaces an unset (or, with `:`, empty) value
        name, colon, op, alt = m.groups()
        if op == "?" or (name in env and env[name] is None):
            return "${" + name + "}"     # `${S:?}` names S; an unknown value refuses below
        if name in env and not (colon and env[name] == ""):
            return env[name]
        val = expand(alt, env) if alt else ""
        if op == "=":
            env[name] = val
        return val
    word = DEFAULT.sub(default, word)
    word = word.replace("$$", "*")    # the shell's pid: a glob over every pid backs up a superset
    if BRACE.search(word):     # `{a,b}` and the range `{1..3}` (r1 Claude probe)
        raise Refuse(f"the target `{word}` is a brace list")

    def sub(m: re.Match) -> str:
        name = m.group(1) or m.group(2)
        val = env.get(name)
        if val is None:
            raise Refuse(f"the variable `${name}` in `{word}` has no value the hook can see")
        return val
    word = VAR.sub(sub, word)
    if "$" in word:
        raise Refuse(f"the target `{word}` holds a `$` the hook cannot expand")
    if word == "~" or word.startswith("~/"):
        home = env.get("HOME")
        if not home:
            raise Refuse(f"`~` in `{word}` has no HOME the hook can see")
        word = home + word[1:]
    return word.translate(UNPROTECT)     # r2 R2-11 fold: `rm "a;b"` names `a;b`


def expand_words(word: str, env: dict[str, str | None]) -> list[str]:
    """`expand`, and when a variable's value holds blanks, each blank-separated piece too: the lexer has dropped the
    quotes, so `rm $X` (split) and `rm "$X"` (whole) look alike — back up both readings (r2 R2-3)."""
    val = expand(word, env)
    return [val] + val.split() if "$" in word and re.search(r"\s", val) else [val]


def _mktemp_template(toks: list[str], s: int, scratch: str | None) -> str | None:
    """`toks[s:]` is a substitution body that is exactly `mktemp [-d|-q|-u] /literal/name.XXX…` whose directory is this
    session's scratchpad, closed by `)` and a separator: the glob of the names it can make (`x.????`). Anything else
    is an unknown value (r2: the `mktemp` exemption is dropped — a value, not a taint)."""
    if not scratch or s >= len(toks) or toks[s] != "mktemp":
        return None
    c, words_ = s + 1, []
    while c < len(toks) and toks[c] not in SEPARATORS:
        words_.append(toks[c])
        c += 1
    if not (c < len(toks) and toks[c] == ")" and (c + 1 == len(toks) or toks[c + 1] in (";", "&&", "||", "\n", ")"))):
        return None
    opts, rest = [w for w in words_ if w in ("-d", "-q", "-u")], [w for w in words_ if w not in ("-d", "-q", "-u")]
    if len(rest) != 1 or not os.path.isabs(rest[0]) or re.search(r"[$`*?\[{\\]", rest[0]):
        return None
    m = re.fullmatch(r"(.*/)([^/]*?)(X{3,})", rest[0])
    if not m or scratch not in os.path.realpath(m[1]) + "/":
        return None
    return m[1] + m[2] + "?" * len(m[3])


def rm_calls(command: str, cwd: str, environ: dict[str, str],
             scratch: str | None = None) -> list[tuple[list[str], str | None]]:
    """Each `rm` in a command position: (its expanded target words, the cwd it runs in or None if unknown)."""
    toks = words(command)
    env: dict[str, str | None] = dict(environ)
    env["PWD"] = cwd                     # r2 R2-6: the shell's own, not the hook's
    here: str | None = cwd
    depth = compound = in_case = 0
    in_pat = cond = False        # r2 S16: inside a `case` pattern list; this command may not run
    namerefs: set[str] = set()   # r2 S15: `declare -n` names: an assignment to one sets a variable the hook cannot name
    attrs: set[str] = set()      # r2 S22: names declared -i/-l/-u/-c/-a/-A: a later `X=v` is not stored as `v`
    chained: set[str] = set()    # r2 S20: set only after `&&`: true for the rest of that `&&` chain, unknown after it
    chain_only = False
    cond_cd = risky = False      # r2 R2-4: a `cd` whose outcome is known only inside its chain; a command before it
    assigned_at: dict[str, int] = {}
    calls = []
    i, n = 0, len(toks)
    prev_sep = None
    piped = False

    def setvar(var: str, val: str | None) -> None:
        if depth > 0:
            assigned_at[var] = depth
        if var in namerefs:
            for v in env:
                env[v] = None            # r2 S15: it assigns the variable it refers to
            val = None
        elif piped or var in attrs:
            val = None                   # r2 S22
        elif cond and (var not in env or env[var] != val):
            if chain_only:
                chained.add(var)         # r2 S20: a later `&& rm $X` runs only if this ran
            else:
                val = None               # r2 S20: under a guard, the old value (or unset) or the new one
        env[var] = val

    def value(val: str) -> str | None:
        try:
            return expand(val, env) if val else ""
        except Refuse:
            return None

    while i < n:
        # one simple command: toks[i:j]
        j = i
        while j < n and toks[j] not in SEPARATORS:
            j += 1
        cmd = toks[i:j]
        sep_after = toks[j] if j < n else None
        piped = prev_sep in ("|", "|&", "&") or sep_after in ("|", "|&", "&")
        k = 0
        while k < len(cmd) and cmd[k] in KEYWORDS:
            compound = max(0, compound + (cmd[k] in COMPOUND_OPEN) - (cmd[k] == "}"))
            k += 1
        guarded = k > 0 or compound > 0      # r2 R2-4: under `then`/`do`/`{`/…, a `cd` may not run
        cond = guarded or prev_sep in ("&&", "||")
        chain_only = not guarded and prev_sep == "&&"
        assigns = []
        while k < len(cmd) and (m := ASSIGN.match(cmd[k])):
            assigns.append(m.groups())
            k += 1
        while k < len(cmd) and cmd[k] in LOOK_THROUGH:
            k += 1
            while k < len(cmd) and cmd[k].startswith("-"):
                k += 1
            while k < len(cmd) and ASSIGN.match(cmd[k]):
                k += 1
        args = cmd[k:]
        name = args[0].lstrip("\\") if args else ""
        if "$" in name:
            try:
                name = expand(name, env)       # `X=rm; $X victim`
            except Refuse:
                pass                           # a command name the hook cannot see: a stated BOUND
        first = base = os.path.basename(name)
        header = first == "case" and args[2:3] == ["in"]
        pattern = (in_pat and cmd[:1] != ["esac"]) or (header and len(args) > 3)     # a `case` pattern `x*)`
        pat_list = pattern or header     # r2 S16: its `(` and `)` open and close no subshell
        if pattern:
            pass
        elif BRACE.search(name) or (re.search(r"[*?\[]", base) and any(fnmatch.fnmatchcase(c, base)
                                                                    for c in ("rm", "find", "xargs"))):
            raise PatternName(f"the command name `{name}` is a pattern or brace list that may run `rm`")    # r2 R2-9
        if name and base not in ("rm", "xargs", "find") and name not in NOT_RUNNERS:
            for a in range(1, len(args)):
                w = args[a].lstrip("\\")
                if os.path.basename(w) in ("rm", "xargs", "find") and args[a - 1] not in REDIRECTS:
                    args, name = args[a:], w   # `timeout 5 rm x`, `nice -n 5 find …` (r2 R2-2)
                    break
            base = os.path.basename(name)
        if not args:
            for var, val in assigns:     # a bare assignment sets a shell variable; forgotten when its subshell
                if val == "$" and sep_after == "(":     # closes (S3); piped: None
                    setvar(var, _mktemp_template(toks, j + 1, scratch))    # `T=$(…)`: unknown, but a scratchpad
                elif val == "" and sep_after == "(":                       # `mktemp` template is its glob
                    setvar(var, None)    # an array `X=(a b)`
                else:
                    setvar(var, value(val))
        elif base == "rm":
            targets, opts_done = [], False
            a = 1
            while a < len(args):
                w = args[a]
                if w in REDIRECTS:
                    a += 2
                    continue
                if not opts_done and w == "--":
                    opts_done = True
                elif not opts_done and w.startswith("-") and w != "-":
                    pass
                else:
                    targets.append(w)
                a += 1
            calls.append(([w for t in targets for w in expand_words(t, env)], here))
        elif base == "xargs" and any(os.path.basename(w.lstrip("\\")) == "rm" for w in args[1:]):
            raise Refuse("`xargs rm` deletes targets the hook cannot see")
        elif base == "find" and ("-delete" in args or (
                {"-exec", "-execdir", "-ok", "-okdir"} & set(args)       # `-exec sudo rm {}` is an `-exec rm`
                and any(os.path.basename(w.lstrip("\\")) == "rm" for w in args[1:]))):
            starts = []
            lead, follow = 1, False
            while lead < len(args) and re.fullmatch(r"-[HLPEXdsxf]+", args[lead]):
                if set(args[lead]) & {"L", "f"}:
                    raise Refuse("`find -L` / `-f` reaches targets the hook cannot see")
                follow = follow or "H" in args[lead]
                lead += 1
            if "-follow" in args:
                raise Refuse("`find -follow` reaches targets the hook cannot see")
            for w in args[lead:]:
                if w.startswith("-") or w in ("(", "!"):
                    break
                starts.append(w)
            found = [t for raw in (starts or ["."]) for t in expand_words(raw, env)]
            calls.append(([FIND] + found, here))
        elif name == "cd":
            old = here
            simple = (depth == 0 and not guarded and prev_sep in (None, ";", "&&", "\n")
                      and sep_after in (None, ";", "&&", "\n"))
            if not simple or len(args) != 2 or args[1] == "-":
                here = None
            else:
                try:
                    dest = expand(args[1], env)
                    if os.path.isabs(dest):
                        here = os.path.normpath(dest)
                    elif here is None:
                        pass
                    else:
                        here = os.path.normpath(os.path.join(here, dest))
                except Refuse:
                    here = None
                if here is not None and (risky or not os.path.isdir(here)):
                    cond_cd = True   # r2 R2-4: it may fail or not run; the shell is there only inside its `&&` chain
            env["OLDPWD"], env["PWD"] = old, here
        elif name in ("pushd", "popd"):
            here = env["PWD"] = None
        if first in ("for", "select") and len(args) > 1:
            setvar(args[1], None)                # r2 R2-6: a variable set other than by `NAME=value`
        elif first in ("read", "mapfile", "readarray", "getopts", "unset"):
            for w in args[1:]:
                if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", w):
                    setvar(w, None)
        elif first == "printf" and "-v" in args[:-1]:
            setvar(args[args.index("-v") + 1], None)
        elif first in SETTERS:
            attr = False
            for w in args[1:]:
                if w[:1] in "-+":
                    attr = attr or bool(set(w[1:]) & set("naAilcu"))     # r2 S15/S22: nameref, array, integer, case transform
                    if "n" in w[1:] and first != "export":
                        namerefs.update(ASSIGN.match(x)[1] if ASSIGN.match(x) else x for x in args[1:]
                                        if not x.startswith(("-", "+")))
                elif m := ASSIGN.match(w):
                    setvar(m[1], None if attr else value(m[2]))
                    attrs.update([m[1]] if attr else [])
                elif attr:
                    setvar(w, None)
                    attrs.add(w)
        elif first in ("eval", "source", "."):
            here = None                          # r2 R2-7: the text it runs is not read
            env = dict.fromkeys(env)
        in_case = max(0, in_case + (first == "case") - (first == "esac"))
        if pat_list:
            in_pat = sep_after != ")"
        elif sep_after in (";;", ";&", ";;&"):
            in_pat = True
        elif cmd[:1] == ["esac"]:
            in_pat = False
        if first in ("for", "case", "select", "function"):
            compound += 1
        elif first in COMPOUND_CLOSE:
            compound = max(0, compound - 1)
        risky = risky or bool(args) and not (name == "cd" and here is not None and not cond_cd)
        if sep_after not in ("&&", "|", "|&"):     # `a && b | c && d` is one chain
            if cond_cd:
                here = env["PWD"] = None
            cond_cd = risky = False
            for v in chained:
                env[v] = None
            chained.clear()
        if sep_after == "(" and not pat_list:
            depth += 1        # a `cd` inside a subshell makes the cwd UNKNOWN (conservative: it may not leak out)
        elif sep_after == ")" and not pat_list:    # a `case` pattern's `)` closes no subshell
            depth = max(0, depth - 1)
            for var in [v for v, d in assigned_at.items() if d > depth]:
                env[var] = None                  # bash's outer value is not the one the subshell set
                del assigned_at[var]
        prev_sep = sep_after
        i = j + 1
    return calls


def _entry(path: str) -> str:
    """The directory entry `rm` removes: its parent resolved, its own last name NOT followed (r1 R1-4)."""
    head, tail = os.path.split(path.rstrip("/") or "/")     # never `normpath`: `link/..` is not `.` to the kernel
    if tail in ("", ".", ".."):
        return os.path.realpath(path)
    return os.path.join(os.path.realpath(head or "."), tail)


def _inside(path: str, root: str) -> bool:
    try:
        return os.path.commonpath([_entry(path), os.path.realpath(root)]) == os.path.realpath(root)
    except ValueError:
        return False


def _size(path: str) -> tuple[int, int]:
    """(bytes, files) under path, stopping early once past either cap."""
    if os.path.islink(path) or not os.path.isdir(path):
        return (os.lstat(path).st_size, 1)
    total, count = 0, 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames + [d for d in dirnames if os.path.islink(os.path.join(dirpath, d))]:
            try:
                total += os.lstat(os.path.join(dirpath, f)).st_size
            except OSError:
                pass
            count += 1
            if total > MAX_BYTES or count > MAX_FILES:
                return (total, count)
    return (total, count)


def plan(payload: dict, environ: dict[str, str], root: str) -> list[str]:
    """The absolute paths to back up; raises Refuse or Unreadable."""
    ti = payload.get("tool_input")
    if not isinstance(ti, dict):
        raise Unreadable("`tool_input` is not an object")
    command = ti.get("command")
    if not isinstance(command, str):
        raise Unreadable("`command` is not a string")
    bare = re.sub(r"[\\'\"]", "", command)       # r2 R2-9: `-de""lete` is `-delete`
    no_rm = not mentions_rm(command) and "-delete" not in bare and "$" not in command    # `r$X` builds a name
    if no_rm and not re.search(r"[*?\[{]", bare):
        return []
    cwd = payload.get("cwd")
    if not isinstance(cwd, str) or not os.path.isabs(cwd):
        raise Unreadable("the payload has no absolute `cwd`")
    session = str(payload.get("session_id") or "")
    out: list[str] = []
    try:
        calls = rm_calls(command, cwd, environ, f"/{session}/scratchpad/" if session else None)
    except (Unreadable, Refuse) as exc:
        if no_rm and not isinstance(exc, PatternName):
            return []     # read only for a pattern command name (`/bin/r? v`); anything else names no `rm`
        raise
    for targets, here in calls:
        if targets and targets[0] == FIND:
            # a `find` that deletes: allowed only when every start path is exempt (it needs no backup)
            for t in targets[1:]:
                base = t if os.path.isabs(t) else (os.path.join(here, t) if here is not None else None)
                if base is None or not all(_inside(p, root) or (session and f"/{session}/scratchpad/" in _entry(p) + "/")
                                           for p in (base, os.path.realpath(base))):    # -H, `link/`: where it LEADS
                    raise Refuse("`find -delete` / `-exec rm` outside the session scratchpad deletes targets the "
                                 "hook cannot see")
            continue
        for t in targets:
            if not os.path.isabs(t):
                if here is None:
                    raise Refuse(f"the relative target `{t}` follows a `cd` the hook cannot follow")
                t = os.path.join(here, t)
            matches = (glob.glob(t) if any(c in t for c in "*?[") else []) + [t]   # the lexer drops quotes: a
            for m in dict.fromkeys(matches):     # quoted `'a[1].txt'` is a literal name, so read it both ways
                follow = m.endswith("/")         # `rm -r link/` deletes what the link points at, on macOS
                m = _entry(m)                    # the parent RESOLVED, so `lnk/../x` is where the kernel finds it
                if not os.path.lexists(m):
                    continue
                if follow and os.path.islink(m):
                    m = os.path.realpath(m)
                if _inside(m, root) or (session and f"/{session}/scratchpad/" in _entry(m) + "/"):
                    continue
                out.append(m)
    total, count = 0, 0
    for p in out:
        b, c = _size(p)
        total, count = total + b, count + c
        if total > MAX_BYTES or count > MAX_FILES:
            raise Refuse(f"the targets are too large to back up on every call (over {MAX_BYTES >> 20} MB or "
                         f"{MAX_FILES} files)")
    return out


def back_up(paths: list[str], payload: dict, root: str, now: _dt.datetime) -> list[tuple[str, str]]:
    """Copy each path under root/<session>/<stamp>/; returns (original, copy) pairs. Raises Refuse on a failure."""
    session = re.sub(r"[^A-Za-z0-9_.-]", "_", str(payload.get("session_id") or "no-session"))
    dest_dir = os.path.join(root, session, now.strftime("%Y%m%d-%H%M%S-%f"))
    pairs = []
    for p in paths:
        dest = os.path.join(dest_dir, p.lstrip(os.sep))
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if os.path.isdir(p) and not os.path.islink(p):
                shutil.copytree(p, dest, symlinks=True, dirs_exist_ok=True)
            else:
                shutil.copy2(p, dest, follow_symlinks=False)
        except OSError as exc:
            raise Refuse(f"the backup of `{p}` failed ({exc})")
        pairs.append((p, dest))
    try:
        with open(os.path.join(root, "log.jsonl"), "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"at": now.isoformat(timespec="seconds"), "session": session,
                                 "cwd": payload.get("cwd"), "command": payload["tool_input"]["command"],
                                 "copies": pairs}, ensure_ascii=False) + "\n")
    except OSError as exc:
        raise Refuse(f"the backup log could not be written ({exc})")
    return pairs


def prune(root: str, now: _dt.datetime) -> None:
    """Remove stamp directories older than KEEP_DAYS (they were backups made by this hook)."""
    cutoff = (now - _dt.timedelta(days=KEEP_DAYS)).strftime("%Y%m%d-%H%M%S")
    real_root = os.path.realpath(root)
    for sess in glob.glob(os.path.join(root, "*")):
        if os.path.islink(sess) or not os.path.isdir(sess):
            continue                    # a link here leads out of the root (r1 R1-5)
        for stamp in glob.glob(os.path.join(sess, "[0-9]" * 8 + "-*")):
            if os.path.islink(stamp) or os.path.dirname(os.path.dirname(os.path.realpath(stamp))) != real_root:
                continue
            if os.path.basename(stamp)[:15] < cutoff:
                shutil.rmtree(stamp, ignore_errors=True)


def decide(payload: object, environ: dict[str, str], root: str, now: _dt.datetime) -> str | None:
    """None to allow (after any backup), or a denial reason. Raises Unreadable for NOT CHECKED."""
    if not isinstance(payload, dict):
        raise Unreadable("the payload is not a JSON object")
    if payload.get("tool_name") != "Bash":
        return None
    try:
        paths = plan(payload, environ, root)
        if paths:
            back_up(paths, payload, root, now)
    except Refuse as exc:
        return (f"⛔ REFUSED (backlog #685): {exc}. An `rm` runs only after its targets are backed up, and this hook "
                f"could not do that. Write each target as a literal path (a variable assigned earlier in the SAME "
                f"command is fine), or make temp dirs in the session scratchpad (`mktemp -d \"$SCRATCH/x.XXXX\"` with a "
                f"literal scratchpad path), which needs no backup, or copy the target under {root}/ yourself and delete it with `rm` on the literal path.")
    return None


def main(argv: list[str] | None = None, stdin_bytes: bytes | None = None, env: dict | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--self-test"]:
        return self_test()
    if argv != ["--hook"]:
        print("usage: check-rm-backup.py --hook | --self-test", file=sys.stderr)
        return 2
    environ = dict(os.environ if env is None else env)
    root = environ.get("RM_BACKUP_ROOT") or os.path.expanduser("~/.claude/rm-backups")
    now = _dt.datetime.now()
    try:
        raw = sys.stdin.buffer.read() if stdin_bytes is None else stdin_bytes
        try:
            payload = json.loads(raw.decode("utf-8", "replace"))
        except ValueError:
            raise Unreadable("the payload is not JSON")
        reason = decide(payload, environ, root, now)
    except Unreadable as exc:
        print(f"⚠ check-rm-backup: {exc}; this call was NOT CHECKED for an `rm` without a backup (backlog #685).",
              file=sys.stderr)
        return 1
    if reason:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                 "permissionDecisionReason": reason}}))
        return 0
    try:
        prune(root, now)
    except OSError:
        pass
    return 0


def self_test() -> int:
    """The suite, inside `fixture_git.isolated()` (backlog #382): the repo's rule for every suite."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    failures = []
    passed = 0

    def case(name: str, got: object, want: object) -> None:
        nonlocal passed
        if got == want:
            passed += 1
        else:
            failures.append(f"[FAIL] {name}: got {got!r}, want {want!r}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = os.path.realpath(tmp)
        work = os.path.join(tmp, "repo", "sub")
        root = os.path.join(tmp, "backups")
        scratch = os.path.join(tmp, "sess-1", "scratchpad")
        for d in (work, scratch, os.path.join(work, "dir", "inner")):
            os.makedirs(d, exist_ok=True)
        for f, body in (("a.tmp", "A"), ("b.txt", "B"), ("dir/inner/c", "C")):
            Path(work, f).write_text(body)
        Path(tmp, "repo", "x.tmp").write_text("X")
        Path(scratch, "s.txt").write_text("S")
        os.symlink(os.path.join(work, "b.txt"), os.path.join(work, "link"))
        now = _dt.datetime(2026, 11, 20, 16, 0, 0)
        env = {"HOME": tmp, "KNOWN": work}

        def pay(command, tool="Bash", cwd=work):
            return {"tool_name": tool, "session_id": "sess-1", "cwd": cwd, "tool_input": {"command": command}}

        def targets(command, cwd=work, environ=env):
            try:
                return sorted(os.path.relpath(p, tmp) for p in plan(pay(command, cwd=cwd), environ, root))
            except Refuse:
                return "refused"
            except Unreadable:
                return "not checked"
            except Exception as exc:     # r2 R2-12: a crash is a red CASE, not a dead suite
                return f"crashed: {type(exc).__name__}"

        # ── which `rm`s are seen, and what they back up
        case("the measured failure: `rm ../x.tmp` from a subdirectory is backed up",
             targets("rm ../x.tmp"), ["repo/x.tmp"])
        case("an `rm` appended to a longer command is seen (the 11-20 shape)",
             targets("python3 x.py --self-test | tail -1; rm -f a.tmp b.txt"), ["repo/sub/a.tmp", "repo/sub/b.txt"])
        case("an `rm` after `&&`, `||`, `|` and a newline is seen",
             targets("true && rm a.tmp\nfalse || rm b.txt"), ["repo/sub/a.tmp", "repo/sub/b.txt"])
        case("`rm -rf dir` backs up the directory", targets("rm -rf dir"), ["repo/sub/dir"])
        case("options are not targets; `--` ends them", targets("rm -f -- -f a.tmp"), ["repo/sub/a.tmp"])
        case("an absolute target", targets(f"rm {work}/b.txt"), ["repo/sub/b.txt"])
        case("a glob is expanded relative to the cwd", targets("rm *.tmp"), ["repo/sub/a.tmp"])
        case("a missing target, and a glob matching nothing, need no backup", targets("rm -f nope.txt *.zzz"), [])
        case("a target in this session's scratchpad needs no backup", targets(f"rm {scratch}/s.txt"), [])
        case("a target in ANOTHER session's scratchpad is backed up",
             sorted(os.path.relpath(p, tmp) for p in plan({**pay(f"rm {scratch}/s.txt"), "session_id": "other"},
                                                          env, root)),
             ["sess-1/scratchpad/s.txt"])
        case("`sudo rm`, `command rm`, `\\rm` and `/bin/rm` are seen",
             targets("sudo rm a.tmp; command rm b.txt; \\rm ../x.tmp; /bin/rm dir/inner/c"),
             ["repo/sub/a.tmp", "repo/sub/b.txt", "repo/sub/dir/inner/c", "repo/x.tmp"])
        case("`NAME=value` before an `rm` is skipped, and `env -i rm`", targets("LC_ALL=C rm a.tmp; env -i rm b.txt"),
             ["repo/sub/a.tmp", "repo/sub/b.txt"])
        case("a variable assigned earlier in the command is expanded", targets("D=dir; rm -r $D/inner"),
             ["repo/sub/dir/inner"])
        case("a variable from the environment, and `${VAR}`", targets("rm ${KNOWN}/a.tmp $KNOWN/b.txt"),
             ["repo/sub/a.tmp", "repo/sub/b.txt"])
        case("`~` is expanded", targets("rm ~/repo/x.tmp"), ["repo/x.tmp"])
        case("a top-level `cd` is followed", targets(f"cd {tmp}/repo && rm x.tmp"), ["repo/x.tmp"])
        case("`cd ..; rm` is followed", targets("cd ..; rm x.tmp"), ["repo/x.tmp"])
        case("a symlink is backed up as the link, its referent is not counted twice", targets("rm link"),
             ["repo/sub/link"])

        # ── what is NOT an `rm`
        case("`git rm` is not an `rm`", targets("git rm -q a.tmp"), [])
        case("an `rm` inside a quoted string is not a command", targets("trap 'rm -f a.tmp' EXIT; echo 'rm b.txt'"), [])
        case("`rm` as an argument is not a command", targets("grep -n rm a.tmp; echo rm b.txt"), [])
        case("a word containing rm is not rm (`rmdir`, `perms`, `rm.sh`)", targets("rmdir dir/inner; ./rm.sh a.tmp"), [])
        case("a heredoc body is data, not commands",
             targets("cat > m.txt <<'EOF'\nrm a.tmp\n$(rm b.txt)\nEOF\necho done"), [])
        case("a command after a heredoc is still read",
             targets("cat > m.txt <<EOF\nhello\nEOF\nrm a.tmp"), ["repo/sub/a.tmp"])
        case("a comment is not a command", targets("echo hi  # then rm a.tmp"), [])
        case("an escaped blank ends no word: `\\ #` opens no comment (r1 R1-1)",
             targets("echo foo\\ #; rm a.tmp"), ["repo/sub/a.tmp"])
        case("an unquoted heredoc's command substitution with `rm` is refused; a quoted one is data (r1 R1-2)",
             [targets("cat <<EOF\n$(rm a.tmp)\nEOF"), targets("cat <<'EOF'\n$(rm a.tmp)\nEOF")],
             ["refused", []])
        case("`rm` inside a double-quoted substitution is refused; a backtick one is read (r1)",
             [targets('echo "$(rm a.tmp)"'), targets("echo `rm a.tmp`")], ["refused", ["repo/sub/a.tmp"]])
        case("a wrapper's option values do not hide `rm` (r1 R1-6, push-time S1)",
             targets("sudo -u root rm a.tmp; timeout 5 rm b.txt; nice -n 5 rm ../x.tmp"),
             ["repo/sub/a.tmp", "repo/sub/b.txt", "repo/x.tmp"])
        case("a quote inside a substitution ends no outer string; `r$X` inside one is parsed, not grepped",
             [targets('echo "$(echo "x"; rm a.tmp)"'), targets('echo "$(X=m; r$X a.tmp)"'),
              targets('echo "$(git log --oneline | grep rm)"'), targets("cat <<EOF\n$(date) rm\nEOF")],
             ["refused", "refused", [], []])
        case("`function f { rm x; }` and `find -LH` are seen",
             [targets("function f { rm a.tmp; }"), targets(f"find -LH {scratch} -delete"), targets(f"find -H {scratch} -delete")],
             [["repo/sub/a.tmp"], "refused", []])
        case("`rm` as data to a command that never runs it is not a call", targets("echo rm b.txt; git rm a.tmp"), [])
        case("ANSI-C `$'…'` and quote tricks spell `rm` and are seen (push-time S2)",
             targets("$'rm' a.tmp; $'\\x72m' b.txt; r\\m ../x.tmp"), ["repo/sub/a.tmp", "repo/sub/b.txt", "repo/x.tmp"])
        case("a command name from a known variable is expanded", targets("X=rm; $X a.tmp"), ["repo/sub/a.tmp"])
        case("a variable set in a subshell or a pipeline part is not the outer one (push-time S3)",
             [targets("( X=a.tmp ); rm $X"), targets("X=a.tmp | true; rm $X"), targets("( X=a.tmp; rm $X )")],
             ["refused", "refused", ["repo/sub/a.tmp"]])
        case("`find -L` is refused; `find -H` outside the scratchpad is refused (r2 R2-13)",
             [targets("find -L . -delete"), targets("find -H dir -delete")], ["refused", "refused"])
        case("a `#` inside a word opens no comment (the 11-20 security review)",
             targets("echo a#b; rm a.tmp"), ["repo/sub/a.tmp"])
        case("`<<<` and a quoted `<<` open no heredoc (the 11-20 security review)",
             [targets("cat <<<EOF\nrm a.tmp\nEOF"), targets('echo "<<EOF"\nrm b.txt\nEOF')],
             [["repo/sub/a.tmp"], ["repo/sub/b.txt"]])
        os.symlink(os.path.join(work, "dir"), os.path.join(work, "into-root"))
        case("a link OUTSIDE the backup root to a path inside it is backed up as the link (r1 R1-4)",
             sorted(plan(pay("rm into-root"), env, os.path.join(work, "dir"))), [os.path.join(work, "into-root")])
        case("`rm -r link/` backs up what the link points at (macOS follows it)",
             sorted(os.path.relpath(p, tmp) for p in plan(pay("rm -r into-root/"), env, root)), ["repo/sub/dir"])
        os.remove(os.path.join(work, "into-root"))
        os.symlink(os.path.join(work, "dir", "inner"), os.path.join(work, "lnk"))
        case("`lnk/../x` is found where the kernel finds it, past the link, not lexically",
             sorted(os.path.relpath(p, tmp) for p in plan(pay("rm lnk/../inner/c"), env, root)), ["repo/sub/dir/inner/c"])
        os.remove(os.path.join(work, "lnk"))
        case("a target inside the backup root needs no backup",
             sorted(plan(pay("rm -r dir/inner"), env, os.path.join(work, "dir"))), [])
        case("a non-Bash tool is allowed without reading",
             decide(pay("rm a.tmp", tool="Read"), env, root, now), None)

        # ── what is refused: the targets cannot be seen
        case("a command substitution target is refused", targets("rm $(cat list)"), "refused")
        case("an unknown variable is refused", targets("rm $NOPE/a.tmp"), "refused")
        case("a brace list and a brace range are refused", [targets("rm {a.tmp,b.txt}"), targets("rm f{1..3}")],
             ["refused", "refused"])
        case("a variable from a command substitution is refused", targets("T=$(ls -d x*); rm -f $T"),
             "refused")
        case("`xargs rm` is refused", targets("ls | xargs rm"), "refused")
        case("`/usr/bin/xargs rm`, `/usr/bin/find -delete` and `-exec sudo rm` are refused (r1 Claude probe)",
             [targets("/usr/bin/xargs rm < list"), targets("/usr/bin/find . -delete"),
              targets("find . -exec sudo rm {} \\;")], ["refused", "refused", "refused"])
        case("arithmetic `<<` is a shift, not a heredoc: the `rm` after it is seen (r1 Claude probe)",
             [targets("x=1; y=2; echo $((x<<y))\nrm a.tmp"), targets("(( z = x << y ))\nrm a.tmp"),
              targets("echo $[x<<y]\nrm a.tmp")], [["repo/sub/a.tmp"]] * 3)
        Path(work, "a[1].txt").write_text("L")
        case("arithmetic counts only its own bracket and reads its substitutions, unclosed too (push-time review)",
             [targets("(( a[1] )); cat <<'X'\nrm a.tmp\nX"), targets('(( x; echo "$(rm a.tmp)"'), targets("echo $(( $(rm a.tmp) ))")],
             [[], "refused", "refused"])
        case("an unquoted heredoc body is read whole: a `$(` spanning lines, a body with no delimiter (push-time review)",
             [targets("cat <<EOF\n$(\nrm a.tmp\n)\nEOF"), targets("cat <<EOF\n$(rm a.tmp)")], ["refused", "refused"])
        os.symlink(os.path.join(work, "dir"), os.path.join(scratch, "out"))
        case("a `find` start that follows a link is judged where it LEADS (push-time review)",
             [targets(f"find -H {scratch}/out -delete"), targets(f"find {scratch}/out/ -delete"),
             ], ["refused"] * 2)
        os.remove(os.path.join(scratch, "out"))
        case("a quoted `a[1].txt` is backed up as the name it is, not only as a pattern (r1 Claude probe)",
             targets("rm 'a[1].txt'"), ["repo/sub/a[1].txt"])
        os.remove(os.path.join(work, "a[1].txt"))
        case("`find -delete` under this session's scratchpad needs no backup",
             targets(f"find {scratch} -name '*.txt' -delete"), [])
        case("`${S:?}` names S, and `$$` backs up every pid's file",
             [targets("S=dir; rm -r ${S:?}/inner"), targets("rm -f a.$$")], [["repo/sub/dir/inner"], ["repo/sub/a.tmp"]])
        case("`find -delete` and `find -exec rm` are refused",
             [targets("find . -name '*.tmp' -delete"), targets("find . -exec rm {} \\;")], ["refused", "refused"])
        case("a relative target after `cd -` is refused", targets("cd - && rm a.tmp"), "refused")
        case("a relative target after a `cd` inside a subshell is refused", targets("(cd .. && ls); rm a.tmp"),
             "refused")
        case("a relative target after `cd x || …` is refused", targets("cd dir || exit; rm a.tmp"), "refused")
        case("an ABSOLUTE target after an unfollowable `cd` is still backed up",
             targets(f"cd - && rm {work}/a.tmp"), ["repo/sub/a.tmp"])

        # ── round 2 (r2 R2-1 … R2-13)
        case("a heredoc delimiter is the whole word after quote removal (r2 R2-1)",
             [targets("cat <<END-X\nhi\nEND-X\nrm a.tmp"), targets("cat <<E.OF\nhi\nE.OF\nrm a.tmp"),
              targets('cat <<E"OF"\nhi $(rm b.txt)\nEOF\nrm a.tmp'), targets("cat <<\\EOF\nhi\nEOF\nrm a.tmp")],
             [["repo/sub/a.tmp"]] * 4)
        case("a heredoc whose delimiter cannot be read is refused (r2 R2-1)", targets("cat <<'EOF\nrm a.tmp"),
             "refused")
        case("a wrapper with an option value does not hide `find` or `xargs rm` (r2 R2-2)",
             [targets("nice -n 5 find . -name a.tmp -delete"), targets("env -u HOME find . -name a.tmp -delete"),
              targets("nice -n 5 xargs rm < list"), targets("timeout 5 find . -delete")], ["refused"] * 4)
        case("an unquoted variable holding blanks is backed up whole and word by word (r2 R2-3)",
             targets('X="a.tmp b.txt"; rm $X'), ["repo/sub/a.tmp", "repo/sub/b.txt"])
        case("a `cd` into a missing directory leaves the shell where it was (r2 R2-4)",
             targets("cd nope; rm a.tmp"), "refused")
        case("a `cd` after a command that can fail is known only inside its `&&` chain (r2 R2-4)",
             [targets("test -d dir && cd dir; rm a.tmp"), targets("test -d dir && cd dir && rm inner/c")],
             ["refused", ["repo/sub/dir/inner/c"]])
        case("a `cd` under `if`/`then` may not run (r2 R2-4)",
             [targets("if false; then cd dir; fi; rm a.tmp"), targets("{ cd dir; }; rm a.tmp")], ["refused"] * 2)
        case("`$PWD` is the payload's cwd, and `cd` moves `$PWD` and `$OLDPWD` (r2 R2-6)",
             [targets("rm -f $PWD/a.tmp", environ={**env, "PWD": tmp}), targets("cd .. && rm -f $PWD/x.tmp"),
              targets("cd .. && rm -f $OLDPWD/a.tmp"), targets("cd nope; rm -f $PWD/a.tmp")],
             [["repo/sub/a.tmp"], ["repo/x.tmp"], ["repo/sub/a.tmp"], "refused"])
        case("a `for` variable is not the value assigned before the loop (r2 R2-6)",
             targets("X=dir/inner/c; for X in a.tmp; do rm $X; done"), "refused")
        case("`read`, `printf -v`, `getopts`, `mapfile` and `unset` make a variable unknown (r2 R2-6)",
             [targets(f"X=b.txt; {s}; rm $X") for s in ("read X < f", "printf -v X a.tmp", "getopts ab X",
                                                        "mapfile X < f", "unset X")], ["refused"] * 5)
        case("`export`/`declare`/`local` X=v set X; without `=` they leave it (r2 R2-6)",
             [targets("X=b.txt; export X=a.tmp; rm $X"), targets("X=b.txt; declare -x X; rm $X")],
             [["repo/sub/a.tmp"], ["repo/sub/b.txt"]])
        case("`builtin cd` moves the shell (r2 R2-7)", targets("builtin cd ..; rm x.tmp"), ["repo/x.tmp"])
        case("`eval`, `source` and `.` make the cwd and every variable unknown (r2 R2-7)",
             [targets("source f; rm a.tmp"), targets("X=$KNOWN/a.tmp; eval X=b.txt; rm $X"), targets(". f; rm a.tmp")],
             ["refused"] * 3)
        case("`${S:-x}`, `${S-x}` and `${S:=x}` use the default when S is empty or unset (r2 R2-8)",
             [targets("S=; rm -f ${S:-a.tmp}"), targets("S=b.txt; rm -f ${S:-a.tmp}"), targets("rm -f ${S-a.tmp}"),
              targets("S=; rm -f x${S-a.tmp}"), targets("rm -f ${S:=a.tmp} $S"), targets("X=$NOPE; rm ${X:-a.tmp}")],
             [["repo/sub/a.tmp"], ["repo/sub/b.txt"], ["repo/sub/a.tmp"], [], ["repo/sub/a.tmp"] * 2, "refused"])
        case("`-de\"\"lete` is `-delete`: the prefilter reads quote-stripped text (r2 R2-9)",
             targets('find . -name a.tmp -de""lete'), "refused")
        case("a command name that is a glob or a brace list that may be `rm` is refused (r2 R2-9)",
             [targets("{rm,a.tmp}"), targets("/bin/r? a.tmp"), targets("ls *.tmp {a,b}"), targets("[ -f a.tmp ]")],
             ["refused", "refused", [], []])
        case("a `case` pattern is not a command name, and its `)` closes no subshell",
             [targets("case x in a) echo;; r*) echo hi;; esac; rm a.tmp"), targets("(case x in a) echo;; esac; X=b.txt); rm $X")],
             [["repo/sub/a.tmp"], "refused"])
        case("`<<` inside `${…}` opens no heredoc (r2 R2-10)", targets("echo ${a[x<<y]}\nrm a.tmp"),
             ["repo/sub/a.tmp"])
        case("a quoted operator character is a word, not an operator (r2 R2-11)",
             [targets('(echo ")"; cd dir; true); rm a.tmp'), targets('echo "x;rm b.txt"; rm a.tmp')],
             ["refused", ["repo/sub/a.tmp"]])
        case("a backslash-newline continues the word list (found in r2's fold)",
             targets("rm a.tmp \\\nb.txt"), ["repo/sub/a.tmp", "repo/sub/b.txt"])
        case("an out-of-range `\\U` escape is left as it is, not a crash (r2 R2-12)",
             targets("echo $'\\UFFFFFFFF'; rm a.tmp"), ["repo/sub/a.tmp"])

        case("`declare -n/-a/-A/-i` make a variable unknown, and a nameref's assignment every one (r2 S15)",
             [targets("declare -n X=/etc; rm -r $X"), targets("X=b.txt; declare -i X=a.tmp; rm $X"),
              targets("X=b.txt; typeset -a X=a.tmp; rm $X"), targets("declare -n R=X; X=b.txt; R=a.tmp; rm $X")],
             ["refused"] * 4)
        case("a subshell opened in a `case` arm is closed by its `)`, not read as a pattern (r2 S16)",
             [targets("X=a.tmp; case x in a) (X=a.tmp; true);; esac; rm $X"),
              targets("case x in a) echo;& r*) echo;;& c*) echo;; esac; rm a.tmp")],
             ["refused", ["repo/sub/a.tmp"]])
        case("an assignment under a guard that may not run leaves the variable unknown (found in r2 S16's fold)",
             [targets("X=b.txt; if false; then X=a.tmp; fi; rm $X"), targets("X=b.txt; false && X=a.tmp; rm $X")],
             ["refused"] * 2)
        case("a `$(mktemp …)` value is unknown: deleting it, `cd` into it or a `find` in it is refused (r2 S21)",
             [targets("T=$(mktemp -d); rm -rf $T"), targets("T=$(mktemp -d); cd $T; rm x"),
              targets("T=$(mktemp -d); find $T -delete"), targets("T=$(mktemp -d); cp a.tmp $T/; rm -rf $T")],
             ["refused"] * 4)
        case("a `mktemp` template in this session's scratchpad is the glob of its names and needs no backup (r2 S21)",
             [targets(f'T=$(mktemp -d "{scratch}/x.XXXX"); mv a.tmp $T/; rm -rf $T'),
              targets(f"T=$(mktemp -d {scratch}/x.XXXX) && cd $T && rm -rf w")], [[], []])
        os.symlink(os.path.join(work, "dir"), os.path.join(scratch, "out"))
        case("a `mktemp` template outside the scratchpad, through a link, or not alone in its word is unknown (r2 S21)",
             [targets(f"T=$(mktemp -d {work}/x.XXXX); mv a.tmp $T/; rm -rf $T"),
              targets(f"T=$(mktemp -d {scratch}/out/x.XXXX); mv a.tmp $T/; rm -rf $T"),
              targets(f"T=$(mktemp -d {scratch}/x.XXXX)/..; rm -rf $T/sub"),
              targets(f"T=$(mktemp -d {scratch}/x.XXXX; echo {work}); rm -rf $T")], ["refused"] * 4)
        os.remove(os.path.join(scratch, "out"))
        case("an assignment under a guard to an UNSET variable leaves it unknown; the same value stays (r2 S20)",
             [targets("if false; then X=a.tmp; fi; rm $X"), targets("X=a.tmp; if c; then X=a.tmp; fi; rm $X"),
              targets("cd /; true && X=a.tmp; rm $X"), targets("true && X=a.tmp || rm $X"),
              targets("true && X=a.tmp && echo && rm $X")], ["refused", ["repo/sub/a.tmp"], "refused", "refused",
                                                             ["repo/sub/a.tmp"]])
        case("`declare -l/-u/-c` transform a value, and a declared attribute outlives its `declare` (r2 S22)",
             [targets("declare -u X=a.tmp; rm $X"), targets("typeset -c X=a.tmp; rm $X"),
              targets("X=b.txt; declare -u X; X=a.tmp; rm $X")], ["refused"] * 3)
        Path(work, "q;x").write_text("Q")
        case("a quoted operator character in a target is restored before the path is read (r2 S18)",
             targets('rm "q;x"'), ["repo/sub/q;x"])
        os.remove(os.path.join(work, "q;x"))

        # ── NOT CHECKED
        case("an unbalanced quote is NOT CHECKED", targets("rm 'a.tmp"), "not checked")
        case("a relative cwd is NOT CHECKED", targets("rm a.tmp", cwd="rel"), "not checked")
        case("a command that is not a string is NOT CHECKED",
             _raises(lambda: decide({**pay(""), "tool_input": {"command": ["rm"]}}, env, root, now)),
             "Unreadable")

        # ── the copy itself
        case("a refusal tells the reader to make temp dirs in the scratchpad (r2 S21)",
             "mktemp -d \"$SCRATCH/x.XXXX\"" in (decide(pay("T=$(mktemp -d); rm -rf $T"), env, root, now) or ""), True)
        reason = decide(pay("rm -rf dir ../x.tmp link"), env, root, now)
        case("decide allows once the copies are made", reason, None)
        stamp = os.path.join(root, "sess-1", now.strftime("%Y%m%d-%H%M%S-%f"))
        case("the file is copied with its content",
             Path(stamp, tmp.lstrip("/"), "repo", "x.tmp").read_text(), "X")
        case("the directory is copied whole", Path(stamp, work.lstrip("/"), "dir", "inner", "c").read_text(), "C")
        case("the symlink is copied as a link", os.path.islink(os.path.join(stamp, work.lstrip("/"), "link")), True)
        log = [json.loads(x) for x in Path(root, "log.jsonl").read_text().splitlines()]
        case("one log line names the command and each copy",
             (len(log), log[-1]["command"], len(log[-1]["copies"])), (1, "rm -rf dir ../x.tmp link", 3))
        case("the originals are untouched (the hook copies; the shell deletes)",
             all(os.path.lexists(os.path.join(work, x)) for x in ("dir", "link")), True)

        # ── a failed copy refuses
        unreadable = os.path.join(work, "locked")
        os.makedirs(os.path.join(unreadable, "in"))
        Path(unreadable, "in", "f").write_text("F")

        def broken_copytree(*a, **k):
            raise OSError("injected copy failure")
        real_copytree, shutil.copytree = shutil.copytree, broken_copytree
        try:
            r = decide(pay("rm -rf locked"), env, root, now + _dt.timedelta(seconds=1))
        finally:
            shutil.copytree = real_copytree
        case("a copy that fails refuses the `rm`", ((r or "").startswith("⛔ REFUSED"), "injected" in (r or "")),
             (True, True))

        # ── the size cap
        global MAX_FILES
        saved, MAX_FILES = MAX_FILES, 1
        try:
            case("targets over the cap are refused", targets("rm -r dir a.tmp"), "refused")
        finally:
            MAX_FILES = saved

        # ── prune
        old = os.path.join(root, "sess-0", "20260101-000000-000000")
        os.makedirs(old)
        prune(root, _dt.datetime(2026, 1, 2))
        case("prune keeps a stamp younger than KEEP_DAYS", os.path.exists(old), True)
        prune(os.path.join(tmp, "no-such-root"), now)
        case("prune of a root that does not exist yet is a no-op", os.path.exists(os.path.join(tmp, "no-such-root")),
             False)
        outside = os.path.join(tmp, "outside", "20200101-000000-000000")
        os.makedirs(outside)
        os.symlink(os.path.join(tmp, "outside"), os.path.join(root, "linked-session"))
        prune(root, now)
        case("prune never follows a session link out of the root (r1 R1-5)", os.path.exists(outside), True)
        os.remove(os.path.join(root, "linked-session"))
        case("prune removes a stamp older than KEEP_DAYS and keeps today's",
             (os.path.exists(old), os.path.exists(stamp)), (False, True))

        # ── main --hook
        def run(payload, environ):
            import io
            buf, old_out = io.StringIO(), sys.stdout
            sys.stdout = buf
            try:
                rc = main(["--hook"], json.dumps(payload).encode(), environ)
            finally:
                sys.stdout = old_out
            return rc, buf.getvalue()
        henv = {**env, "RM_BACKUP_ROOT": root}
        rc, out = run(pay("rm $(cat x)"), henv)
        case("main --hook: a refusal is exit 0 with a deny decision on stdout",
             (rc, json.loads(out or "{}").get("hookSpecificOutput", {}).get("permissionDecision")), (0, "deny"))
        rc, out = run(pay("rm a.tmp"), henv)
        case("main --hook: a backed-up `rm` is exit 0, silent", (rc, out), (0, ""))
        other = os.path.join(tmp, "backups-2")
        case("decide backs up under the root it is given",
             (decide(pay("rm $KNOWN/b.txt"), env, other, now),
              any(f == "b.txt" for _, _, fs in os.walk(other) for f in fs)), (None, True))
        case("decide reads variables from the environment it is given",
             (decide(pay("rm $KNOWN/b.txt"), {"HOME": tmp}, other, now) or "").startswith("⛔ REFUSED"), True)
        import io
        err, old_err = io.StringIO(), sys.stderr
        sys.stderr = err
        try:
            rc = main(["--hook"], b"not json", henv)
        finally:
            sys.stderr = old_err
        case("main --hook: an unreadable payload is NOT CHECKED — exit 1, said on stderr",
             (rc, "NOT CHECKED" in err.getvalue()), (1, True))

    for f in failures:
        print(f)
    total = passed + len(failures)
    print(f"{passed}/{total} self-test cases passed")
    return 0 if not failures else 1


def _raises(fn) -> str:
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 — the case names which exception it expects
        return type(exc).__name__
    return "no exception"


if __name__ == "__main__":
    sys.exit(main())
