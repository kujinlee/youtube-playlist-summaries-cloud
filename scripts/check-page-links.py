#!/usr/bin/env python3
"""Every key on a generated page is a link, built in ONE place, and every internal fragment resolves.

    python3 scripts/check-page-links.py --sources          # rule 2 only: the scripts/ tree
    python3 scripts/check-page-links.py --build            # every rule: builds the five pages into a temp dir
    python3 scripts/check-page-links.py --build --ci       # every rule over what the CHECKOUT alone builds (CI)
    python3 scripts/check-page-links.py --dir ~/explainers # every rule, over pages already built
    python3 scripts/check-page-links.py --self-test  # 94 cases

WHY (backlog #470; spec `docs/superpowers/specs/2026-11-02-comprehensibility-suite-design.md` §3, §7).
A key — `backlog #N`, `PR #N`, a goal, a feature, a dashboard entry, a goal-tree thread — has ONE home
page, and `page_markup.key_link` is the one function that builds the href to it. Before it, six hrefs were
hand-built in four places and the generated pages carried 0 PR links against 18-157 PR mentions each
(MEASURED, inventory 2026-10-27). This guard is the spec's three falsifiers for that rule, as checks, and
the page-validity rules review round 1 showed the linker needs:

  0. THE PAGE IS IN THE SUPPORTED SUBSET — `page_markup.subset_problems` names a construct where
     `html.parser` and a browser disagree about what is text (review round 2): a non-void self-closing
     tag, an unterminated comment, CDATA or script, a tag inside a `<textarea>`, an end tag out of order,
     an implied end tag, `&amp` with no `;`, ... A page outside it has its other rules NOT RUN, said so —
     they would read a page no browser shows. `link_html` refuses to link such a page at all.
  1. EVERY KEY IS A LINK — a page shows `backlog #N` or `PR #N` in a text node that is not exempt, or a
     bare `#N` chip outside an `<a>`.
  1b. NO `<a>` IN AN `<a>` — a page opens an `<a>` while one is open, or ends with one open.
  2. ONE LINK FUNCTION — an href to `/backlog-table#i`, `/goals#`, `/features#`, `/dashboard#`,
     `/goal-tree#` or `github.com/…/pull/` is built anywhere in `scripts/` except `page_markup.py`.
  3. LINKS RESOLVE — an internal link's `#fragment` has no matching `id` on its target page.
  4. IDS ARE UNIQUE — a page declares one `id` twice.
  5. SCRIPTS PARSE — an inline `<script>` fails `node --check`. No `node` is CANNOT RUN, never a pass.

⛔ ONE READING OF A PAGE. Rules 0, 1, 1b, 3, 4 and 5 read a page through `page_markup.page_tokens` — the
`html.parser` tokenizer the linker itself uses — so "what is text", "which text is exempt" and "which
element is open" have one answer for the thing that links and the thing that checks. Ids and hrefs come
from PARSED start tags: a string inside a script or a comment is not an element.

⚠ BOUNDS, stated.
  * Rule 2 reads the SYNTAX TREE of each script: string literals, f-strings (their constant `{'#'}`
    parts too), `+` chains, `"…" % (…)`, `"…".format(…)` and `"…".join([…])` of them, so
    `"/goals" + "#" + slug` and `"/goals#%s" % slug` are seen and a `# /goals#x` comment or a docstring
    is not. It does not see an href assembled through VARIABLES or a `%` DICT that never spell the
    literal in one expression. Only the BODIES of the self-test
    functions (`_self_test*` / `self_test*`) are exempt — expected VALUES, not built links.
  * The page rules read BUILT pages. `--build` needs a `gh` login, the Ask tray and the goal-tree log, so
    it runs locally. `--build --ci` builds what the checkout alone can: dashboard, goals and features as
    fragments, the backlog table whole. The goal-tree page needs the local log and is NOT RUN there — said
    so, and its fragments are counted unchecked. A missing page is CANNOT RUN (exit 2), never a pass.
  * Rule 3 checks fragments whose target is a page built here (or the same page). A fragment pointing
    anywhere else (`/src/…`, an explainer) is COUNTED as unchecked and printed, not silently skipped. A
    link built by the page's own JavaScript at run time is not seen.
  * A key split across elements (`backlog <b>#7</b>`) is neither linked nor reported (`page_markup`).
    A key naming a backlog row that does not exist renders as MARKED text, which is exempt: it is not a
    link, so it cannot dangle. A citation of a RENUMBERED row that now names a DIFFERENT existing row
    resolves cleanly and is confidently wrong; no rule here can see it.
  * Rule 1's "chip" is an element whose class names `chip` and whose first text starts with `#N`.

EXIT CODES (repo convention): 0 = clean · 1 = a rule is broken · 2 = CANNOT RUN.
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import functools
import io
import pathlib
import random
import re
import shutil
import subprocess
import sys
import tempfile

import page_markup

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
OK, BROKEN, CANNOT = 0, 1, 2

# page name (its served path) -> the generator that builds it, with the arguments that build it.
# The last argument is the flag the output path follows.
PAGES: dict[str, list[str]] = {
    "dashboard": ["gen-dashboard.py", "--out"],
    "backlog-table": ["gen-backlog-page.py", "--out"],
    "goals": ["gen-goals-page.py", "--out"],
    "features": ["gen-features-page.py", "--out"],
    "goal-tree": ["goal-tree.py", "--page", "--out"],
}
# `--ci`: what the checkout alone builds. A fragment needs no Ask tray; the goal-tree page needs the
# local log, so it is absent here, and said so.
CI_PAGES: dict[str, list[str]] = {
    "dashboard": ["gen-dashboard.py", "--fragment-only"],
    "backlog-table": ["gen-backlog-page.py", "--out"],
    "goals": ["gen-goals-page.py", "--fragment-only"],
    "features": ["gen-features-page.py", "--fragment-only"],
}
BUILD_TIMEOUT = 120      # seconds per generator; the slowest measured 2026-11-03 was gen-backlog-page, ~20s

# ── rule 2: hrefs to a key's home page, as SOURCE literals
HREF_LITERAL = re.compile(r"/backlog-table#i|/goals#|/features#|/dashboard#|/goal-tree#|(?<!refs)/pull/[{\"'\d]")
EXEMPT_SOURCES = {"page_markup.py", "check-page-links.py"}
TEST_FUNC = re.compile(r"_?self_test\w*")
# A file naming none of these cannot spell an href to a home page, so it is not parsed (a full AST pass
# over every script cost ~3.5 s, and the self-test runs it four times).
HOME_PATHS = ("/backlog-table", "/goals", "/features", "/dashboard", "/goal-tree", "/pull")

# ── rule 1: a bare `#N` chip
CHIP_TEXT = re.compile(r"\s*#\d+")
JS_TYPES = {"", "text/javascript", "application/javascript", "module"}

# Every rule reads the same few pages; tokenize each once. A pure function of the page, so a cache
# cannot change an answer — only how often a 4 MB page is parsed.
_tokens = functools.lru_cache(maxsize=16)(page_markup.page_tokens)


# A `%` conversion: `%s`, `%(name)s`, `%-5d`, `%%`.
_PCT = re.compile(r"%(?:\((?P<f>\w+)\))?[-#0 +]*(?:\*|\d+)?(?:\.(?:\*|\d+))?[a-zA-Z%]")
# A `str.format` field: `{}`, `{0}`, `{name}`, `{0!r:>4}`; `{{` / `}}` are literal braces.
_FIELD = re.compile(r"\{\{|\}\}|\{(?P<f>[^{}]*)\}")


def _fill(template: str, spec: re.Pattern, args: list, kwargs: dict) -> str:
    """`template` with each conversion replaced by the literal text of the argument it names, or `{}`
    when that argument is not a string literal (or is not there)."""
    pos = iter(args)

    def one(m):
        if m.group(0) in ("%%", "{{", "}}"):
            return m.group(0)[0]
        field = re.split(r"[!:.\[]", m.group("f") or "")[0]
        if field.isdigit():
            a = args[int(field)] if int(field) < len(args) else None
        else:
            a = kwargs.get(field) if field else next(pos, None)
        t = _literal(a) if a is not None else None
        return t if t is not None else "{}"
    return spec.sub(one, template)


def _call_parts(node):
    """(template, positional args, keyword args) of `"…".format(…)` / `"…".join([…])` on a string
    literal, else None."""
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr in ("format", "join") and _literal(node.func.value) is not None):
        if node.func.attr == "format":
            return node.func.value, list(node.args), {k.arg: k.value for k in node.keywords if k.arg}
        if len(node.args) == 1 and isinstance(node.args[0], (ast.List, ast.Tuple)):
            return node.func.value, list(node.args[0].elts), {}
    return None


def _literal(node) -> str | None:
    """The text a string expression spells, with `{}` for each part that is not a string literal; None
    if it is not a string expression. Reads a constant, an f-string (its constant `{'#'}` parts too), a
    `+` chain, `"…" % (…)`, `"…".format(…)` and `"…".join([…])` (round 2, Codex 1)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        out = []
        for v in node.values:
            t = _literal(v.value) if isinstance(v, ast.FormattedValue) and v.format_spec is None else None
            out.append(v.value if isinstance(v, ast.Constant) else t if t is not None else "{}")
        return "".join(out)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = _literal(node.left), _literal(node.right)
        if left is not None or right is not None:
            return (left if left is not None else "{}") + (right if right is not None else "{}")
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
        template = _literal(node.left)
        if template is not None:
            args = list(node.right.elts) if isinstance(node.right, ast.Tuple) else [node.right]
            return _fill(template, _PCT, args, {})
    call = _call_parts(node)
    if call:
        template, args, kwargs = call
        if node.func.attr == "join":
            return _literal(template).join(t if (t := _literal(a)) is not None else "{}" for a in args)
        return _fill(_literal(template), _FIELD, args, kwargs)
    return None


