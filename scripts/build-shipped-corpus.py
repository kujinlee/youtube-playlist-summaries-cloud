#!/usr/bin/env python3
"""Build the memory corpus a stranger receives, and check the built output (marketplace-inventory plan, Task 18,
step "Build the shipped corpus"; the owner's answer to walkthrough decision 5).

    python3 scripts/build-shipped-corpus.py --self-test  # 31 cases
    python3 scripts/build-shipped-corpus.py --out DIR      # build into DIR, then run both checks on DIR
    python3 scripts/build-shipped-corpus.py --check DIR    # both checks on an already-built DIR

The corpus is built FROM `docs/memory/`, never edited in place there. The groups come from the first table of
`docs/marketplace/decision-5-suspect-files.md` (rows `| A |` … `| D |`, the backticked file names in the row): A, B
and C (16 files) are EXCLUDED; each D file (6) is replaced by its paraphrase in `docs/marketplace/shipped-corpus/`;
every other `.md` file is copied byte for byte, except `MEMORY.md`, whose index lines that link an excluded file are
dropped. A paraphrase is used only while its source is unchanged: `shipped-corpus/sources.json` records each D
source's sha256, and a source that no longer matches is CANNOT RUN (the paraphrase may have lost a new rule).

The two checks read the BUILT OUTPUT, never the transform:
  1. no original group-D quote is in any output file. The quotes are DERIVED from the SOURCE D files at check time
     (italic `*"…"*` quotes, and blockquotes that open with a `"`, each read within one paragraph), split at an
     ellipsis, and every fragment of three words or more — and every run of six consecutive words inside a longer
     one — is searched for as WORDS: every run of punctuation, markdown emphasis, blockquote markers and whitespace
     is one space, and case is folded. Each text is read under TWO views, on both sides: the PLAIN view, and the
     LINK-REDUCED one, where a Markdown link `[text](url)` or `[text][ref]` is first reduced to its text and a bare
     URL dropped. A fragment of either view of a quote that appears in either view of an output file is a hit; the
     reduction only ever adds hits, since a bracket or parenthesis it reads as a link may be text a reader sees
     (round 3 C1). A source D file with no quote found in it is CANNOT RUN, not a pass (its quotes would
     go unsearched).
  2. no excluded file is present anywhere in the output tree — by name, or by content (an output file whose
     CANONICAL bytes equal an excluded source file's, under any name: line endings unified, trailing whitespace
     dropped from each line, trailing blank lines dropped, on both sides).

rc 0 = built/checked and both checks pass; 1 = a check FAILED (each hit is named); 2 = CANNOT RUN (treat as NOT
RUN): a group count other than 6/4/6/6, a listed file missing from the source, a D file with no paraphrase or a
stale one, an `--out` that is not absent or empty, a non-`.md` entry in the source, or a D file with no quote found.

What this cannot see: a paraphrase that keeps an owner's words in a form the normaliser does not undo (a reworded
sentence, a reused run of fewer than six words from a longer quote, a fragment under three words, a word split or
joined differently, a link whose text is not the quoted word, a quote whose words are split by a link in one place
and by visible bracketed text in another, so that neither view holds a whole window), an excluded file's content in the output when it differs
by more than line endings and trailing whitespace (edited, or concatenated into another file), and private content
that is not a quote. Dangling `[[links]]` from kept files to excluded ones are left as they are.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

SRC = "docs/memory"
DECISION = "docs/marketplace/decision-5-suspect-files.md"
PARA = "docs/marketplace/shipped-corpus"
GROUP_SIZES = {"A": 6, "B": 4, "C": 6, "D": 6}
MIN_WORDS = 3
WINDOW = 6
VIEWS = (True, False)   # norm(text, links=...): the link-reduced view, then the plain one (round 3 C1)


class CannotRun(Exception):
    pass


def groups(decision_text: str) -> dict[str, list[str]]:
    """The file names per group, from the FIRST table's `| X |` rows (the *Answered* table repeats the letters with
    no file names, so only the first row per letter counts)."""
    out: dict[str, list[str]] = {}
    for line in decision_text.splitlines():
        m = re.match(r"^\|\s*([A-D])\s*\|", line)
        if m and m.group(1) not in out:
            out[m.group(1)] = re.findall(r"`([\w.-]+\.md)`", line.rsplit("|", 2)[-2])
    got = {k: len(v) for k, v in sorted(out.items())}
    if got != GROUP_SIZES:
        raise CannotRun(f"decision-5 group sizes are {got}, expected {GROUP_SIZES}")
    return out


def quotes(text: str) -> list[str]:
    """The owner's quotes in one source file, each read within ONE paragraph (a regex over the whole flattened file
    pairs one quote's opening with a later one's close and swallows the prose between)."""
    found: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        lines = para.split("\n")
        flat = re.sub(r"\s+", " ", " ".join(re.sub(r"^\s*(>\s?)*", "", ln) for ln in lines))
        found += [m.group(1) for m in re.finditer(r'\*"(.+?)"\*', flat)]
        if lines and re.match(r'^\s*>\s*"', lines[0]):
            body = " ".join(re.sub(r"^\s*>\s?", "", ln) for ln in lines if ln.lstrip().startswith(">"))
            found.append(re.sub(r"\s+", " ", body).strip().strip('"'))
    return found


def norm(text: str, links: bool = True) -> str:
    """WORDS, not characters: with `links`, a Markdown link (`[text](url)`, `[text][ref]`) is reduced to its text and
    a bare URL is dropped — their destinations would otherwise become words BETWEEN the quoted ones (round 2 X1) —
    then every run of non-alphanumeric characters (punctuation, markdown emphasis, blockquote markers, apostrophes of
    either kind, line breaks) becomes one space, and case is folded — so a quote reproduced with its punctuation
    changed, added or stripped, or each word wrapped in a link, still matches. The reduction can also DELETE visible
    words (`[a](b c)` and `[a][b c]` render as text, and `\\S+` swallows a word glued to a URL), so it is never the
    only view: `check` and `fragments` read both (round 3 C1)."""
    if links:
        text = re.sub(r"\[([^\]\n]*)\](?:\([^)\n]*\)|\[[^\]\n]*\])", r"\1", text)
        text = re.sub(r"(?:https?|ftp)://\S+|www\.\S+", " ", text)
    return " ".join(re.sub(r"[\W_]+", " ", text.lower()).split())


def fragments(quote: str) -> list[str]:
    """A quote split at each ellipsis, every piece of MIN_WORDS words or more, normalised under EACH view (link-reduced
    and plain; a piece the two views agree on is listed once)."""
    out: list[str] = []
    for links in VIEWS:
        for p in re.split(r"…|\.\.\.", quote):
            s = norm(p, links).strip(" .,;:")
            if len(s.split()) >= MIN_WORDS and s not in out:
                out.append(s)
    return out


def windows(fragment: str) -> list[str]:
    """Every run of WINDOW consecutive words in a fragment (the fragment itself when it is shorter), so a quote
    reused in part, or with one word changed, is still found."""
    w = fragment.split()
    return [" ".join(w[i:i + WINDOW]) for i in range(max(1, len(w) - WINDOW + 1))]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canon_sha(path: Path) -> str:
    """The hash of a file's CANONICAL bytes, for the excluded-content check (round 2 X2): every line ending is one
    (`splitlines`), each line's trailing whitespace is dropped, and so are the trailing blank lines — so a copy with
    CRLF endings or a ` \\n` appended still matches. `_sha` stays raw: the stale-paraphrase check wants ANY change."""
    lines = path.read_bytes().splitlines()
    return hashlib.sha256(b"\n".join(ln.rstrip() for ln in lines).rstrip(b"\n")).hexdigest()


def build(root: Path, out: Path) -> list[str]:
    src, para = root / SRC, root / PARA
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise CannotRun(f"--out {out} is not an empty directory")
    g = groups((root / DECISION).read_text())
    excluded = set(g["A"] + g["B"] + g["C"])
    d_files = set(g["D"])
    missing = sorted(n for n in excluded | d_files if not (src / n).is_file())
    if missing:
        raise CannotRun(f"listed in decision 5 but absent from {SRC}: {missing}")
    recorded = json.loads((para / "sources.json").read_text())
    for n in sorted(d_files):
        if not (para / n).is_file():
            raise CannotRun(f"group-D file {n} has no paraphrase in {PARA}")
        if recorded.get(n) != _sha(src / n):
            raise CannotRun(f"paraphrase of {n} is stale: its source changed since sources.json was written")
    entries = sorted(src.iterdir())
    odd = [p.name for p in entries if not (p.is_file() and p.suffix == ".md")]
    if odd:
        raise CannotRun(f"non-.md entries in {SRC}: {odd}")
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for p in entries:
        if p.name in excluded:
            continue
        if p.name in d_files:
            shutil.copyfile(para / p.name, out / p.name)
        elif p.name == "MEMORY.md":
            keep = [ln for ln in p.read_text().split("\n")
                    if not any(f"({n})" in ln for n in excluded)]
            (out / p.name).write_text("\n".join(keep))
        else:
            shutil.copyfile(p, out / p.name)
        written.append(p.name)
    return written


def check(root: Path, out: Path) -> tuple[int, list[str]]:
    g = groups((root / DECISION).read_text())
    excluded = set(g["A"] + g["B"] + g["C"])
    report, hits = [], []
    frags: dict[str, str] = {}
    unread = []
    for n in g["D"]:
        qs = quotes((root / SRC / n).read_text())
        mine = {s for q in qs for f in fragments(q) for s in windows(f)}
        report.append(f"  {n}: {len(qs)} quotes")
        if not mine:
            unread.append(n)
        frags.update({s: n for s in mine})
    if unread:
        return 2, report + [f"CANNOT RUN: no quote found in group-D source(s) {unread} — their quotes were not checked"]
    gone = {_canon_sha(root / SRC / n): n for n in sorted(excluded)}
    files = sorted(p for p in out.rglob("*") if p.is_file())
    if not files:
        return 2, report + [f"CANNOT RUN: {out} holds no files — nothing was checked"]
    for p in files:
        if p.name in excluded:
            hits.append(f"EXCLUDED FILE PRESENT: {p.relative_to(out)}")
        elif _canon_sha(p) in gone:
            hits.append(f"EXCLUDED CONTENT PRESENT: {p.relative_to(out)} is {gone[_canon_sha(p)]}")
    for p in files:
        raw = p.read_text(errors="replace")
        bodies = {norm(raw, links) for links in VIEWS}
        for f, n in frags.items():
            if any(f in body for body in bodies):
                hits.append(f"QUOTE FROM {n} IN {p.relative_to(out)}: {f[:80]!r}")
    report.append(f"checked {len(files)} output files for {len(frags)} quote fragments and {len(excluded)} "
                  f"excluded names")
    if hits:
        return 1, report + hits + [f"FAIL: {len(hits)} hit(s)"]
    return 0, report + ["PASS: no group-D quote and no excluded file in the output"]


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--self-test"]:
        return _self_test()
    if len(argv) != 2 or argv[0] not in ("--out", "--check"):
        print("usage: build-shipped-corpus.py --out DIR | --check DIR | --self-test", file=sys.stderr)
        return 2
    root, out = Path(__file__).resolve().parent.parent, Path(argv[1])
    try:
        if argv[0] == "--out":
            print(f"built {len(build(root, out))} files into {out}")
        rc, lines = check(root, out)
    except CannotRun as e:
        print(f"CANNOT RUN: {e}", file=sys.stderr)
        return 2
    print("\n".join(lines))
    return rc


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

    base = Path(tempfile.mkdtemp(prefix="shipped-corpus-"))
    letters = {"A": ["a1.md", "a2.md", "a3.md", "a4.md", "a5.md", "a6.md"], "B": ["b1.md", "b2.md", "b3.md", "b4.md"],
               "C": ["c1.md", "c2.md", "c3.md", "c4.md", "c5.md", "c6.md"],
               "D": ["d1.md", "d2.md", "d3.md", "d4.md", "d5.md", "d6.md"]}
    table = "\n".join(f"| {k} | why | " + ", ".join(f"`{n}`" for n in v) + " |" for k, v in letters.items())
    answered = "\n".join(f"| {k} | EXCLUDE | no files here |" for k in letters)
    d_text = {
        "d1.md": 'Rule one.\n\nThe owner: *"say the conclusion first, then explain"*\n',
        "d2.md": '> "keep a reserve for the\n> later days of the week"\n\nRule two.\n',
        "d3.md": 'Rule three: *"the first part of a quote … and the part after the cut"*\n',
        "d4.md": 'Rule four: *"#297 is NOT ready to merge — no review, `verify` pending."*\n',
        "d5.md": 'Rule five: *"don\'t stop tonight, as un-used capacity will be lost"*\n',
        "d6.md": 'Rule six: *"use the name of the owner here"*\n',
    }

    def world(name, d=None, decision=None, extra=None):
        root = base / name
        (root / SRC).mkdir(parents=True)
        (root / PARA).mkdir(parents=True)
        (root / DECISION).write_text(decision if decision is not None else f"{table}\n\n## Answered\n\n{answered}\n")
        files = dict(d_text if d is None else d)
        files.update({n: f"excluded {n}\n" for k in "ABC" for n in letters[k]})
        files.update({"kept.md": "A kept lesson. See [[a1]].\n",
                      "MEMORY.md": "- [a](a1.md) — gone\n- [k](kept.md) — stays\n"})
        files.update(extra or {})
        for n, t in files.items():
            (root / SRC / n).write_text(t)
        for n in letters["D"]:
            (root / PARA / n).write_text(f"Paraphrase of {n}: the rule, in other words.\n")
        (root / PARA / "sources.json").write_text(json.dumps({n: _sha(root / SRC / n) for n in letters["D"]}))
        return root

    def cannot(fn):
        try:
            fn()
        except CannotRun as e:
            return "CANNOT RUN: " + str(e).split(":")[0]
        return "RETURNED"

    good = world("good")
    # built INSIDE a case, so a build that raises is a named red case, not a crash before the first case
    case("a clean build writes the kept files, the paraphrases and the index, and no excluded file",
         lambda: sorted(build(good, base / "good-out")), sorted(["MEMORY.md", "kept.md"] + letters["D"]))
    case("a clean build passes both checks", lambda: check(good, base / "good-out")[0], 0)
    case("a D file in the output is its paraphrase, not its source",
         lambda: (base / "good-out/d1.md").read_text().startswith("Paraphrase of d1.md"), True)
    case("the index drops the lines that link an excluded file and keeps the rest",
         lambda: (base / "good-out/MEMORY.md").read_text(), "- [k](kept.md) — stays\n")
    case("italic and multi-line blockquote quotes are both extracted",
         lambda: (quotes(d_text["d1.md"]), quotes(d_text["d2.md"])),
         (["say the conclusion first, then explain"], ["keep a reserve for the later days of the week"]))
    case("a quote is read within one paragraph, never paired with a later paragraph's close",
         lambda: quotes('*"one" and more\n\nlater "two"* text'), [])
    case("an ellipsis splits a quote into fragments, and short fragments are dropped",
         lambda: (fragments('Keep the WHOLE rule … and the second half... ok'), fragments("two words")),
         (["keep the whole rule", "and the second half"], []))

    def planted(rel, text):
        out = base / f"planted-{len(list(base.iterdir()))}"
        shutil.copytree(base / "good-out", out)
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / rel).write_text(text)
        rc, lines = check(good, out)
        return rc, [ln.split(":")[0] for ln in lines if ln.startswith(("QUOTE", "EXCLUDED"))]

    case("an excluded file in the output fails check 2", lambda: planted("b3.md", "x\n"),
         (1, ["EXCLUDED FILE PRESENT"]))
    case("an excluded file nested in a subdirectory of the output fails check 2",
         lambda: planted("sub/c6.md", "x\n"), (1, ["EXCLUDED FILE PRESENT"]))
    case("a source quote in a kept output file fails check 1, through emphasis, case and line breaks",
         lambda: planted("kept.md", "As said: **Say the conclusion\nfirst**, then explain.\n"),
         (1, ["QUOTE FROM d1.md IN kept.md"]))
    case("one fragment of an ellipsis-cut quote in the output fails check 1",
         lambda: planted("kept.md", "...and the part after the cut.\n"), (1, ["QUOTE FROM d3.md IN kept.md"]))
    case("a quote reused in part, with its other words changed, fails check 1 on a six-word run",
         lambda: planted("kept.md", "We must keep a reserve for the later stages, always.\n"),
         (1, ["QUOTE FROM d2.md IN kept.md"]))
    case("a long fragment yields its six-word runs, a short one itself",
         lambda: (windows("one two three four five six seven"), windows("one two three")),
         (["one two three four five six", "two three four five six seven"], ["one two three"]))
    case("a quote reproduced with its punctuation stripped, changed or added fails check 1 (words, not characters)",
         lambda: (planted("kept.md", "297 is not ready to merge\n"),
                  planted("kept.md", "#297, is, not, ready, to, merge.\n"),
                  (lambda r: (r[0], sorted(set(r[1]))))(  # a long quote hits on several six-word runs
                      planted("kept.md", "Don’t stop tonight; as un-used capacity will be lost!\n"))),
         ((1, ["QUOTE FROM d4.md IN kept.md"]), (1, ["QUOTE FROM d4.md IN kept.md"]), (1, ["QUOTE FROM d5.md IN kept.md"])))
    case("a quote with each word wrapped in a Markdown link, or split by bare URLs, fails check 1 (links reduced to text)",
         lambda: tuple((lambda r: (r[0], sorted(set(r[1]))))(planted("kept.md", t)) for t in (
             "[297](https://x) [is](https://x) [NOT](https://x) [ready](https://x) [to](https://x) [merge](https://x)"
             " — no review, `verify` pending.\n",
             "[297][1] [is][1] [NOT][1] [ready][1] [to][1] [merge][1]\n\n[1]: https://x\n",
             "297 https://x is https://x/a?b=c NOT www.x.org ready to merge\n")),
         ((1, ["QUOTE FROM d4.md IN kept.md"]),) * 3)
    case("a quote inside text that only LOOKS like a link, or glued to a URL, fails check 1 (the plain view is searched too)",
         lambda: tuple((lambda r: (r[0], sorted(set(r[1]))))(planted("kept.md", t)) for t in (
             "Context [note](297 is NOT ready to merge) here.\n",
             "Context [aside][297 is NOT ready to merge] here.\n",
             "see <https://x>say the conclusion first, then explain\n")),
         ((1, ["QUOTE FROM d4.md IN kept.md"]), (1, ["QUOTE FROM d4.md IN kept.md"]), (1, ["QUOTE FROM d1.md IN kept.md"])))

    def linked_quote():
        root = world("linkquote", d={**d_text, "d6.md": 'Rule six: *"see [aside][you are not emitting banners] now"*\n'})
        out = base / "linkquote-out"
        shutil.copytree(base / "good-out", out)
        (out / "kept.md").write_text("They said: see aside, you are not emitting banners now.\n")
        rc, lines = check(root, out)
        return rc, sorted({ln.split(":")[0] for ln in lines if ln.startswith("QUOTE")})
    case("a SOURCE quote holding text that only looks like a link is searched in its plain view too, and fails check 1",
         linked_quote, (1, ["QUOTE FROM d6.md IN kept.md"]))
    case("the words of a quote with its punctuation changed still match, apostrophes of either kind included",
         lambda: (norm("Don’t, stop: tonight!") == norm("don't stop tonight"), norm("**Say** the\n> conclusion")),
         (True, "say the conclusion"))
    case("the plain view keeps the words inside a bracket or parenthesis, and a word glued to a URL; the link-reduced view drops them",
         lambda: (norm("[a](b c) <https://x>d", links=False), norm("[a](b c) <https://x>d", links=True)),
         ("a b c https x d", "a"))
    case("an excluded file's content in the output under another name fails check 2",
         lambda: planted("renamed.md", "excluded b2.md\n"), (1, ["EXCLUDED CONTENT PRESENT"]))
    case("an excluded file's content renamed with a whitespace line appended, or copied with CRLF endings, fails check 2 (canonical)",
         lambda: (planted("renamed.md", "excluded b2.md\n \n"), planted("renamed.md", "excluded b2.md\r\n")),
         ((1, ["EXCLUDED CONTENT PRESENT"]), (1, ["EXCLUDED CONTENT PRESENT"])))
    case("an excluded file's content with a trailing blank line added fails check 2 (canonical)",
         lambda: planted("renamed.md", "excluded b2.md\n\n\n"), (1, ["EXCLUDED CONTENT PRESENT"]))
    case("a kept file whose content differs from every excluded file does not fail check 2",
         lambda: planted("renamed.md", "excluded b2.md, edited\n"), (0, []))
    case("ONE source D file with no quote is CANNOT RUN, though the other five have quotes",
         lambda: (lambda r: (r[0], r[1][-1]))(
             check(world("onenoquote", d={**d_text, "d5.md": "Rule five, its quote reworded away.\n"}), base / "good-out")),
         (2, "CANNOT RUN: no quote found in group-D source(s) ['d5.md'] — their quotes were not checked"))
    case("no quote in any source D file is CANNOT RUN, not a pass",
         lambda: check(world("noquote", d={n: "no quotes\n" for n in letters["D"]}), base / "good-out")[0], 2)
    def stale():
        root = world("stale")
        (root / SRC / "d4.md").write_text("Rule four, now with a second rule.\n")
        return cannot(lambda: build(root, base / "stale-out"))
    case("a stale paraphrase (its source changed after sources.json) is CANNOT RUN", stale,
         "CANNOT RUN: paraphrase of d4.md is stale")
    case("a non-empty --out is CANNOT RUN", lambda: cannot(lambda: build(good, base / "good-out")),
         f"CANNOT RUN: --out {base / 'good-out'} is not an empty directory")
    case("the group table is read from the first row per letter, the Answered table's repeat ignored",
         lambda: groups(f"{table}\n\n## Answered\n\n{answered}\n")["D"], letters["D"])
    case("a decision table with the wrong group sizes is CANNOT RUN",
         lambda: cannot(lambda: groups(table.replace(", `b4.md`", ""))), "CANNOT RUN: decision-5 group sizes are {'A'")

    case("an output directory with no files is CANNOT RUN, not a pass",
         lambda: (base / "empty-out").mkdir() or check(good, base / "empty-out")[0], 2)

    def no_paraphrase():
        root = world("nopara")
        (root / PARA / "d5.md").unlink()
        return cannot(lambda: build(root, base / "nopara-out"))
    case("a D file with no paraphrase is CANNOT RUN", no_paraphrase, "CANNOT RUN: group-D file d5.md has no paraphrase in docs/marketplace/shipped-corpus")
    shutil.rmtree(base, ignore_errors=True)
    print(f"{ok}/{ok + fail} self-test cases passed")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
