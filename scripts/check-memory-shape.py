#!/usr/bin/env python3
"""Every memory file in `docs/memory/` is well-formed, reachable from the index, and OPENS WITH ITS
CURRENT RULE — not with its history.

WHY THIS EXISTS. The owner (2026-11-13, `docs/memory/memory-files-are-audited-weekly.md`) asked for
a one-time audit and then "option B": a CI shape check on every PR. The audit merged as PR #585
(`4d76f76a`). It found rules buried under their own correction layers, so a session read the OLD
form of the rule first. This is part 1 of option B: the shape half. `check-memory-index-budget.py`
already owns the index's SIZE, and this script does not re-measure it.

WHAT FAILS (rc 1), one rule code per line of output:

  FRONTMATTER   a file has no `---` frontmatter, or lacks `name`, `description` or `metadata.type`,
                or holds a line this reader would accept but YAML would not (see `scalar_problem`):
                an unterminated quote or flow collection, an indicator-led or `: `-holding unquoted
                value, or a non-blank line that is not `key: value` (r1, Codex); a double-quoted
                escape YAML does not define, or text after a closing quote that is not a
                ` # comment` (r2, Codex). A trailing comment is valid, and is not part of the value
  TYPE          `metadata.type` is not one of user | feedback | project | reference
  NAME          `name` is not the filename's slug (`foo-bar.md` must say `name: foo-bar`)
  MISSING       `MEMORY.md` links a memory file that does not exist
  UNLISTED      a file is not REACHABLE from `MEMORY.md` within two hops (see the bound below)
  HISTORY-FIRST the first non-blank body line after the frontmatter is a history marker
  EMPTY-BODY    a file has frontmatter and nothing after it, so it opens with no rule at all

rc 2 = CANNOT RUN (no index, no memory files, an unreadable file, an unknown argument). That is
NEVER a pass. rc 0 = every file passed every rule.

⛔ THE HISTORY-MARKER SET, AND WHERE IT CAME FROM. It was derived from PR #585 by comparing every
file's first body line at `4d76f76a^` and at `4d76f76a`, and from the markers in the corpus before
and after the merge. It was not invented. After stripping leading markdown decoration (`#`, `>`,
`*`, `_`, `(`, a backtick, whitespace, a list marker `-`/`+`/`9.`, and the house glyphs ⛔ ⭐ ✅ ⚠ —
repeatedly, until nothing more strips), a first line is HISTORY when it starts with:

  `⟳`              the correction-layer glyph, optionally after a leading date. Before the
                   audit, 25+ `## ⟳ <date>` correction headings existed, and one was a file's opener (`launch-roadmap-state.md`). The
                   audit memory's rule is "never append another ⟳ section".
  `History`        the label the audit itself put on demoted history: `## History`,
                   `## History (condensed)`, `History: split out of …` (80+ after the merge, none
                   as an opener). In a HEADING the bare word counts; elsewhere only as a LABEL —
                   followed by `:`, `(`, a dash or the line's end — so a rule sentence that begins
                   "History goes below …" is not history (r1, Claude).
  `Split out of`   a provenance note. The audit removed it from the top of 2 files
                   (`slice-history.md`, `m4-superseded-trail.md`).
  `Was:`, `Was <date>:`, or `<date> … Was` (any case; the bold may close before the date)
                   the brief's date-stamped "Was:". ⚠ WITNESSED ZERO TIMES in the corpus before
                   or after the audit. It is in the set because the brief names it, not because the
                   audit removed one.

⚠ THE BOUND: WHAT THIS DOES NOT CATCH, ON PURPOSE.
  - Date-led STATUS openers (`**MEASURED 2026-…**`, `**MERGED 2026-… — PR #N**`). The audit rewrote
    many of them, but it also LEFT 20+ as openers of `project` memories, where the dated state IS the
    current content. Flagging them would contradict the audit it is derived from.
  - `> Merged N memories …` provenance notes. The audit kept 9 as openers.
  - History that is not marked. A paragraph of old narrative with no marker passes. This is a SHAPE
    check over the first line, not a reading of whether the rule is current. The weekly content
    audit owns that question.
  - A marker that is not at the line's start after decoration: `**Note:** ⟳ …`, a label before the
    date (`**MERGED 2026-09-21** — was …`). A date-then-`Was` is caught only when the date LEADS.
  - Only the FIRST non-blank body line is read. A `⟳` section appended BELOW the rule (the
    "never append another ⟳ section" half of the rule) is not detected here.

⚠ THE REACHABILITY BOUND ("UNLISTED"). It is NOT "every file has a row in MEMORY.md". That literal
rule fails 57 of 195 files today (measured 2026-11-19), and by design: `slice-history.md` says
"NEW slice rows go HERE, never in MEMORY.md", because the index is truncated in silence past its
size limit. So a file passes when MEMORY.md links it, or when a file that MEMORY.md links links it
(two hops). Measured 2026-11-19: 138 at hop 1, 57 at hop 2, 0 unreachable. A link is
`](name.md)` or `[[name]]`, read after dropping a `#anchor`, a `"title"`, `<…>`, a leading `./`
and a wiki `|alias` (r1, Claude), and never inside an HTML comment (r1, Codex: a reader cannot
follow it). A link inside a CODE SPAN or fence still counts: a reader can see and follow it. A `<!--`
or `-->` INSIDE a code span or a fenced block is literal text, not a delimiter (r2, Codex). An
INDENTED code block (four spaces) is not recognised as code, so a `<!--` in one still opens a comment.
MISSING is checked for MEMORY.md's own links only. Broken links inside
other memory files (10 measured 2026-11-19, several of them deliberate placeholders or paths outside
the folder) are not this check's subject.

CONTROL, measured 2026-11-19. On the live tree: rc 0, 195 files. On the PRE-audit tree
(`git archive 4d76f76a^ docs/memory`): 5 violations. They are the 3 openers the audit rewrote
(`launch-roadmap-state` ⟳, `slice-history` and `m4-superseded-trail` "Split out of"), plus 2 files
that had no frontmatter then. So the check catches what the audit fixed, and it does not pass by
reading nothing.

Only top-level `*.md` files in `docs/memory/` are examined. Subdirectories are not.

Callers: `.github/workflows/ci.yml`, next to `check-memory-index-budget.py`.

Usage:
    python3 scripts/check-memory-shape.py
    python3 scripts/check-memory-shape.py --self-test  # 104 cases
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MEMDIR = ROOT / "docs" / "memory"
INDEX_NAME = "MEMORY.md"

OK, VIOLATIONS, CANNOT_RUN = 0, 1, 2

TYPES = frozenset({"user", "feedback", "project", "reference"})

# Leading decoration stripped before a first line is matched. ⟳ is NOT in it: it is a marker.
# ⟳ r1 (Claude MAJOR): ⚠ was missing, and it is the corpus's MOST frequent line-start glyph (70 line
# starts, against ⛔ 43). `(` is in it too, and a list marker is stripped by `_LIST_MARKER`.
_DECORATION = "#>*_`( \t⛔⭐✅⚠️"
_LIST_MARKER = re.compile(r"(?:[-+]|\d+[.)])\s+")
_DATE = r"\d{4}-\d{2}-\d{2}"
# ⟳ r1 (Claude MINOR): a bare `History\b` fired on a CURRENT-rule sentence that begins with the
# word ("History goes BELOW the rule"). Outside a heading, `History` is now a marker only as a LABEL:
# followed by `:`, `(`, a dash, or the end of the line, through any closing bold. In a HEADING
# (`## History and detail`, witnessed) the bare word still counts: `_HEADING_MARKERS`.
# ⟳ r1 (Claude MINOR): `Was` is IGNORECASE like the others, and may close its bold before the date.
_HISTORY_MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("⟳", re.compile(r"(?:" + _DATE + r"\W{0,4})?⟳")),
    ("History", re.compile(r"History\**\s*(?:[:(—–]|$)", re.IGNORECASE)),
    ("Split out of", re.compile(r"Split out of\b", re.IGNORECASE)),
    ("Was:", re.compile(r"Was\**\s*(\(?" + _DATE + r"\)?)?\**\s*:", re.IGNORECASE)),
    ("Was:", re.compile(_DATE + r"\W{0,4}Was\b", re.IGNORECASE)),
)
_HEADING_MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("History", re.compile(r"History\b", re.IGNORECASE)),
)

# ⟳ r1 (Claude MINOR): a link is read whole, then normalised — `#anchor`, a `"title"`, `<…>`, a
# leading `./`, and a wiki `|alias` are dropped — so a dead `[x](gone.md#h)` in the index is MISSING
# rather than silently not a link.
_MD_LINK_RE = re.compile(r"\]\(([^)]*)\)")
_WIKI_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
# ⟳ r1 (Codex MAJOR): a link inside an HTML comment is invisible to a reader, so it reaches nothing.
# An unclosed `<!--` comments out the rest of the text, as it does in HTML.
# ⟳ r2 (Codex MAJOR + MINOR, both caused by the r1 fold): a `<!--` or `-->` inside a CODE SPAN or a
# fenced block is literal text, not a delimiter. One scan matches the LEFTMOST of a fenced block, an
# inline code span or a comment, so a delimiter inside code is consumed with the code (and kept), and
# a backtick inside a comment is consumed with the comment (and dropped). A span closes on a backtick
# run of the SAME length, and never across a blank line; an opener with no closer is literal.
_COMMENT_RE = re.compile(
    r"^[ ]{0,3}(?P<fence>`{3,}|~{3,})[^\n]*\n.*?(?:^[ ]{0,3}(?P=fence)[`~]*[ \t]*$|\Z)"
    r"|(?<!`)(?P<ticks>`+)(?!`)(?:(?!\n[ \t]*\n).)+?(?<!`)(?P=ticks)(?!`)"
    r"|<!--.*?(?:-->|\Z)", re.DOTALL | re.MULTILINE)


def _keep_code(match: re.Match[str]) -> str:
    """PURE. A `_COMMENT_RE` match is dropped when it is a comment, and kept whole when it is code."""
    return "" if match.group(0).startswith("<!--") else match.group(0)

# ⟳ r1 (Codex MAJOR): a frontmatter value this reader would accept but YAML would not. Measured
# 2026-11-20 over the live corpus: 189 double-quoted values, 796 plain, 0 single-quoted, 0 flow,
# 0 indicator-led — and ONE plain value holding `: ` (a YAML "mapping values are not allowed" error),
# fixed in the same commit.
_YAML_INDICATORS = "[]{}`@&*!|>%#,?"
# ⟳ r2 (Codex MAJOR): `\q` passed. A double-quoted scalar may hold only the escapes YAML 1.2 defines
# (§5.7): `\0 \a \b \t \n \v \f \r \e \  \" \/ \\ \N \_ \L \P`, a TAB, `\xHH`, `\uHHHH`, `\UHHHHHHHH`.
_ESCAPE = r'\\(?:[0abt\tnvfre "/\\N_LP]|x[0-9A-Fa-f]{2}|u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8})'
_DQ_RE = re.compile(r'"(?:[^"\\]|' + _ESCAPE + r')*"')
_DQ_ANY_ESCAPE_RE = re.compile(r'"(?:[^"\\]|\\.)*"')
_SQ_RE = re.compile(r"'(?:[^']|'')*'")
# ⟳ r2 (Codex MINOR, caused by the r1 fold): `"valid" # comment` is valid YAML. After a closing quote
# only a comment may follow, and YAML requires whitespace before its `#`. A PLAIN value's comment is
# ` #` onwards, too: it is dropped before the `: ` rule, and from the value read.
_TAIL_RE = re.compile(r"(?:\s+#.*)?")
_PLAIN_COMMENT_RE = re.compile(r"\s#.*")


def scalar_problem(value: str) -> str | None:
    """PURE. Why `value` (a frontmatter value, already stripped of whitespace) is not a well-formed
    YAML string scalar, or None when it is. An empty value is not this function's question."""
    if not value:
        return None
    if value[0] in "\"'":
        quoted = (_DQ_RE if value[0] == '"' else _SQ_RE).match(value)
        if quoted is None:
            if value[0] == "'":
                return "an unterminated single-quoted string"
            if _DQ_ANY_ESCAPE_RE.match(value):
                return "a double-quoted string holding an escape YAML does not define"
            return "an unterminated double-quoted string"
        return None if _TAIL_RE.fullmatch(value[quoted.end():]) else (
            "a quoted string followed by text that is not a ` # comment`")
    if value[0] in _YAML_INDICATORS:
        return f"an unquoted value starting with the YAML indicator `{value[0]}`"
    plain = _PLAIN_COMMENT_RE.sub("", value)
    if ": " in plain or plain.endswith(":"):
        return "an unquoted value holding `: `, which YAML reads as a nested mapping"
    return None