def _parts(node) -> list:
    """The sub-expressions `_literal(node)` read its text FROM — part of one literal, never reported alone."""
    if isinstance(node, ast.JoinedStr):
        return [*node.values, *(v.value for v in node.values if isinstance(v, ast.FormattedValue))]
    if isinstance(node, ast.BinOp):
        kids = [node.left, *(node.right.elts if isinstance(node.right, ast.Tuple) else [node.right])]
        return [c for c in kids if _literal(c) is not None]
    call = _call_parts(node)
    if call:
        return [node.func, call[0], *(a for a in [*call[1], *call[2].values()] if _literal(a) is not None)]
    return []


def built_hrefs(name: str, text: str) -> list[str]:
    """PURE. `name:line: literal` of every key href spelled in one source file, outside its self-test
    function bodies. A file that names a home page and does not parse is reported, never passed."""
    if name in EXEMPT_SOURCES or not any(h in text for h in HOME_PATHS):
        return []
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return [f"{name}:{exc.lineno}: CANNOT READ — the file does not parse ({exc.msg})"]
    tests = [(f.lineno, f.end_lineno) for f in ast.walk(tree)
             if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)) and TEST_FUNC.fullmatch(f.name)]
    docs = {id(s.value) for s in ast.walk(tree) if isinstance(s, ast.Expr)}
    inner: set[int] = set()
    out = []
    for n in ast.walk(tree):                     # breadth-first: an expression before its parts
        if id(n) in docs:
            continue
        s = _literal(n)
        if s is not None:
            inner.update(id(c) for c in _parts(n))
        if id(n) in inner or s is None or any(a <= n.lineno <= b for a, b in tests):
            continue
        # `'` closes the literal: its end is a join point, as `"/pull/"` + n is (`HREF_LITERAL`'s tail).
        out += [f"{name}:{n.lineno}: {h.group(0)}" for h in HREF_LITERAL.finditer(s + "'")]
    return sorted(set(out), key=lambda x: (int(x.split(":")[1]), x))


def _line(page: str, at: int) -> int:
    return page.count("\n", 0, at) + 1


def unlinked_keys(page: str) -> list[str]:
    """PURE. Every key `page_markup.text_keys` says should be a link, and every bare `#N` chip outside
    an `<a>`. Attribute values, scripts, comments and exempt elements are not page text."""
    tokens, _ = _tokens(page)
    out, chip = [], False
    for t in tokens:
        out += [m.group(0) for m in page_markup.text_keys(t)]
        if chip and t.kind == "data" and CHIP_TEXT.match(t.text):
            out.append(f"chip {t.text.strip().split()[0]}")
        chip = (t.kind == "start" and t.tag != "a" and not t.in_a
                and "chip" in (dict(t.attrs).get("class") or "").split())
    return out


def nested_anchors(page: str) -> list[str]:
    """PURE. Rule 1b: `line N` of every `<a>` opened inside an open `<a>`, and an `<a>` left open."""
    tokens, open_at_end = _tokens(page)
    out = [f"line {_line(page, t.start)}" for t in tokens if t.tag == "a" and t.kind == "start" and t.in_a]
    return out + (["an <a> still open at the end"] if "a" in open_at_end else [])


# ── THE GENERATORS' OWN TEXT IS INSIDE THE SUBSET (review round 3, F1 / F2). The subset is strict, and
# r2 measured it only against what the generators happened to EMIT: a URL in quotes, which the renderer
# cut into `&quot`, crashed all five. So each generator's renderer for author text is read here, by its
# OWN name in its OWN module (not `page_markup`'s, which a generator could stop using), and its output,
# placed where that generator places it, is linked and checked over a seeded fuzz corpus.
# (script, attribute, how the page wraps it). goal-tree's `_html_line` takes the repo too.
GENERATOR_RENDERERS = (
    ("gen-dashboard.py", "_prose", "<div>{}</div>"),
    ("gen-dashboard.py", "_inline", "<p>{}</p>"),
    ("gen-dashboard.py", "_inline_unlinked", '<a href="#x">{}</a>'),
    ("gen-backlog-page.py", "md", "<table><tbody><tr><td>{}</td></tr></tbody></table>"),
    ("gen-goals-page.py", "inline_md", '<p class="sentence">{}</p>'),
    ("gen-features-page.py", "inline_md", '<p class="purpose">{}</p>'),
    ("gen-features-page.py", "inline_unlinked", '<li><a href="#x">{}</a></li>'),
    ("goal-tree.py", "_html_line", '<pre class="tree">{}</pre>'),
)
# The alphabet: everything `escape` rewrites, URLs, keys, markdown delimiters, line and paragraph breaks,
# and references written raw (`&nbsp;`, a `;`-less `&amp`) or as the character itself (U+00A0).
FUZZ_TOKENS = ("<", ">", "&", '"', "'", " ", "\n", "\n\n", "\t", " ", "https://a.b/c", "http://x.y/",
               "backlog #7", "PR #3", "[", "]", "(", ")", "](https://b.c)", "`", "*", "**", "_", "~~",
               "&nbsp;", "&amp", "&#35;", ".", ",", ";", ":", "x", "word", "- ", "|", "#")
# The review's concrete inputs, verbatim, so the corpus always holds them.
FUZZ_VERBATIM = ('see "https://x.com/a" now', "see 'https://x.com/a' now", "see <https://x.com/a> now",
                 "see https://x.com/a& now", 'The page is served at "http://127.0.0.1:7391/dashboard" now.',
                 " See <https://example.com/x> and \"https://example.com/y\". ", "[https://a.com/x](https://b.com)")
FUZZ_SEED, FUZZ_COUNT = 470, 3000


def fuzz_inputs(seed: int = FUZZ_SEED, count: int = FUZZ_COUNT) -> list[str]:
    """PURE. The review's inputs, then `count` strings of 1-24 tokens drawn from `FUZZ_TOKENS` by a
    seeded generator: the same corpus on every run and every machine."""
    rng = random.Random(seed)
    return list(FUZZ_VERBATIM) + ["".join(rng.choice(FUZZ_TOKENS) for _ in range(rng.randint(1, 24)))
                                  for _ in range(count)]


def generator_renderers(root: pathlib.Path = ROOT) -> list[tuple[str, object]]:
    """Each `GENERATOR_RENDERERS` entry as (`script.attribute`, raw text -> the wrapped page). A missing
    script or attribute RAISES: a renderer this cannot read is not one whose output was checked."""
    import importlib.util
    mods, out = {}, []
    for script, attr, wrap in GENERATOR_RENDERERS:
        if script not in mods:
            spec = importlib.util.spec_from_file_location(script[:-3].replace("-", "_") + "_r3", root / "scripts" / script)
            mods[script] = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mods[script])
        fn = getattr(mods[script], attr)
        render = (lambda s, fn=fn: fn(s, "o/r")) if attr == "_html_line" else fn
        out.append((f"{script[:-3]}.{attr}", lambda s, render=render, wrap=wrap: wrap.format(render(s))))
    return out


def renderer_problems(renderers, inputs) -> list[str]:
    """`name: input -> problem` for each input on which a renderer's page, then `link_html`, RAISES (a
    crash is a problem, never swallowed as a pass), is outside the subset, nests an `<a>` in an `<a>`,
    or is not a fixed point of `link_html`. [] when every renderer is clean on every input."""
    out = []
    for name, render in renderers:
        for s in inputs:
            try:
                linked = page_markup.link_html(render(s), "o/r")
                why = (page_markup.subset_problems(linked) + nested_anchors(linked)
                       + ([] if page_markup.link_html(linked, "o/r") == linked else ["not a fixed point"]))
            except Exception as exc:
                why = [f"{type(exc).__name__}: {str(exc)[:120]}"]
            out += [f"{name}: {s!r} -> {w}" for w in why[:1]]
    return out