def scalar_text(value: str) -> str:
    """PURE. `value` (stripped) without a trailing YAML comment, its quotes still on. A value that
    `scalar_problem` refuses is returned unchanged: it is reported, not read."""
    if value and value[0] in "\"'":
        quoted = (_DQ_RE if value[0] == '"' else _SQ_RE).match(value)
        return value[:quoted.end()] if quoted else value
    return _PLAIN_COMMENT_RE.sub("", value)


def parse_frontmatter(text: str) -> tuple[dict[str, str] | None, list[str]]:
    """PURE. -> (fields, body lines). `fields` is None when there is no closed `---` block.

    Reads only the shape this corpus uses: top-level `key: value`, and `type:` indented under
    `metadata:`. Quotes around a value are removed. This is not a YAML parser, so what it cannot
    vouch for is REPORTED, not read: a non-blank line with no `key:`, and a value `scalar_problem`
    refuses, land in `fields["!malformed"]` (one reason per line, joined by `; `).
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None, lines
    for end in range(1, len(lines)):
        if lines[end].strip() == "---":
            break
    else:
        return None, lines
    fields: dict[str, str] = {}
    malformed: list[str] = []
    in_metadata = False
    for raw in lines[1:end]:
        if not raw.strip():
            continue
        indented = raw[0] in " \t"
        key, sep, value = raw.strip().partition(":")
        if not sep:
            malformed.append(f"line {raw.strip()[:40]!r} is not `key: value`")
            continue
        problem = scalar_problem(value.strip())
        if problem:
            malformed.append(f"`{key}` is {problem}")
        value = scalar_text(value.strip())
        value = value.strip().strip('"').strip("'")
        if not indented:
            in_metadata = key == "metadata"
            if not in_metadata:
                fields[key] = value
        elif in_metadata:
            fields["metadata." + key] = value
    if malformed:
        fields["!malformed"] = "; ".join(malformed)
    return fields, lines[end + 1:]


def first_body_line(body: list[str]) -> str | None:
    """PURE. The first non-blank line of a body, or None when there is none."""
    for line in body:
        if line.strip():
            return line
    return None


def history_marker(line: str) -> str | None:
    """PURE. The name of the history marker `line` opens with, or None for a current-rule line."""
    heading = line.lstrip().startswith("#")
    stripped = line
    while True:
        before = stripped
        stripped = stripped.lstrip(_DECORATION)
        stripped = _LIST_MARKER.sub("", stripped, count=1) if _LIST_MARKER.match(stripped) else stripped
        if stripped == before:
            break
    for label, pattern in _HISTORY_MARKERS + (_HEADING_MARKERS if heading else ()):
        if pattern.match(stripped):
            return label
    return None


def link_targets(text: str) -> set[str]:
    """PURE. Every `](x.md)` and `[[x]]` target in `text` outside an HTML comment, as a filename."""
    visible = _COMMENT_RE.sub(_keep_code, text)
    out: set[str] = set()
    for raw in _MD_LINK_RE.findall(visible):
        parts = raw.strip().split()
        target = parts[0].strip("<>").split("#", 1)[0] if parts else ""
        target = target[2:] if target.startswith("./") else target
        if target.endswith(".md"):
            out.add(target)
    for raw in _WIKI_LINK_RE.findall(visible):
        name = raw.split("|", 1)[0].split("#", 1)[0].strip()
        if name:
            out.add(name + ".md")
    return out


def file_violations(fname: str, text: str) -> list[str]:
    """PURE. The per-file rules: FRONTMATTER, TYPE, NAME, EMPTY-BODY, HISTORY-FIRST."""
    out: list[str] = []
    fields, body = parse_frontmatter(text)
    if fields is None:
        return [f"FRONTMATTER {fname}: no closed `---` frontmatter block"]
    if fields.get("!malformed"):
        out.append(f"FRONTMATTER {fname}: not well-formed YAML: {fields['!malformed']}")
    for need in ("name", "description", "metadata.type"):
        if not fields.get(need):
            out.append(f"FRONTMATTER {fname}: `{need}` is missing or empty")
    mtype = fields.get("metadata.type")
    if mtype and mtype not in TYPES:
        out.append(f"TYPE {fname}: `metadata.type: {mtype}` is not one of {sorted(TYPES)}")
    name = fields.get("name")
    slug = fname[:-3] if fname.endswith(".md") else fname
    if name and name != slug:
        out.append(f"NAME {fname}: `name: {name}` does not match the filename slug `{slug}`")
    first = first_body_line(body)
    if first is None:
        out.append(f"EMPTY-BODY {fname}: nothing after the frontmatter, so no current rule")
    else:
        marker = history_marker(first)
        if marker:
            out.append(f"HISTORY-FIRST {fname}: opens with history (`{marker}`), not its current "
                       f"rule: {first.strip()[:100]!r}")
    return out


def index_violations(index_text: str, texts: dict[str, str]) -> list[str]:
    """PURE. MISSING (the index links a file that is not there) and UNLISTED (two-hop reachability)."""
    out: list[str] = []
    hop1 = link_targets(index_text)
    for target in sorted(hop1):
        if target not in texts:
            out.append(f"MISSING {INDEX_NAME}: links `{target}`, which does not exist")
    reached = {t for t in hop1 if t in texts}
    for t in sorted(reached):
        reached = reached | {x for x in link_targets(texts[t]) if x in texts}
    for fname in sorted(texts):
        if fname not in reached:
            out.append(f"UNLISTED {fname}: not linked from {INDEX_NAME}, nor from any file it links")
    return out


def shape_violations(index_text: str, texts: dict[str, str]) -> list[str]:
    """PURE. Every violation over one corpus: per-file rules, then the index rules."""
    out: list[str] = []
    for fname in sorted(texts):
        out += file_violations(fname, texts[fname])
    return out + index_violations(index_text, texts)


def load(memdir: pathlib.Path) -> tuple[str | None, dict[str, str], str]:
    """The FETCH. -> (index text or None, {filename: text}, reason when it could not be read)."""
    index = memdir / INDEX_NAME
    try:
        index_text = index.read_text(encoding="utf-8")
        texts = {p.name: p.read_text(encoding="utf-8")
                 for p in sorted(memdir.glob("*.md")) if p.name != INDEX_NAME}
    except (OSError, UnicodeDecodeError) as exc:
        return None, {}, f"could not be READ ({type(exc).__name__}: {exc})"
    return index_text, texts, ""


def verdict(index_text: str | None, texts: dict[str, str], why: str, shown: str) -> tuple[int, str]:
    """PURE. -> (rc, message). An unreadable or empty corpus is CANNOT RUN, never a pass."""
    if index_text is None:
        return CANNOT_RUN, (f"CANNOT RUN — the memory corpus at {shown} {why or 'is absent'}. "
                            "Nothing was checked. Treat this as NOT RUN, never as a pass.")
    if not texts:
        return CANNOT_RUN, (f"CANNOT RUN — {shown} holds no memory files besides {INDEX_NAME}. "
                            "Nothing was checked. Treat this as NOT RUN, never as a pass.")
    found = shape_violations(index_text, texts)
    if found:
        return VIOLATIONS, "\n".join(
            [f"memory shape FAILED — {len(found)} violation(s) over {len(texts)} files in {shown}:"]
            + [f"  {v}" for v in found]
            + ["Fix the memory file, not this check. A file must OPEN with its current rule; "
               "history goes below it (docs/memory/memory-files-are-audited-weekly.md)."])
    return OK, f"memory shape ok — {len(texts)} files in {shown}, every rule passed"


def unknown_args(argv: list[str]) -> list[str]:
    """PURE. -> the arguments this guard does not accept. `--self-test` is the only one it does.
    A predicate, so a case can witness it without re-entering the suite (the budget check's hazard)."""
    return [a for a in argv if a != "--self-test"]


def main(argv: list[str], memdir: pathlib.Path = MEMDIR) -> int:
    """ADR-0014 D1: the world (`memdir`) arrives as a defaulted parameter beyond `argv`."""
    unknown = unknown_args(argv)
    if unknown:
        print(f"CANNOT RUN — unrecognised argument(s) {unknown}. This guard takes no operands and "
              "no options but `--self-test`, so nothing was checked. Treat this as NOT RUN, "
              "never as a pass.")
        return CANNOT_RUN
    if "--self-test" in argv:
        return _self_test()
    try:
        shown = str(memdir.relative_to(ROOT))
    except ValueError:
        shown = str(memdir)
    index_text, texts, why = load(memdir)
    rc, msg = verdict(index_text, texts, why, shown)
    print(msg)
    return rc


def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _mem(name: str, body: str = "**The rule:** do the thing.\n", mtype: str = "feedback",
         desc: str = "FIRES-WHEN: something") -> str:
    return (f"---\nname: {name}\ndescription: \"{desc}\"\nmetadata:\n  type: {mtype}\n---\n\n"
            f"{body}")


def _self_test_body() -> int:
    import contextlib
    import io
    import tempfile

    ok = fail = 0

    def check(label: str, got, want) -> None:
        nonlocal ok, fail
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"  [FAIL] {label}\n         got  {got!r}\n         want {want!r}")

    def codes(index_text: str, texts: dict[str, str]) -> list[str]:
        return [v.split(" ", 1)[0] for v in shape_violations(index_text, texts)]

    # A clean world: two listed files, one reached only through hop 2 (the slice-history shape).
    def world() -> tuple[str, dict[str, str]]:
        return ("# Memory Index\n\n- [A](alpha.md) — a\n- [[beta]] — b\n",
                {"alpha.md": _mem("alpha", "**The rule:** x. See [[gamma]].\n"),
                 "beta.md": _mem("beta", mtype="project"),
                 "gamma.md": _mem("gamma", "> Merged 2 memories. Former names: a, b.\n\nRule.\n",
                                  mtype="reference")})

    # --- the clean case: no rule fires on a well-formed corpus ---------------------------------
    idx, t = world()
    check("a clean corpus has no violations", codes(idx, t), [])

    # --- one case per failure rule; each asserts the EXACT code list, so over-firing is red too --
    idx, t = world()
    t["beta.md"] = "**The rule:** no frontmatter at all.\n"
    check("FRONTMATTER: a file with no frontmatter block", codes(idx, t), ["FRONTMATTER"])

    idx, t = world()
    t["beta.md"] = "---\nname: beta\nmetadata:\n  type: project\n---\n\nRule.\n"
    check("FRONTMATTER: a file missing `description`", codes(idx, t), ["FRONTMATTER"])

    idx, t = world()
    t["beta.md"] = "---\nname: beta\ndescription: d\n---\n\nRule.\n"
    check("FRONTMATTER: a file missing `metadata.type`", codes(idx, t), ["FRONTMATTER"])

    idx, t = world()
    t["beta.md"] = "---\ndescription: d\nmetadata:\n  type: project\n---\n\nRule.\n"
    check("FRONTMATTER: a file missing `name`", codes(idx, t), ["FRONTMATTER"])

    idx, t = world()
    t["beta.md"] = "---\nname: beta\ndescription: d\nmetadata:\n  type: project\n\nRule.\n"
    check("FRONTMATTER: an UNCLOSED frontmatter block", codes(idx, t), ["FRONTMATTER"])

    # ⟳ r1 (Codex MAJOR): values this reader accepted but YAML refuses. Each is FRONTMATTER alone.
    for label, line in (
            ("an unterminated flow sequence (the Codex input)", "description: [unterminated"),
            ("an unterminated double-quoted string", 'description: "never closed'),
            ("an unterminated single-quoted string", "description: 'never closed"),
            ("an unquoted value holding `: ` (the live defect)", "description: FIRES-WHEN: scoring"),
            ("an unquoted value led by a YAML indicator", "description: `code` first"),
            ("a line with no `key:` at all", "description: d\njust some text"),
    ):
        idx, t = world()
        t["beta.md"] = f"---\nname: beta\n{line}\nmetadata:\n  type: project\n---\n\nRule.\n"
        check(f"FRONTMATTER: {label}", codes(idx, t), ["FRONTMATTER"])
    for label, line in (
            ("a double-quoted value holding `: ` and an escaped quote", r'description: "A: \"b\" c"'),
            ("a single-quoted value with a doubled quote", "description: 'it''s: fine'"),
            ("a plain value with a colon not followed by a space", "description: see 10:30 today"),
    ):
        idx, t = world()
        t["beta.md"] = f"---\nname: beta\n{line}\nmetadata:\n  type: project\n---\n\nRule.\n"
        check(f"NOT malformed: {label}", codes(idx, t), [])
    # ⟳ r2 (Codex MAJOR): an escape YAML does not define; text after a closing quote that is not a
    # comment; a `#` that is not preceded by whitespace.
    for label, line in (
            ("a double-quoted value with the undefined escape `\\q` (the Codex input)",
             r'description: "bad\q"'),
            ("a quoted value followed by text that is not a comment", 'description: "a" b'),
            ("a quoted value followed by `#` with no space before it", 'description: "a"#x'),
    ):
        idx, t = world()
        t["beta.md"] = f"---\nname: beta\n{line}\nmetadata:\n  type: project\n---\n\nRule.\n"
        check(f"FRONTMATTER: {label}", codes(idx, t), ["FRONTMATTER"])
    # ⟳ r2 (Codex MINOR, caused by the r1 fold): valid YAML that the r1 rules refused.
    for label, line in (
            ("every escape YAML defines, in a double-quoted value",
             r'description: "t\t n\n q\" s\\ sl\/ x\x41 u\u00e9 U\U0001F600 sp\  z\0 e\e N\N"'),
            ("a double-quoted value, then a ` # comment` (the Codex input)",
             'description: "valid" # comment'),
            ("a plain value whose ` # comment` holds `: `", "description: d # see: the rule"),
    ):
        idx, t = world()
        t["beta.md"] = f"---\nname: beta\n{line}\nmetadata:\n  type: project\n---\n\nRule.\n"
        check(f"NOT malformed: {label}", codes(idx, t), [])
    idx, t = world()
    t["beta.md"] = '---\nname: "beta" # the slug\ndescription: d\nmetadata:\n  type: project\n---\n\nR.\n'
    check("a trailing comment is not part of the value read: `name: \"beta\" # …` is the slug",
          codes(idx, t), [])
    idx, t = world()
    t["beta.md"] = "---\nname: beta # the slug\ndescription: d\nmetadata:\n  type: project\n---\n\nR.\n"
    check("a PLAIN value's trailing comment is not read either: `name: beta # …` is the slug",
          codes(idx, t), [])
    check("scalar_problem tells a bad escape from an unterminated string",
          (scalar_problem(r'"bad\q"'), scalar_problem('"never closed')),
          ("a double-quoted string holding an escape YAML does not define",
           "an unterminated double-quoted string"))
    check("scalar_problem names the defect, and is None for an empty value",
          (scalar_problem(""), scalar_problem("ok"), scalar_problem("[x")),
          (None, None, "an unquoted value starting with the YAML indicator `[`"))

    idx, t = world()
    t["beta.md"] = _mem("beta", mtype="decision")
    check("TYPE: an unknown metadata.type", codes(idx, t), ["TYPE"])

    idx, t = world()
    t["beta.md"] = "---\nname: beta\ndescription: d\ntype: project\n---\n\nRule.\n"
    check("FRONTMATTER: a TOP-LEVEL `type:` is not `metadata.type`", codes(idx, t), ["FRONTMATTER"])

    idx, t = world()
    t["beta.md"] = _mem("beta-old")
    check("NAME: `name` differs from the filename slug", codes(idx, t), ["NAME"])

    idx, t = world()
    idx += "- [Gone](deleted-memory.md) — gone\n"
    check("MISSING: the index links a file that does not exist", codes(idx, t), ["MISSING"])

    idx, t = world()
    t["orphan.md"] = _mem("orphan")
    check("UNLISTED: a file nothing reaches", codes(idx, t), ["UNLISTED"])

    idx, t = world()
    t["deep.md"] = _mem("deep")
    t["gamma.md"] = _mem("gamma", "Rule. See [[deep]].\n", mtype="reference")
    check("UNLISTED: THREE hops is not reachable (the bound is two)", codes(idx, t), ["UNLISTED"])

    # ⟳ r1 (Codex MAJOR): reached ONLY through a commented-out link is not reached.
    idx, t = world()
    t["delta.md"] = _mem("delta")
    t["alpha.md"] = _mem("alpha", "**The rule:** x. See [[gamma]]. <!-- [[delta]] -->\n")
    check("UNLISTED: a file linked only inside an HTML comment", codes(idx, t), ["UNLISTED"])

    # ⟳ r1 (Claude MINOR): an anchored, titled or aliased index link to a missing file is MISSING.
    for form in ("[x](gone.md#h)", '[x](gone.md "t")', "[[gone|alias]]", "[[gone#h]]"):
        idx, t = world()
        check(f"MISSING: an index link of the form {form}", codes(idx + f"- {form}\n", t), ["MISSING"])
    # ⟳ r2 (Codex MAJOR + MINOR, caused by the r1 fold): a comment delimiter inside code is literal.
    idx, t = world()
    check("a `<!--` inside a code span does not hide the links after it (the Codex input)",
          codes("# Memory Index\n\n- `<!--` [[alpha]]\n- [[beta]]\n", t), [])
    idx, t = world()
    check("a link between two code-span delimiters is visible, so a dead one is MISSING",
          codes(idx + "- `<!--` [[gone]] `-->`\n", t), ["MISSING"])
    idx, t = world()
    check("a `<!--` inside a fenced block (with a blank line in it) hides nothing after the fence",
          codes("# Memory Index\n\n```html\n<!--\n\nx\n```\n- [A](alpha.md)\n- [[beta]]\n", t), [])

    idx, t = world()
    idx = "# Memory Index\n\n- [A](./alpha.md#top) — a\n- [[beta|B]] — b\n"
    check("an anchored and an aliased index link REACH their files", codes(idx, t), [])

    idx, t = world()
    t["beta.md"] = _mem("beta", "\n\n")
    check("EMPTY-BODY: frontmatter and nothing after it", codes(idx, t), ["EMPTY-BODY"])

    for label, opener in (
            ("`## ⟳ <date>` correction heading", "## ⟳ 2026-08-22 — master `9211f74`. Five PRs."),
            ("a bare `⟳` line", "⟳ I then called the second row unmutatable."),
            ("a decorated `⛔ **⟳ …**` line", "⛔ **⟳ CORRECTED 2026-09-14** the rule moved."),
            ("`## History` heading", "## History (condensed)"),
            ("`History:` label", "History: split out of the index on 2026-10-19."),
            ("`> Split out of` provenance", "> Split out of [[MEMORY.md]] on 2026-10-19 because"),
            ("`Was:` with a date", "**Was (2026-10-01):** the rule said otherwise."),
            ("`Was:` undated", "Was: always ask first."),
            ("a date, then `Was`", "2026-10-01 — Was the old rule."),
            # ⟳ r1 (Claude MAJOR): a one-glyph or list-item prefix hid each of these.
            ("a `⚠ ⟳` line", "⚠ ⟳ 2026-10-01 corrected the rule."),
            ("a `⚠️ ⟳` line (with the variation selector)", "⚠️ ⟳ 2026-10-01 corrected the rule."),
            ("a list item `- ⟳`", "- ⟳ 2026-10-01 the rule moved."),
            ("a list item, then a glyph `- ⚠ ⟳`", "- ⚠ ⟳ 2026-10-01 the rule moved."),
            ("a numbered list item `9. ⟳`", "9. ⟳ 2026-10-01 the rule moved."),
            ("a parenthesised `(⟳ …)`", "(⟳ 2026-10-01: the rule moved.)"),
            ("a date-first `**<date> ⟳**`", "**2026-10-01 ⟳** the rule moved."),
            # ⟳ r1 (Claude MINOR): `Was:` was case-sensitive, and could not cross a closing bold.
            ("`WAS:` in capitals", "WAS: ask first."),
            ("a date, then a lower-case `was`", "2026-10-01 — was the old rule."),
            ("`was:` in lower case", "was: ask first."),
            ("`**Was** (<date>):` with the bold closed first", "**Was** (2026-10-01): ask first."),
            # ⟳ r1 (Claude MINOR): the forms the tightened `History` must still catch, as witnessed.
            ("a `## History and detail` heading", "## History and detail"),
            ("a `## History — …` heading", "## History — the eight rounds"),
            ("a bold `**History:**` label", "**History:** on 10-30 I set it."),
            ("a bold `**History**:` label (the colon outside the bold)", "**History**: on 10-30 I set it."),
    ):
        idx, t = world()
        t["beta.md"] = _mem("beta", opener + "\n\n**The rule:** current.\n")
        check(f"HISTORY-FIRST: {label}", codes(idx, t), ["HISTORY-FIRST"])

    # --- ADJACENT negatives: shapes the audit KEPT as openers must pass -------------------------
    for label, opener in (
            ("`**The rule:**`", "**The rule:** each memory file opens with its CURRENT rule."),
            ("a dated status opener the audit kept", "**MERGED 2026-09-21 as `fab6f655` (PR #327).**"),
            ("`**Measured <date>**` the audit kept", "**Measured 2026-10-06, PR #366.** CI went red."),
            ("`> Merged N memories` the audit kept", "> Merged 2 memories. Former names (still valid)"),
            ("a rule that MENTIONS history later", "**The rule:** history goes below; never ⟳ on top."),
            ("a word that merely starts with `Was`", "Washing the cache is not the fix."),
            ("a word that merely starts with `History`", "Historyless rows are fine."),
            ("a HEADING whose first word merely starts with `History`", "## Historyless rows are kept"),
            # ⟳ r1 (Claude MINOR): a current rule may BEGIN with the word `History`.
            ("a rule sentence that begins with `History`", "History goes BELOW the current rule."),
            ("`HISTORY of …` in capitals", "HISTORY of this rule is in slice-history."),
            ("`History-first …` (a hyphen is not a label)", "History-first openers are refused."),
            ("a plain list-item rule", "- **The rule:** each memory opens with its rule."),
            # the date-then-`Was` form matches only when the DATE leads the line, so a dated STATUS
            # opener the bound keeps (label first, then the date) is not caught by its `was`.
            ("a status opener whose date is not first, then `was`", "**MERGED 2026-09-21** — was green, now live."),
    ):
        idx, t = world()
        t["beta.md"] = _mem("beta", opener + "\n")
        check(f"NOT history: {label}", codes(idx, t), [])

    # --- the first line is the first NON-BLANK one, and only that one is read ---------------------
    idx, t = world()
    t["beta.md"] = _mem("beta", "\n\n   \n## History\n")
    check("blank lines are skipped before the first line is read", codes(idx, t), ["HISTORY-FIRST"])
    idx, t = world()
    t["beta.md"] = _mem("beta", "**The rule:** current.\n\n## ⟳ 2026-09-01 — old\n")
    check("a ⟳ section BELOW the rule passes (stated bound)", codes(idx, t), [])

    # --- the pieces, directly ----------------------------------------------------------------
    # ⟳ r1 (Claude MINOR): `v.md#h` now counts as a link to `v.md` — the anchor is dropped.
    check("link_targets reads both link forms",
          link_targets("[a](x.md) and [[y]] and [z](http://e.com) and [w](v.md#h)"),
          {"x.md", "y.md", "v.md"})
    check("link_targets normalises a title, `<…>`, `./`, an alias and a wiki anchor",
          link_targets('[a](x.md "T") [b](<y.md>) [c](./z.md) [[w|W]] [[u#h]] [[#only-anchor]]'),
          {"x.md", "y.md", "z.md", "w.md", "u.md"})
    # ⟳ r1 (Codex MAJOR): a link inside an HTML comment is not a link a reader can follow.
    check("link_targets ignores links inside HTML comments, closed or not",
          link_targets("[[a]] <!-- [[b]] --> [[c]] <!-- [d](d.md)"), {"a.md", "c.md"})
    # ⟳ r2: a backtick with no closer, or one past a blank line, is literal, so the `<!--` is real.
    check("link_targets: a backtick with no closing run opens no code span",
          link_targets("x ` <!-- [[b]]"), set())
    check("link_targets: a code span never crosses a blank line",
          link_targets("`a\n\n<!-- [[b]] `"), set())
    check("link_targets: a link INSIDE a code span or a fenced block still counts (stated bound)",
          link_targets("see `[[a]]`\n```\n[[b]]\n```\n"), {"a.md", "b.md"})
    check("link_targets finds nothing in text without links", link_targets("plain [x] text"), set())
    check("parse_frontmatter strips quotes and reads metadata.type",
          parse_frontmatter('---\nname: "n"\ndescription: \'d\'\nmetadata:\n  type: user\n---\nB')[0],
          {"name": "n", "description": "d", "metadata.type": "user"})
    # ⟳ a mutation SURVIVED here: a file with no opening fence but a `---` rule further down was
    # parsed as frontmatter. Its codes are the same (FRONTMATTER either way), so assert the parse.
    check("parse_frontmatter: no opening fence is NO frontmatter, even with a `---` rule later",
          parse_frontmatter("**Rule.**\n\n---\n\nmore")[0], None)
    check("parse_frontmatter returns the body AFTER the closing fence",
          parse_frontmatter("---\nname: n\n---\nBODY\nmore")[1], ["BODY", "more"])
    check("a message names the file and the rule",
          [v.split(":", 1)[0] for v in
           shape_violations(world()[0], {**world()[1], "beta.md": _mem("nope")})],
          ["NAME beta.md"])
    check("the unknown-argument predicate keeps only what is not `--self-test`",
          unknown_args(["--self-test", "--bogus", "x"]), ["--bogus", "x"])
    check("the unknown-argument predicate is empty for the accepted forms",
          (unknown_args([]), unknown_args(["--self-test"])), ([], []))

    # --- driving main() over constructed worlds: rc in all three directions ----------------------
    # A raise is recorded as the case's `got`, never left to crash the suite: the mutation harness
    # reads a crash before `[FAIL] <case>` as no kill at all. The wanted rcs are LITERALS (0, 1, 2),
    # so a mutant that collapses CANNOT_RUN onto OK cannot satisfy a case that compares the constants.
    # Each case calls `main` at its OWN call site, so `check-fixture-variation` sees argv and memdir
    # take different values rather than one helper parameter.
    def run(call) -> tuple[object, str]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            try:
                rc: object = call()
            except Exception as exc:  # noqa: BLE001 — reported as the case's result
                rc = f"RAISED {type(exc).__name__}"
        return rc, buf.getvalue()

    with tempfile.TemporaryDirectory() as tmp:
        clean = pathlib.Path(tmp) / "clean"
        dirty = pathlib.Path(tmp) / "dirty"
        bare = pathlib.Path(tmp) / "bare"
        absent = pathlib.Path(tmp) / "absent"
        for d in (clean, dirty, bare):
            d.mkdir()
        idx, t = world()
        for d in (clean, dirty):
            (d / INDEX_NAME).write_text(idx, encoding="utf-8")
            for n, body in t.items():
                (d / n).write_text(body, encoding="utf-8")
        (dirty / "beta.md").write_text(_mem("beta", "## ⟳ 2026-01-01 — old\n"), encoding="utf-8")
        (bare / INDEX_NAME).write_text(idx, encoding="utf-8")

        rc, out = run(lambda: main([], memdir=clean))
        check("main over a clean corpus is rc 0", rc, 0)
        check("an OK message counts the files it checked", "3 files" in out, True)
        rc, out = run(lambda: main([], memdir=dirty))
        check("main over a corpus with a history opener is rc 1", rc, 1)
        check("the FAIL message names the file and the rule", "HISTORY-FIRST beta.md" in out, True)
        rc, out = run(lambda: main([], memdir=absent))
        check("a missing corpus is CANNOT RUN, not a pass", rc, 2)
        # ⟳ two mutations SURVIVED here. With the absent arm severed, the empty-corpus arm still
        # gave rc 2; and the exception text already carries the path, so `str(absent) in out`
        # held with the directory dropped from the sentence. Assert WHICH arm, and the sentence.
        check("an absent corpus says it could not be READ, not that it holds no files",
              ("could not be READ" in out, "holds no memory files" in out), (True, False))
        check("a CANNOT RUN names the directory it examined", f"corpus at {absent} " in out, True)
        rc, out = run(lambda: main([], memdir=bare))
        check("an index with no memory files is CANNOT RUN, not a vacuous pass", rc, 2)
        rc, out = run(lambda: main(["--bogus"], memdir=clean))
        check("an unknown argument is CANNOT RUN", (rc, "unrecognised" in out), (2, True))
        (dirty / "beta.md").write_bytes(b"---\nname: beta\n\xff\xfe\n---\n")
        rc, out = run(lambda: main([], memdir=dirty))
        check("an undecodable file is CANNOT RUN, not a traceback", rc, 2)

    check("MEMDIR is the repo's docs/memory", MEMDIR, ROOT / "docs" / "memory")

    print(f"self-test: {ok}/{ok + fail} cases passed")
    return OK if fail == 0 else VIOLATIONS


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