def _attrs(page: str):
    for t in _tokens(page)[0]:
        if t.kind in ("start", "startend"):
            yield t, dict(t.attrs)


def ids(page: str) -> set[str]:
    """PURE. Every `id` an element declares, and every `name` an `<a>` declares (parsed, decoded)."""
    out = set()
    for t, a in _attrs(page):
        if a.get("id"):
            out.add(a["id"])
        if t.tag == "a" and a.get("name"):
            out.add(a["name"])
    return out


def duplicate_ids(page: str) -> list[str]:
    """PURE. Rule 4: every `id` declared more than once."""
    seen, dup = set(), set()
    for _, a in _attrs(page):
        i = a.get("id")
        if i:
            (dup if i in seen else seen).add(i)
    return sorted(dup)


def inline_scripts(page: str) -> list[tuple[int, str, bool]]:
    """PURE. (line, body, is_module) of every inline JavaScript `<script>` — not `src=`, not JSON."""
    tokens, _ = _tokens(page)
    out = []
    for i, t in enumerate(tokens):
        if t.kind != "start" or t.tag != "script":
            continue
        a = dict(t.attrs)
        kind = (a.get("type") or "").strip().lower()
        if "src" in a or kind not in JS_TYPES:
            continue
        body = tokens[i + 1].text if i + 1 < len(tokens) and tokens[i + 1].kind == "data" else ""
        out.append((_line(page, t.start), body, kind == "module"))
    return out


def script_errors(pages: dict[str, str], node: str | None) -> tuple[list[str] | None, int]:
    """Rule 5. (each `page line N: error`, or None when there is no `node` — CANNOT RUN; scripts read)."""
    found = [(n, *s) for n, p in pages.items() for s in inline_scripts(p)]
    if node is None:
        return None, len(found)
    bad = []
    with tempfile.TemporaryDirectory() as td:
        for k, (n, line, body, module) in enumerate(found):
            f = pathlib.Path(td) / f"s{k}.{'mjs' if module else 'js'}"
            f.write_text(body, encoding="utf-8")
            r = subprocess.run([node, "--check", str(f)], capture_output=True, text=True, timeout=60)
            if r.returncode != 0:
                msg = next((x for x in r.stderr.splitlines() if "Error" in x), r.stderr.strip()[:120])
                bad.append(f"{n} line {line}: {msg}")
    return bad, len(found)


def fragment_targets(page: str, own: str) -> list[tuple[str | None, str]]:
    """PURE. (target page or None for one not generated here, fragment) for every href with a fragment.
    `#x` targets `own`; `/goals#x` and `/goals.html#x` target `goals`."""
    out = []
    for _, a in _attrs(page):
        href = a.get("href") or ""
        path, sep, frag = href.partition("#")
        if not sep or not frag:
            continue
        if path == "":
            out.append((own, frag))
            continue
        name = path[1:].removesuffix(".html") if path.startswith("/") else None
        out.append((name if name in PAGES else None, frag))
    return out


def dangling(pages: dict[str, str]) -> tuple[list[str], int]:
    """PURE. (each `page -> target#fragment` with no matching id, count of fragments not checked)."""
    declared = {n: ids(p) for n, p in pages.items()}
    bad, unchecked = [], 0
    for n, p in pages.items():
        for target, frag in fragment_targets(p, n):
            if target is None:
                unchecked += 1
            elif target in declared and frag not in declared[target]:
                bad.append(f"{n} -> /{target}#{frag}")
            elif target not in declared:
                unchecked += 1
    return sorted(set(bad)), unchecked


def check_sources(root: pathlib.Path) -> list[str]:
    out = []
    for p in sorted((root / "scripts").glob("*.py")):
        out += built_hrefs(p.name, p.read_text(encoding="utf-8", errors="replace"))
    return out


def build(into: pathlib.Path, pages: dict[str, list[str]] = PAGES) -> list[str]:
    """Run each generator into `into`. -> the problems (a generator that failed, timed out, or wrote
    nothing). Each runs as its own process; one failure does not stop the others."""
    problems = []
    for name, argv in pages.items():
        out = into / f"{name}.html"
        try:
            r = subprocess.run([sys.executable, str(SCRIPTS / argv[0]), *argv[1:], str(out)],
                               cwd=ROOT, capture_output=True, text=True, timeout=BUILD_TIMEOUT)
            if r.returncode != 0 or not out.is_file():
                problems.append(f"{argv[0]} exit {r.returncode}: {(r.stderr or r.stdout).strip()[-300:]}")
        except subprocess.TimeoutExpired:
            problems.append(f"{argv[0]} timed out after {BUILD_TIMEOUT}s")
    return problems


def check_pages(d: pathlib.Path, names=tuple(PAGES), node: str | None = "node") -> tuple[int, list[str]]:
    """Every page rule over `<name>.html` in `d`. `node` is the binary rule 5 runs (looked up on PATH)."""
    missing = [n for n in names if not (d / f"{n}.html").is_file()]
    if missing:
        return CANNOT, [f"CANNOT RUN — no {', '.join(m + '.html' for m in missing)} in {d}. "
                        f"Treat the page rules as NOT RUN."]
    read = {n: (d / f"{n}.html").read_text(encoding="utf-8", errors="replace") for n in names}
    lines, rc = [], OK
    pages = {}
    for n, p in read.items():
        outside = page_markup.subset_problems(p)
        if outside:
            rc = BROKEN
            lines.append(f"[FAIL] rule 0: /{n} is outside the supported HTML subset ({len(outside)} construct(s)), "
                         f"so its other rules are NOT RUN, e.g. " + "; ".join(outside[:6]))
        else:
            pages[n] = p
    for n, p in pages.items():
        for rule, found in (("1", unlinked_keys(p)), ("1b", nested_anchors(p)), ("4", duplicate_ids(p))):
            if found:
                rc = BROKEN
                what = {"1": "key(s) that are not links", "1b": "<a> inside an <a>", "4": "duplicate id(s)"}[rule]
                lines.append(f"[FAIL] rule {rule}: /{n} has {len(found)} {what}, e.g. " + ", ".join(found[:6]))
    bad, unchecked = dangling(pages)
    if bad:
        rc = BROKEN
        lines.append(f"[FAIL] rule 3: {len(bad)} internal fragment(s) with no id on the target page: "
                     + "; ".join(bad[:12]))
    errs, n_scripts = script_errors(pages, shutil.which(node) if node else None)
    if errs is None:
        rc = CANNOT if rc == OK else rc
        lines.append(f"CANNOT RUN — rule 5: no `node` on PATH, so {n_scripts} inline script(s) were NOT "
                     f"checked. Treat rule 5 as NOT RUN.")
    elif errs:
        rc = BROKEN
        lines.append(f"[FAIL] rule 5: {len(errs)} inline script(s) fail `node --check`: " + "; ".join(errs[:6]))
    checked = sum(len(fragment_targets(p, n)) for n, p in pages.items()) - unchecked
    lines.append(f"rule 0 read {len(read)} page(s); rules 1, 1b, 3, 4, 5 read the {len(pages)} inside the subset "
                 f"({', '.join(pages)}); "
                 f"{n_scripts if errs is not None else 0} inline script(s) parsed; {checked} fragment link(s) "
                 f"checked; {unchecked} point at a page not built here and were NOT checked")
    return rc, lines


def main(argv: list[str] | None = None, *, root: pathlib.Path = ROOT) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sources", action="store_true", help="rule 2 only")
    ap.add_argument("--build", action="store_true", help="build the pages into a temp dir, then check")
    ap.add_argument("--ci", action="store_true", help="with --build: only what the checkout alone builds")
    ap.add_argument("--dir", type=pathlib.Path, default=None, help="check pages already built here")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return _self_test()
    src = check_sources(root)
    rc = BROKEN if src else OK
    print(f"[FAIL] rule 2: {len(src)} key href(s) built outside page_markup.key_link:\n  "
          + "\n  ".join(src) if src else "rule 2: every key href in scripts/ is built by page_markup.key_link")
    if a.sources:
        return rc
    pages = CI_PAGES if a.ci else PAGES
    with tempfile.TemporaryDirectory() as tmp:
        d = a.dir.expanduser() if a.dir else pathlib.Path(tmp)
        if a.build:
            problems = build(d, pages)
            if problems:
                print("CANNOT RUN — a page did not build, so the page rules are NOT RUN:\n  "
                      + "\n  ".join(problems))
                return CANNOT
        elif a.dir is None:
            d = pathlib.Path.home() / "explainers"
        if a.ci:
            print("NOT RUN — the goal-tree page: it renders from the local goal-tree log, which a "
                  "checkout does not carry; links to it are counted unchecked below.")
        prc, lines = check_pages(d, tuple(pages))
        print("\n".join(lines))
    return max(rc, prc) if prc != CANNOT else CANNOT


# ───────────────────────────────────────────────────────────────── self-test

def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    ok = fail = 0

    def case(label, got, want):
        nonlocal ok, fail
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"[FAIL] {label}: got {got!r} want {want!r}")

    # ── rule 2
    case("rule 2: a hand-built backlog href is found, with its line",
         built_hrefs("x.py", 'a = 1\nh = f"/backlog-table#i{n}"\n'), ["x.py:2: /backlog-table#i"])
    case("rule 2: each of the other home pages is found",
         len(built_hrefs("x.py", 'h = ("/goals#a" "/features#b" "/dashboard#c" "/goal-tree#t")')), 4)
    case("rule 2: a PR href split over two lines is still found (the gen-dashboard shape)",
         len(built_hrefs("x.py", "a = f'https://github.com/{s}'\nb = f'/pull/{n}\">'")), 1)
    case("rule 2: a PR href whose number is joined on is found", len(built_hrefs("x.py", 'b = "/pull/" + n')), 1)
    case("rule 2: an href concatenated from pieces that never spell it alone is found (Codex r1 5)",
         built_hrefs("x.py", 'href = "/goals" + "#" + slug\n'), ["x.py:1: /goals#"])
    # Codex r2 1: the review's own inputs, and the other literal-only assemblies it names
    case("rule 2: Codex r2 1 — a `%`-formatted goals href is found",
         built_hrefs("x.py", 'h = "/goals#%s" % slug'), ["x.py:1: /goals#"])
    case("rule 2: Codex r2 1 — a `%`-formatted PR href is found", len(built_hrefs("x.py", 'h = "/pull/%s" % n')), 1)
    case("rule 2: a `%` whose literal pieces are its ARGUMENTS is found",
         built_hrefs("x.py", 'h = "%s#%s" % ("/goals", slug)'), ["x.py:1: /goals#"])
    case("rule 2: a `.format` whose literal pieces are its arguments, positional or named, is found",
         [built_hrefs("x.py", t) for t in ('h = "/goals{}{}".format("#", s)', 'h = "{0}#{1}".format("/goals", s)',
                                           'h = "{a}#".format(a="/goals")')], [["x.py:1: /goals#"]] * 3)
    case("rule 2: a `\"\".join` of constants is found",
         built_hrefs("x.py", 'h = "".join(["/goals", "#", slug])'), ["x.py:1: /goals#"])
    case("rule 2: an f-string whose CONSTANT parts spell the href is found",
         built_hrefs("x.py", "h = f\"/goals{'#'}{slug}\""), ["x.py:1: /goals#"])
    case("rule 2: an href inside a `.format` ARGUMENT is still found",
         built_hrefs("x.py", 'h = "{}".format("/goals#" + s)'), ["x.py:1: /goals#"])
    case("rule 2: `%%` and a join of other literals are not hrefs",
         built_hrefs("x.py", 'h = "/goals %d%%" % n\nk = "/".join(["a", "b"])'), [])
    case("rule 2: a COMMENT naming an href is not a built href",
         built_hrefs("x.py", "# See /goals#slug\nx = 1\n"), [])
    case("rule 2: a DOCSTRING naming an href is not a built href",
         built_hrefs("x.py", 'def f():\n    """links /goals#slug"""\n'), [])
    case("rule 2: `refs/pull/` (a git ref, not a link) is not a PR href",
         built_hrefs("x.py", "c = startsWith(github.ref, 'refs/pull/')"), [])
    case("rule 2: page_markup.py, the one place, is exempt",
         built_hrefs("page_markup.py", 'h = f"/backlog-table#i{key}"'), [])
    case("rule 2: a literal INSIDE the self-test body is test code and exempt",
         built_hrefs("x.py", 'ok = 1\ndef _self_test():\n    h = "/backlog-table#i5"\n'), [])
    case("rule 2: ...and so is one inside a `def self_test` (the gen-*-page spelling)",
         built_hrefs("x.py", 'def self_test():\n    h = "/goals#a"\n'), [])
    case("rule 2: production code AFTER a self-test is NOT exempt (Codex r1 5)",
         built_hrefs("x.py", 'def self_test(): pass\ndef main():\n    return "/goals#" + slug\n'),
         ["x.py:3: /goals#"])
    case("rule 2: a literal BEFORE the self-test is still found",
         len(built_hrefs("x.py", 'h = "/goals#a"\ndef _self_test():\n    pass\n')), 1)
    case("rule 2: a file that names a home page and does not parse is reported, never passed",
         len(built_hrefs("x.py", 'h = "/goals#a"\ndef (:\n')), 1)
    case("rule 2: a file naming no home page is not read at all", built_hrefs("x.py", "def (:\n"), [])
    case("rule 2: the live scripts/ tree builds every key href through key_link", check_sources(ROOT), [])
    with tempfile.TemporaryDirectory() as r:
        (pathlib.Path(r) / "scripts").mkdir()
        (pathlib.Path(r) / "scripts" / "gen-x.py").write_text('h = f"/features#{slug}"\n')
        case("rule 2: a tree with a hand-built href is found, by file and line",
             check_sources(pathlib.Path(r)), ["gen-x.py:1: /features#"])
        _o = io.StringIO()
        with contextlib.redirect_stdout(_o):
            _rc = main(["--sources"], root=pathlib.Path(r))
        case("main --sources: a hand-built href FAILS, and the output names it",
             (_rc, "gen-x.py:1" in _o.getvalue()), (BROKEN, True))
        with contextlib.redirect_stdout(io.StringIO()):     # the [FAIL] line must NOT be swallowed:
            _rc = main(["--sources"], root=ROOT)               # the case runs OUTSIDE the redirect
        case("main --sources: the live tree passes", _rc, OK)

    # ── rule 1
    case("rule 1: a backlog key in plain text is found",
         unlinked_keys("<p>see backlog #5 now</p>"), ["backlog #5"])
    case("rule 1: a PR key in plain text is found", unlinked_keys("<li>PR #9</li>"), ["PR #9"])
    case("rule 1: a key inside an <a> is fine",
         unlinked_keys('<p><a href="/backlog-table#i5">backlog #5</a></p>'), [])
    case("rule 1: a key inside <code> is fine", unlinked_keys("<code>backlog #5</code>"), [])
    case("rule 1: a key inside a <script> is not page text", unlinked_keys("<script>'PR #3'</script>"), [])
    case("rule 1: a key in an ATTRIBUTE is not page text", unlinked_keys('<span title="PR #3">x</span>'), [])
    case("rule 1: a key in a <textarea> is exempt, as the linker leaves it (Codex r1 6)",
         unlinked_keys("<textarea>backlog #7</textarea>"), [])
    case("rule 1: an ENCODED key (`&#35;`) is a key the reader sees (Codex r1 6)",
         unlinked_keys("<p>backlog &#35;7</p>"), ["backlog #7"])
    case("rule 1: a key split across elements is not one text node, as the linker reads it",
         unlinked_keys("<p>backlog <b>#7</b></p>"), [])
    case("rule 1: a comment inside an <a> keeps the <a> open, so its key is fine (Codex r1 3)",
         unlinked_keys('<a href="/x">a<!-- c -->backlog #7</a>'), [])
    case("rule 1: a key naming a row that does not exist, MARKED, is not an unlinked key",
         unlinked_keys(f'<span class="{page_markup.MISSING_CLASS}" title="t">backlog #9</span>'), [])
    case("rule 1: a bare #N chip outside an <a> is found",
         unlinked_keys('<span class="chip">#12 · rel</span>'), ["chip #12"])
    case("rule 1: a #N chip that IS a link is fine",
         unlinked_keys('<a class="chip" href="/backlog-table#i12">#12</a>'), [])
    case("rule 1: a lowercase `pr #N` is not a key", unlinked_keys("<p>pr #4</p>"), [])
    _corpus = ['<p title="x > backlog #7">ok PR #2</p>', '<a href="/x">before<!-- c -->backlog #7</a> backlog #8',
               "<p>backlog &#35;7</p>", "<p>backlog <b>#7</b></p>", "<textarea>backlog #7</textarea> PR #1",
               "<code>a<!-- c -->backlog #7</code>", '<a href="/x"><style>p{}</style>backlog #7</a>',
               "<button>backlog #1</button><svg><text>PR #3</text></svg>"]
    def _linked(c):
        try:
            return page_markup.link_html(c, "o/r")
        except page_markup.OutsideSubset as exc:     # a refusal is a red case below, never a crash
            return f"<p>REFUSED backlog #0 {page_markup.escape(str(exc))}</p>"
    case("the linker and rule 1 AGREE: after link_html no input above has an unlinked key",
         [unlinked_keys(_linked(c)) for c in _corpus], [[]] * len(_corpus))
    case("...and link_html opens no <a> inside an <a> on any of them",
         [nested_anchors(_linked(c)) for c in _corpus], [[]] * len(_corpus))

    # ── rule 1b
    _nest = '<div class="frag"><a href="/backlog-table#i45">#45 when <a href="https://x/pull/98">PR #98</a> merged</a></div>'
    case("rule 1b: the features row of round 1 — an <a> inside an <a> — is found", nested_anchors(_nest), ["line 1"])
    case("rule 1b: two sibling links are fine", nested_anchors('<a href="/a">x</a><a href="/b">y</a>'), [])
    case("rule 1b: an <a> left open at the end is found", nested_anchors('<p><a href="/a">x'),
         ["an <a> still open at the end"])

    # ── rule 3
    case("rule 3: ids, and an <a>'s name, are both read", ids('<a id="x"></a><a name="y"></a>'), {"x", "y"})
    case("rule 3: a `name` on anything but an <a> is not a fragment target", ids('<input name="q">'), set())
    case("rule 3: single-quoted ids are read, and entities in them decoded",
         ids("<p id='a&amp;b'>"), {"a&b"})
    case("rule 3: an id-like string inside a SCRIPT is not an element's id (Codex r1 7)",
         ids("<script>const x = 'id=\"fake\"';</script><!-- id=\"c\" -->"), set())
    case("rule 3: ...so a link to it dangles",
         dangling({"goals": "<script>const x = 'id=\"fake\"';</script><a href=\"#fake\">x</a>"}),
         (["goals -> /goals#fake"], 0))
    case("rule 3: a same-page and a cross-page fragment are resolved to their targets",
         fragment_targets('<a href="#a">.</a><a href="/goals#b">.</a><a href="/src/x.md#c">.</a>', "features"),
         [("features", "a"), ("goals", "b"), (None, "c")])
    case("rule 3: `#x` targets the page it is ON, and `/x.html#y` names page x",
         fragment_targets("<a href='#q'>.</a><a href='/goal-tree.html#t-pr-1'>.</a><a href='/x'>.</a>", "goals"),
         [("goals", "q"), ("goal-tree", "t-pr-1")])
    _pages = {"goals": '<article id="g1">', "features": '<a href="/goals#g1">.</a><a href="/goals#gone">.</a>'}
    case("rule 3: a fragment with no id on its target page is dangling; one that resolves is not",
         dangling(_pages), (["features -> /goals#gone"], 0))
    case("rule 3: a fragment on a page this does not build is COUNTED, not passed silently",
         dangling({"goals": '<a href="/src/a.md#x">.</a>'}), ([], 1))
    case("rule 3: a fragment on a generated page that was NOT built here is counted unchecked",
         dangling({"goals": '<a href="/goal-tree#t-pr-1">.</a>'}), ([], 1))
    case("rule 3: an empty fragment (`#`, a neutralised href) is not a link to check",
         dangling({"goals": '<a href="#">.</a>'}), ([], 0))

    # ── rule 4
    case("rule 4: an id declared twice is found", duplicate_ids('<p id="a"></p><div id="a"></div><i id="b">'), ["a"])
    case("rule 4: an id inside a script string is not a declaration",
         duplicate_ids("<p id=\"a\"></p><script>'<p id=\"a\">'</script>"), [])

    # ── rule 5
    _js = '<script>var a = 1;</script><script type="application/json">{"x": 1}</script><script src="/x.js"></script>'
    case("rule 5: only inline JavaScript is read — not JSON, not src=",
         [(ln, b) for ln, b, _ in inline_scripts(_js)], [(1, "var a = 1;")])
    case("rule 5: a module script is read as a module", [m for *_, m in inline_scripts('<script type="module">import x from "y";</script>')], [True])
    _node = shutil.which("node")
    if _node:
        case("rule 5: a script that does not parse is found",
             len(script_errors({"goals": "<script>if (</script><script>ok();</script>"}, _node)[0]), 1)
        case("rule 5: scripts that parse pass, and are counted", script_errors({"goals": _js}, _node), ([], 1))
    else:
        case("rule 5: NOT RUN — no node on PATH, so a broken script cannot be shown to fail", "node", None)
    case("rule 5: no node is CANNOT RUN (None), never an empty list", script_errors({"goals": _js}, None), (None, 1))

    # ── the page check, end to end
    with tempfile.TemporaryDirectory() as t0:
        (pathlib.Path(t0) / "goals.html").write_text("<p></p>")
        rc, lines = check_pages(pathlib.Path(t0))
        case("ONE page present is still CANNOT RUN, naming the four missing",
             (rc, lines[0].count(".html")), (CANNOT, 4))
        case("--ci's page set is checked without the goal-tree page",
             check_pages(pathlib.Path(t0), ("goals",))[0], OK)
    with tempfile.TemporaryDirectory() as t:
        rc, lines = check_pages(pathlib.Path(t))
        case("a missing page is CANNOT RUN, never a pass", (rc, "NOT RUN" in lines[0]), (CANNOT, True))
        with contextlib.redirect_stdout(io.StringIO()):
            _rc = main(["--dir", t], root=ROOT)
        case("main --dir: missing pages are CANNOT RUN", _rc, CANNOT)
        for n in PAGES:
            (pathlib.Path(t) / f"{n}.html").write_text('<p id="a"><a href="#a">backlog #1</a></p><script>f();</script>')
        case("five clean pages pass", check_pages(pathlib.Path(t))[0], OK)
        with contextlib.redirect_stdout(io.StringIO()):
            _rc = main(["--dir", t], root=ROOT)
        case("main --dir: five clean pages and a clean tree pass", _rc, OK)
        case("no node: five clean pages are CANNOT RUN for rule 5, never a pass",
             check_pages(pathlib.Path(t), node="no-such-node-binary")[0], CANNOT)
        for body, label in (("<p>backlog #1</p>", "an unlinked key"),
                            ('<a href="/features#gone">x</a>', "a dangling fragment"),
                            ('<a href="/a"><a href="/b">x</a></a>', "an <a> in an <a>"),
                            ('<p id="d"></p><p id="d"></p>', "a duplicate id"),
                            ("<script>if (</script>", "a script that does not parse")):
            (pathlib.Path(t) / "goals.html").write_text(body)
            if "script" in label and not _node:
                continue
            case(f"a page with {label} FAILS", check_pages(pathlib.Path(t))[0], BROKEN)
        # ── rule 0 (Codex r2 2-8): each review input, verbatim, fails the page. MEASURED with rule 0
        # switched off: six of the eleven pass every other rule under 3.14, and five under 3.12.9, where
        # `<![foo]>` crashes the parser instead — not the same ones, because the two parsers read them
        # differently, which is the finding. (3.12.9 is an OLD 3.12; 3.12.12 reads these as 3.14 does —
        # `page_markup`'s subset comment, review round 3 F4.)
        for body, label in (('<a href="#fake">go</a><textarea><b id="fake">text</b></textarea>', "r2 2: a textarea"),
                            ("<script/>broken (</script>", "r2 3: a self-closed script"),
                            ("<script>broken (", "r2 3: an unterminated script"),
                            ('<a href="/x"><a/>backlog #7</a>', "r2 4: a self-closed anchor"),
                            ('<p class="key-missing">x<div>backlog #7</div>', "r2 5: an implied </p>"),
                            ("<!--backlog #7", "r2 6: an unterminated comment"),
                            ("<![CDATA[backlog #7", "r2 6: an unterminated CDATA"),
                            ("<plaintext>backlog #7", "r2 6: a plaintext"),
                            ("<p>&ampbacklog #7</p>", "r2 7: a reference with no ;"),
                            ("</>backlog #7", "r2 8: an empty end tag"),
                            ("<![foo]>", "r2 8: a marked section")):
            (pathlib.Path(t) / "goals.html").write_text(body)
            try:                                     # a crash is a red case, never a dead suite
                _rc = check_pages(pathlib.Path(t))[0]
            except Exception as exc:
                _rc = type(exc).__name__
            case(f"rule 0: a page with {label} FAILS", _rc, BROKEN)
        (pathlib.Path(t) / "goals.html").write_text("<p>backlog #1</p><span/>")
        rc, lines = check_pages(pathlib.Path(t))
        case("rule 0: a page outside the subset is named, and its other rules are NOT RUN",
             (rc, any(x.startswith("[FAIL] rule 0: /goals") and "NOT RUN" in x for x in lines),
              any(x.startswith("[FAIL] rule 1:") for x in lines)), (BROKEN, True, False))

    # ── the property (Claude r3 F1 / F2): every generator's renderer, over the seeded corpus, then
    # `link_html`, never raises, stays inside the subset, nests no `<a>`, and is a fixed point.
    _saved = page_markup.REPO, page_markup.ROWS
    try:
        page_markup.use_repo("o/r")
        page_markup.use_rows(None)
        _renderers = generator_renderers()
        case("property: every generator renderer in GENERATOR_RENDERERS is read from its own module",
             len(_renderers), len(GENERATOR_RENDERERS))
        _inputs = fuzz_inputs()
        case("property: the corpus is the review's inputs plus the seeded draw, the same on every run",
             (len(_inputs), _inputs == fuzz_inputs(), _inputs[:len(FUZZ_VERBATIM)] == list(FUZZ_VERBATIM)),
             (len(FUZZ_VERBATIM) + FUZZ_COUNT, True, True))
        case(f"property: Claude r3 F1/F2 — {len(_inputs)} inputs x {len(_renderers)} generator renderers, "
             "linked, raise nothing and stay inside the subset", renderer_problems(_renderers, _inputs)[:3], [])
        case("property: the seed and the count each move the draw, and the review's inputs lead it",
             (fuzz_inputs(1, 5) != fuzz_inputs(2, 5), len(fuzz_inputs(1, 5)), len(fuzz_inputs(1, 9))),
             (True, len(FUZZ_VERBATIM) + 5, len(FUZZ_VERBATIM) + 9))
        with tempfile.TemporaryDirectory() as _empty:
            try:
                _missing = f"returned {len(generator_renderers(pathlib.Path(_empty)))}"
            except OSError as exc:
                _missing = type(exc).__name__
        case("property: a root with no generators RAISES, never a corpus with no renderers in it",
             _missing, "FileNotFoundError")
        # The property's own falsifiers: each failure shape it claims to see, seen.
        _bad = [("ref", lambda s: '<a href="https://x.com/a&quot">x</a>'),
                ("nest", lambda s: '<a href="/a"><a href="/b">x</a></a>'),
                ("raise", lambda s: 1 / 0)]
        case("property: a renderer outside the subset, nesting an <a>, or raising is each reported",
             [w.split(" -> ")[1].split(":")[0][:17] for w in renderer_problems(_bad, ["x"])],
             ["OutsideSubset", "line 1", "ZeroDivisionError"])
    finally:
        page_markup.use_repo(_saved[0])
        page_markup.use_rows(_saved[1])

    print(f"\n{ok}/{ok + fail} self-test cases passed")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
