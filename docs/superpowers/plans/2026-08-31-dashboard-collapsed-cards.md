# Dashboard Collapsed Cards Implementation Plan

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them — without reading the chat transcript.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collapse each dashboard entry card to one clipped row that opens on a triangle, and stop the 110-character title cap from displaying an author's words nowhere.

**Architecture:** One `<details>` per entry, nested inside the existing `<article class="entry" id="{eid}">` so every anchor keeps resolving. The `<summary>` is a single `<h3 class="row">` holding id, badge, title and triangle. Clipping moves from a Python character cap to CSS `text-overflow`, which lets the whole sentence live in the DOM; `TITLE_CAP` and its entire orphaned-delimiter repair cascade are deleted rather than disabled.

**Tech Stack:** Python 3.14 (stdlib only), the in-file `--self-test` harness in `scripts/gen-dashboard.py`, `scripts/check-plan-code.py --mutate .` for mutation coverage. No new dependencies. No JS added — the browser's own disclosure widget carries the state.

**Spec:** `docs/superpowers/specs/2026-08-31-dashboard-collapsed-cards-design.md` v3 (`95f1d09f`). Reviews: `docs/reviews/spec-dashboard-collapsed-cards-r{1,2}-{codex,claude}.md`.

## Global Constraints

- **The page is DERIVED.** Never hand-edit `~/explainers/dashboard.html`. Regenerate via `scripts/gen-dashboard.py`. `.claude/hooks/regen-goals-page.sh` governs the goals page, not this one.
- **`EXPECTED_MUTATIONS` is exact equality, not a floor** (`scripts/check-plan-code.py:540`, `if got != want:`). Any change to a manifest's entry count must move the pin **in the same commit** (`:543`).
- **Coverage may shrink only with a written reason.** When mutations are deleted, the `EXPECTED_MUTATIONS` comment must name them and say they died with the code they guarded.
- **Anything longer than one line goes in a FILE**, never a shell argument: `git commit -F`, `--body-file`, `--prompt-file`. A backtick inside a double-quoted bash string is command substitution and has silently skipped a gate here before.
- **Current measured baselines** (2026-08-31, before any change): `gen-dashboard --self-test` **266/266**; `page_markup --self-test` **78/78**; `check-plan-code --mutate .` **5 files, 120 mutations, 0 survivors**; `EXPECTED_MUTATIONS` = gen-dashboard **56**, page_markup **14**, check-dashboard-entry **18**, check-plan-code **21**, page_chrome **11**.
- **Do not touch** `docs/dashboard-entries.md` content, the ask tray, the Worth-knowing block, the chart, or the glossary. Only the *What changed* cards change.
- **Branch:** `feat/dashboard-collapsed-cards`, already based on `origin/master`. Do not rebase onto anything else; PR #188 must not ride along.

---

### Task 1: Delete the title cap and its whole repair cascade — ONE commit, because the spec forbids splitting it

**Files:**
- Modify: `scripts/gen-dashboard.py:123-201` (delete the truncation branch, `_orphaned_delimiters`, `_close_orphan_markup`)
- Modify: `scripts/gen-dashboard.py:90` (delete `TITLE_CAP`)
- Modify: `scripts/gen-dashboard.py:250-271` (`_prose`: drop the `cap=` argument, pop unconditionally, rewrite the comment)
- Modify: `scripts/gen-dashboard.py` self-test region ~`:2377-2455` (delete 6 truncation cases, add 3)
- Test: the `--self-test` block inside `scripts/gen-dashboard.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `_first_sentence(text: str) -> str` — **one parameter**, no `cap`. Returns the full first sentence, never truncated, never ending in an author-absent `…`. `_prose(text: str, drop_headline: bool = False) -> str` — unchanged signature; now returns `""` when the entry's body is entirely its first sentence. Tasks 3 and 4 rely on both.

> ⚠ **This task carries THREE couplings the spec requires in one commit** (§3a). Splitting any of them ships a defect: the cap alone duplicates an unbounded paragraph, the guard relaxation alone re-opens the content loss, and deleting `cap` from the signature without fixing `_prose` raises `TypeError` on every normal entry.

- [ ] **Step 1: Write the failing tests**

Add these three cases immediately after the existing `case("a URL inside the first sentence does not end it", …)` case (~`:2455`):

```python
    # ⛔ THE DEFECT THIS SLICE EXISTS FOR. Two individually-correct rules composed
    # into content loss: `:428` cut the title at TITLE_CAP and `_prose` dropped the
    # whole first sentence, so everything between the cut and the full stop reached
    # NO reader. Measured on the live page 2026-08-31.
    #
    # ⚠ Tag-stripped, and the fixture is markup-BEARING on purpose. `_inline`
    # renders `**bold**` to `<strong>bold</strong>`, so a raw-substring assertion
    # would be false for correct output — the vacuity the spec's §4 M2 names.
    _bare_tags = re.compile(r"</?(?:strong|code|em|del|a)[^>]*>")
    _longsent = ("The backlog page refused to build until the newest item was described "
                 "in **plain words**, which is the `guard` doing its job. Second para.")
    _title_now = _bare_tags.sub("", _inline(_first_sentence(_longsent)))
    case("a long first sentence reaches the reader WHOLE",
         ("which is the guard doing its job." in _title_now,
          _title_now.endswith("…")),
         (True, False))
    case("the title is no longer capped at a character count",
         len(_first_sentence("y " * 200).strip()) > 110, True)
    # ⚠ THE WIRING. Every case above calls the helper directly; a complete page
    # build is what catches the `cap=` keyword surviving in `_prose` (Codex r1 H2).
    _norm = parse_entries("## 2026-08-31\nAn ordinary entry here.\n\nWith a body.\n")
    case("building a page with one ordinary entry does not raise",
         "An ordinary entry here." in build(
             entries=_norm, days=bucket_days(["2026-08-31"], _norm, 2, "2026-08-31"),
             prs=[], pr_error=None, git_error=None, window=2, exemptions=[],
             exempt_error=None, store="x", store_error=None, generated_at="t"),
         True)
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 scripts/gen-dashboard.py --self-test 2>&1 | tail -20`
Expected: FAIL. The first case fails because the title is cut and ends in `…`; the second fails because `len(...) > 110` is False.

- [ ] **Step 3: Delete `TITLE_CAP` and the truncation branch**

At `:90`, delete the whole `TITLE_CAP = 110` line and its comment.

Replace `_first_sentence` (`:123-159`) with:

```python
def _first_sentence(text: str) -> str:
    """The headline for an entry: its first SENTENCE, not its first LINE.

    It was `the first non-blank line`, which is a physical artefact of where the
    author's editor wrapped — so a heading read "...It is one page at" and
    stopped. A sentence is a unit of meaning; a line is a unit of typing.

    Short leading fragments ("Decided:", "Fixed.") are joined onto the next
    sentence rather than standing alone as the whole headline.

    ⟳ 2026-08-31: NOT TRUNCATED. There was a `cap` (TITLE_CAP = 110) and a
    repair, `_close_orphan_markup`, for the `**bold**` spans the cut orphaned.
    Both are gone. MEASURED on the live page: the cap cut the title while
    `_prose` dropped the whole first sentence, so the words between the cut and
    the full stop were displayed NOWHERE. Clipping is now CSS
    (`text-overflow: ellipsis`), which keeps the text in the DOM where find-in-page
    and an opened card can both reach it. The orphan repair existed only to heal a
    wound the cap inflicted; removing the cut removed the class.
    """
    text = " ".join(text.split())
    if not text:
        return ""
    out = ""
    for part in SENTENCE_END.split(text):
        out = f"{out} {part}".strip() if out else part
        if len(out) >= TITLE_FLOOR and not _ends_in_abbreviation(out):
            break
    return out
```

Delete `_orphaned_delimiters` (`:162-168`) and `_close_orphan_markup` (`:171-201`) entirely, including their docstrings. Keep the `# ── inline markup is NOT implemented here any more. Backlog #71.` comment block that follows, but **delete its last sentence** — the one reading "`_close_orphan_markup` stays above: it is dashboard TRUNCATION POLICY, not inline rendering, …" — because the function it refers to is gone.

- [ ] **Step 4: Fix `_prose` — coupling 1 (the `cap=` keyword) and couplings 2 and 3**

In `_prose`, replace `:252` through the end of the `drop_headline` block (`:271`) with:

```python
        head = _first_sentence(first)
        rest = first[len(head):].lstrip() if head else first
        if rest:
            paras[0] = rest
        else:
            # The whole first paragraph WAS the headline. Promote the next one —
            # or, with nothing to promote, return NOTHING and let the card render
            # as a plain row with no triangle (spec §2f).
            #
            # ⟳ 2026-08-31. This branch used to KEEP the repetition, on the stated
            # premise that "an empty fold is worse than a repeated sentence, and
            # there is nothing else to show." COLLAPSED CARDS OVERTURN THAT
            # PREMISE: an empty fold is no longer the alternative — no fold is.
            # A triangle that opens onto the sentence just read is a promise of
            # hidden content that isn't there. 6 of the store's 10 entries open
            # with a single-sentence paragraph, so this is the common case.
            #
            # ⚠ The no-terminator REFUSAL that used to guard this also went. Its
            # own reason was the cap — "the title showed only TITLE_CAP
            # characters" — and with the title uncapped it always displays the
            # paragraph whole, so dropping loses nothing. Keeping it would have
            # rendered an unbounded paragraph TWICE.
            paras.pop(0)
```

Delete the `if head == first and not first.rstrip().endswith((".", "!", "?")): head = ""` refusal and its comment block (`:253-261`).

- [ ] **Step 5: Delete the six truncation cases**

In the self-test region, delete:
1. the `for _delim, _elem in (("**", "strong"), ("`", "code")):` loop and its comment (2 cases);
2. `case("a truncated code span's CONTENT is a prefix of the full span's", …)` and its comment;
3. the whole `if STORE_DEFAULT.exists(): … else: …` block whose cases are `"no truncated title in the REAL store renders a bare delimiter"` and `"the REAL-store title check is skipped ONLY where there is no docs/"`;
4. `case("the cap bounds a title even when closers have to be added", …)`, its `_capbust` fixture and its comment;
5. `case("an over-long headline is cut at a WORD, with an ellipsis", …)`.

Also delete the case asserting the no-terminator refusal (search for `_noterm`, ~`:2087-2091`).

**KEEP** — these are not about truncation and deleting them is a coverage loss:
- `case("the URL trim keeps a HEX numeric entity too, not just the decimal form", …)`
- `case("a URL inside the first sentence does not end it", …)`
- every `_prose` case that does not mention a cap.

- [ ] **Step 6: Run the suite**

Run: `python3 scripts/gen-dashboard.py --self-test 2>&1 | tail -5`
Expected: PASS, all cases. The total drops from 266 by the number deleted and rises by 3. Record the new number — Task 6 needs it.

- [ ] **Step 7: Verify the defect is actually dead, by probe not by suite**

Run:

```bash
python3 - <<'PY'
import importlib.util
s=importlib.util.spec_from_file_location("gd","scripts/gen-dashboard.py")
gd=importlib.util.module_from_spec(s); s.loader.exec_module(gd)
long1=("The backlog page refused to build until the newest item was described in plain words, "
       "which is the guard doing exactly its job at the least convenient moment. Second para.")
t=gd._first_sentence(long1); pr=gd._prose(long1, drop_headline=True)
tail="at the least convenient moment"
print("TAIL IN TITLE?", tail in t)
print("TAIL IN PROSE?", tail in pr)
print("hasattr TITLE_CAP:", hasattr(gd,"TITLE_CAP"))
print("hasattr _close_orphan_markup:", hasattr(gd,"_close_orphan_markup"))
PY
```

Expected exactly:
```
TAIL IN TITLE? True
TAIL IN PROSE? False
hasattr TITLE_CAP: False
hasattr _close_orphan_markup: False
```

`TAIL IN PROSE? False` is correct and not a regression: the title now shows the sentence whole, so `drop_headline` removing it from the fold loses nothing. That is the whole point of coupling 2.

- [ ] **Step 8: Commit**

Write the message to a file first (never a `-m` string — the body contains backticks):

```bash
cat > "$SCRATCH/c1.txt" <<'EOF'
fix(dashboard): the title is no longer capped, so its tail stops vanishing

MEASURED on the live page: TITLE_CAP cut the title at 110 chars while
_prose(drop_headline=True) dropped the entry's whole first sentence, so the words
between the cut and the full stop were displayed NOWHERE.

Three couplings, deliberately in ONE commit (spec §3a):
  1. _prose must stop passing cap=len(first) or every normal entry raises
     TypeError once the parameter goes.
  2. The no-terminator refusal's own stated reason was the cap. Uncapped, not
     dropping renders an unbounded paragraph twice.
  3. The else-branch now pops instead of keeping the repetition. Its comment
     argued "an empty fold is worse than a repeated sentence" — collapsed cards
     overturn that premise, because no fold is the alternative.

_close_orphan_markup and _orphaned_delimiters are DELETED, not disabled. They
existed only to heal a wound the cut inflicted.
EOF
git commit -F "$SCRATCH/c1.txt"
```

---

### Task 2: Delete `page_markup.orphaned_delimiters`, now callerless

**Files:**
- Modify: `scripts/page_markup.py:253-269` (delete the function)
- Modify: `scripts/page_markup.py:435-439` (delete its 4 cases and the `# ── orphaned_delimiters` header comment)

**Interfaces:**
- Consumes: Task 1 having removed `gen-dashboard._orphaned_delimiters`, its only non-test consumer.
- Produces: nothing. Pure deletion.

- [ ] **Step 1: Prove it is callerless before deleting**

Run: `grep -rn "orphaned_delimiters" scripts/ | grep -v "^scripts/page_markup.py"`
Expected: **no output.** If anything prints, STOP — Task 1 is incomplete and this deletion would break a caller.

- [ ] **Step 2: Delete the function and its cases**

Delete `def orphaned_delimiters(text: str) -> int:` through the end of its body (`:253-269`), and in the self-test the `# ── orphaned_delimiters` comment plus these four cases:

```python
    case("orphans: balanced text has none", orphaned_delimiters("**a** `b`"), 0)
    case("orphans: an unpaired bold counts", orphaned_delimiters("**a"), 1)
    case("orphans: an unpaired backtick counts", orphaned_delimiters("a ` b"), 1)
    case("orphans: a delimiter inside code is NOT an orphan",
         orphaned_delimiters("`a ** b`"), 0)
```

- [ ] **Step 3: Run both suites**

Run: `python3 scripts/page_markup.py --self-test 2>&1 | tail -3 && python3 scripts/gen-dashboard.py --self-test 2>&1 | tail -3`
Expected: page_markup **74/74** (78 minus 4); gen-dashboard passing at Task 1's number.

- [ ] **Step 4: Confirm no mutation named it**

Run: `python3 -c "import json;d=json.load(open('scripts/mutations/page_markup.json'));ms=d if isinstance(d,list) else d.get('mutations',[]);print(len(ms), sum('orphaned_delimiters' in json.dumps(m) for m in ms))"`
Expected: `14 0`. So `EXPECTED_MUTATIONS["scripts/page_markup.py"]` stays **14** and needs no change. If the second number is not 0, the manifest must be edited and the pin moved with it in this commit.

- [ ] **Step 5: Commit**

```bash
git add scripts/page_markup.py
git commit -m "refactor(page_markup): delete orphaned_delimiters — its one consumer is gone" -m "Its docstring said 'Its one consumer is gen-dashboard._close_orphan_markup', which was literally true. That function went with the title cap. Measured: 14 mutations in page_markup.json, NONE naming it, so the pin stays at 14 and this deletion retires 4 self-test cases that no mutation ever covered." -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: The card becomes one fold inside the article

**Files:**
- Modify: `scripts/gen-dashboard.py:976-1003` (the entry-card emission loop)
- Test: the `--self-test` block in the same file

**Interfaces:**
- Consumes: `_first_sentence`/`_prose` from Task 1.
- Produces: the DOM contract Tasks 4 and 5 depend on — `<article class="entry" id="{eid}">` containing `<details id="{eid}-card">`, whose `<summary>` is `<h3 class="row">` holding `<span class="eid">`, an optional badge span, `<span class="title">`, and `<span class="tri" aria-hidden="true">`. The tech fold keeps id `{eid}-tech` and moves INSIDE the card fold. The id `{eid}-plain` no longer exists.

- [ ] **Step 1: Write the failing tests**

Add near the existing `case("the entry id is rendered", …)`:

```python
    # §4's binding rules: locate ONE synthetic entry's fragment and assert inside
    # it. A page-wide substring test is satisfied by the glossary and the ask
    # tray — `:1520` records that exact vacuity biting this file before.
    def _fragment(html_: str, eid: str) -> str:
        _start = html_.index(f'<article class="entry" id="{eid}">')
        return html_[_start:html_.index("</article>", _start)]

    _c = parse_entries("## 2026-08-31\nZorbal quandle sentence.\n\nGlimmerwax body.\n"
                       "<!--tech-->\nVexipop detail.\n")
    _ch = build(entries=_c, days=bucket_days(["2026-08-31"], _c, 2, "2026-08-31"),
                prs=[], pr_error=None, git_error=None, window=2, exemptions=[],
                exempt_error=None, store="x", store_error=None, generated_at="t")
    _frag = _fragment(_ch, "2026-08-31-1")
    # POSITIVE EXISTENCE FIRST — an assertion over an absent fixture passes while
    # the feature is missing.
    case("the entry fold exists, with its own id",
         ('<details id="2026-08-31-1-card"' in _frag, "<summary>" in _frag,
          '<h3 class="row"' in _frag, '<span class="title"' in _frag),
         (True, True, True, True))
    _summary = _frag[_frag.index("<summary>"):_frag.index("</summary>")]
    case("F2: the date appears ONCE in what the reader sees",
         _bare_tags.sub("", _summary).count("2026-08-31"), 1)
    case("F4: the tech fold is INSIDE the card fold, not a sibling",
         _frag.index('id="2026-08-31-1-tech"') <
         _frag.index("</details>", _frag.index('id="2026-08-31-1-card"')), True)
    case("F6: cards are shut by default", "<details id=\"2026-08-31-1-card\" open" in _frag, False)
    case("the -plain fold is gone", "-plain" in _ch, False)
    # F5: a parse failure must get LOUDER, not quieter.
    _brk = parse_entries("## not-a-date\nSomething.\n")
    _bh = build(entries=_brk, days=bucket_days([], _brk, 2, "2026-08-31"),
                prs=[], pr_error=None, git_error=None, window=2, exemptions=[],
                exempt_error=None, store="x", store_error=None, generated_at="t")
    case("F5: a broken entry is NOT foldable",
         ("entry broken" in _bh, "<details" in _bh[_bh.index("entry broken"):
                                                   _bh.index("</article>", _bh.index("entry broken"))]),
         (True, False))
    # F10: entry-level heading stops survive. Broken entries emit no <h3>; the ask
    # tray and Worth knowing emit <h2>, verified in review round 2.
    case("F10: one h3 per non-broken entry in What changed",
         _ch.count('<h3 class="row"'), 1)
    # F9 — the needs tray links to #{eid}, whose target lives on the ARTICLE
    # (:877-880). Moving the canonical id onto the new fold would leave every tray
    # link rendered, plausible, and resolving to nothing. Codex r1 M5.
    _ask = parse_entries("## 2026-08-31 [needs-you]\nSnorbit decision needed.\n\n"
                         "**Decide:** pick one\n- yes\n- no\n")
    _ah = build(entries=_ask, days=bucket_days(["2026-08-31"], _ask, 2, "2026-08-31"),
                prs=[], pr_error=None, git_error=None, window=2, exemptions=[],
                exempt_error=None, store="x", store_error=None, generated_at="t")
    _targets = set(re.findall(r'\sid="([^"]+)"', _ah))
    _trayrefs = set(re.findall(r'href="#([^"]+)"', _ah))
    case("F9: every in-page tray link resolves to an id that exists",
         (bool(_trayrefs), sorted(_trayrefs - _targets)), (True, []))
```

⚠ `_trayrefs` must be non-empty or this case is vacuous — that is why the first element of the tuple asserts it. A fixture that produced no tray link would otherwise pass by having nothing to check.

- [ ] **Step 2: Run to verify they fail**

Run: `python3 scripts/gen-dashboard.py --self-test 2>&1 | tail -20`
Expected: FAIL — `substring not found` on `<details id="2026-08-31-1-card"`.

- [ ] **Step 3: Rewrite the card emission**

Replace the non-broken branch (`:989-1002`) with:

```python
            tech = ("" if not e["tech"] else
                    f'<details id="{eid}-tech"><summary>Raw technical detail</summary>'
                    f'<pre>{_html.escape(e["tech"])}</pre></details>')
            _b = badge_of(e, _cleared)
            _bcls = "flag resolved" if _b == "resolved" else "flag"
            flag = (f'<span class="{_bcls}">{_html.escape(_b)}</span>') if _b else ""
            prose = _prose(e["plain"], drop_headline=True)
            # §2f: a disclosure that discloses NOTHING is a lie about the content.
            # Suppress the fold only when there is no prose AND no tech block —
            # round 2 measured that comparing prose TEXT to the title took the
            # only route to the raw detail with it.
            body = (f'<div class="prose">{prose}</div>' if prose else "") + tech
            # ⚠ ONE <h3> is the summary's ENTIRE content. <summary>'s content model
            # is phrasing content OR a single heading element — the old
            # `<p class="title">` was neither, and a <summary> is not itself a
            # heading, so without this the page loses its per-entry heading stops.
            row = (f'<h3 class="row"><span class="eid">{_html.escape(e["id"])}</span>'
                   f'{flag}<span class="title">{_inline(e["title"])}</span>'
                   f'<span class="tri" aria-hidden="true"></span></h3>')
            inner = (f'<details id="{eid}-card"><summary>{row}</summary>{body}</details>'
                     if body else row)
            parts.append(f'{day_anchor}<article class="entry" id="{eid}">{inner}</article>')
```

The bare date is gone from the row: `e["id"]` already contains it (`:379`).

- [ ] **Step 4: Run the suite**

Run: `python3 scripts/gen-dashboard.py --self-test 2>&1 | tail -6`
Expected: PASS. If `every details has an id` (`:1701`) fails, the new fold is missing its id.

- [ ] **Step 5: Extend the `:1525` comment, do not replace it**

The case `"tech is behind a fold"` stays. Append to its comment:

```python
    # ⟳ 2026-08-31: the bare form is now wrong a SECOND way — the entry card
    # itself emits a <details>, so `"<details" in html` would pass with the tech
    # fold deleted for two independent reasons rather than one.
```

- [ ] **Step 6: Commit**

Message file, then `git commit -F`. Subject: `feat(dashboard): each entry card is one row that opens on a triangle`.

---

### Task 4: The §2f suppression rule, pinned by falsifiers

**Files:**
- Modify: `scripts/gen-dashboard.py` self-test block only (Task 3 already implemented the rule via `if body else row`)

**Interfaces:**
- Consumes: Task 3's `body`/`inner` logic and Task 1's `_prose` returning `""`.
- Produces: nothing consumed downstream.

> This task is separate from Task 3 on purpose: a reviewer can reject the suppression rule's coverage while accepting the markup change. It has no implementation step — if a case fails here, the defect is in Task 3's `if body else row`.

- [ ] **Step 1: Write the tests**

```python
    # §2f. F8/F8b/F8c — the rule that only exists BECAUSE of the collapse, and the
    # hole round 2 found in its first wording.
    _solo = parse_entries("## 2026-08-31\nFlimbert solo sentence.\n")
    _sh = build(entries=_solo, days=bucket_days(["2026-08-31"], _solo, 2, "2026-08-31"),
                prs=[], pr_error=None, git_error=None, window=2, exemptions=[],
                exempt_error=None, store="x", store_error=None, generated_at="t")
    _sfrag = _fragment(_sh, "2026-08-31-1")
    case("F8: a single-sentence entry with no tech has NO fold and NO triangle",
         ("<details" in _sfrag, 'class="tri"' in _sfrag,
          "Flimbert solo sentence." in _sfrag),
         (False, False, True))
    # ⛔ F8b — THE ROUND-2 DEFECT. v2's rule suppressed on prose==title, which for
    # this input took the ONLY route to the raw detail with it.
    _solotech = parse_entries("## 2026-08-31\nWurbleflux alone.\n<!--tech-->\nQuixtan detail.\n")
    _sth = build(entries=_solotech, days=bucket_days(["2026-08-31"], _solotech, 2, "2026-08-31"),
                 prs=[], pr_error=None, git_error=None, window=2, exemptions=[],
                 exempt_error=None, store="x", store_error=None, generated_at="t")
    _stfrag = _fragment(_sth, "2026-08-31-1")
    case("F8b: a tech block ALWAYS keeps its route, even with an empty plain half",
         ('<details id="2026-08-31-1-card"' in _stfrag,
          'id="2026-08-31-1-tech"' in _stfrag, "Quixtan detail." in _stfrag),
         (True, True, True))
    case("F8c: no empty prose container is emitted",
         '<div class="prose"></div>' in _sth, False)
```

- [ ] **Step 2: Run**

Run: `python3 scripts/gen-dashboard.py --self-test 2>&1 | tail -6`
Expected: PASS. A failure on F8b means `body` is being computed from prose alone.

- [ ] **Step 3: Commit**

Subject: `test(dashboard): pin §2f — no fold with nothing behind it, but tech always keeps its route`.

---

### Task 5: The CSS — a flex row that clips, and un-clips when opened

**Files:**
- Modify: `scripts/gen-dashboard.py` stylesheet inside the `build()` f-string (the `.entry .title` rule and the `details`/`summary` rules)

**Interfaces:**
- Consumes: Task 3's class names — `.row`, `.eid`, `.title`, `.tri`, `.flag`.
- Produces: nothing consumed by later tasks.

> ⚠ **Braces are DOUBLED** — this stylesheet lives in an f-string. `{{` and `}}`.

- [ ] **Step 1: Replace the title and fold rules**

Replace `.entry .title{{margin:0;font-weight:600;line-height:1.4;max-width:60ch;color:var(--p-head)}}` with:

```
.entry summary{{display:flex;list-style:none;cursor:pointer;padding:2px 0}}
.entry summary::-webkit-details-marker{{display:none}}
.entry .row{{display:flex;gap:.6rem;align-items:baseline;margin:0;font-size:1rem;
  font-weight:600;width:100%;min-width:0}}
/* ⚠ flex:1 AND min-width:0. A flex item defaults to min-width:auto and refuses
   to shrink below its content, so text-overflow:ellipsis NEVER engages without
   it — measured in spec review round 1 (Codex Blocking 1). */
.entry .title{{flex:1;min-width:0;white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis;font-weight:600;color:var(--p-head)}}
/* Opening a card un-clips ITS OWN title. The selector is `.entry details[open]`,
   NOT `details[open] .entry` — `.entry` is the ARTICLE, an ancestor of the fold,
   so the descendant form matches nothing. */
.entry details[open] .title{{white-space:normal;overflow:visible;max-width:60ch}}
.entry .tri{{flex:none;color:var(--fg3);font-size:11px;align-self:center}}
.entry .tri::before{{content:"\\25B8"}}
.entry details[open] .tri::before{{content:"\\25BE"}}
```

The clipped text stays in the DOM, so find-in-page still reaches it.

- [ ] **Step 2: Keep the nested tech fold indented and readable**

Add:

```
.entry details details{{margin-top:10px;margin-left:0}}
.entry .prose{{margin-top:10px}}
```

- [ ] **Step 3: Run the suite — the contrast guards read the EMITTED stylesheet**

Run: `python3 scripts/gen-dashboard.py --self-test 2>&1 | tail -6`
Expected: PASS, including every `clears WCAG AA` case. Those parse the emitted CSS and will raise, not silently skip, if a palette block goes missing.

- [ ] **Step 4: Commit**

Subject: `style(dashboard): collapsed rows clip with an ellipsis and un-clip when opened`.

---

### Task 6: Mutation coverage — new entries, deleted entries, and the pin moved in the same commit

**Files:**
- Modify: `scripts/mutations/gen-dashboard.json`
- Modify: `scripts/check-plan-code.py:432-450` (`EXPECTED_MUTATIONS` and its comment)

**Interfaces:**
- Consumes: the delivered code from Tasks 1, 3, 4, 5.
- Produces: nothing.

- [ ] **Step 1: Delete the three mutations that guarded deleted code**

Remove, by exact `name`:
- `a truncated headline is not re-balanced, so an orphan delimiter ships`
- `the orphan closer becomes a SECOND scanner again, disagreeing on code`
- `closers are appended PAST the cap, so TITLE_CAP stops bounding`

- [ ] **Step 2: Add mutations for the new properties**

Each entry needs `name`, `file`, `edits` (a `find`/`replace` pair matching the delivered source **exactly once**) and `expect` naming the case that must go red. Add:

1. **name:** `the collapsed title stops clipping, so a long row wraps by default`
   **edit:** in the `.entry .title` rule, `white-space:nowrap;` → `white-space:normal;`
   **expect:** a new case asserting the emitted CSS contains `white-space:nowrap` inside `.entry .title` — add it in Task 5's step 3 region if absent.
2. **name:** `the fold is emitted even when nothing is behind it`
   **edit:** `inner = (f'<details id="{eid}-card">…' if body else row)` → drop the `if body else row` conditional so the fold is unconditional.
   **expect:** `F8: a single-sentence entry with no tech has NO fold and NO triangle`
3. **name:** `the suppression rule is computed from prose alone, hiding the tech route`
   **edit:** `body = (f'<div class="prose">{prose}</div>' if prose else "") + tech` → `body = (f'<div class="prose">{prose}</div>' if prose else "")`
   **expect:** `F8b: a tech block ALWAYS keeps its route, even with an empty plain half`
4. **name:** `the bare date returns to the row`
   **edit:** `<span class="eid">{_html.escape(e["id"])}</span>` → `{_html.escape(e["date"])} <span class="eid">{_html.escape(e["id"])}</span>`
   **expect:** `F2: the date appears ONCE in what the reader sees`
5. **name:** `the title is capped again, so its tail vanishes`
   **edit:** in `_first_sentence`, `    return out` → `    return out[:110] + "…" if len(out) > 110 else out`
   **expect:** `a long first sentence reaches the reader WHOLE`
6. **name:** `the row stops being a heading, losing every per-entry stop`
   **edit:** `<h3 class="row">` → `<div class="row">` (and the closing tag)
   **expect:** `F10: one h3 per non-broken entry in What changed`

> ⚠ **Take `expect` FROM THE RUN, not from this document.** A mutation that CRASHES the suite instead of reddening the case it names is rejected by the harness, correctly. If a `find` string matches more than once, `--mutate .` refuses — narrow it with surrounding context.

- [ ] **Step 3: Run the mutation harness**

Run: `python3 scripts/check-plan-code.py --mutate . 2>&1 | tail -25`
Expected: `0 survivor(s)`, and a drift error naming the new gen-dashboard count — that error is the harness demanding step 4.

- [ ] **Step 4: Move the pin, with the reason in the comment**

Set `EXPECTED_MUTATIONS["scripts/gen-dashboard.py"]` to the measured number and append:

```python
    # ⟳ 2026-08-31, collapsed cards: gen-dashboard 56 -> <measured>. THREE entries were
    # DELETED WITH THE CODE THEY GUARDED, not narrowed — the orphan-delimiter repair
    # existed only to heal a cut that no longer happens (spec §3a):
    #   "a truncated headline is not re-balanced, so an orphan delimiter ships"
    #   "the orphan closer becomes a SECOND scanner again, disagreeing on code"
    #   "closers are appended PAST the cap, so TITLE_CAP stops bounding"
    # Six were added for the collapse: the CSS clip, the §2f suppression in both
    # directions, the returning bare date, a re-introduced cap, and the row's
    # heading element. page_markup stays at 14 — MEASURED: none of its mutations
    # named `orphaned_delimiters`, so deleting that function moved no coverage.
```

- [ ] **Step 5: Re-run to green**

Run: `python3 scripts/check-plan-code.py --mutate . 2>&1 | tail -8`
Expected: no drift error, `0 survivor(s)`.

- [ ] **Step 6: Commit**

Subject: `test(dashboard): mutation coverage for the collapse; retire the three that guarded the cut`.

---

### Task 7: Regenerate, drive it in a real browser, and record the entry

**Files:**
- Create: a dashboard entry appended to `docs/dashboard-entries.md`
- Regenerate: the dashboard page (not tracked)

**Interfaces:**
- Consumes: everything above.

> **Neither review half observed a flex ellipsis in a browser.** §6 says the falsifiers are necessary and not sufficient. This task is the sufficiency.

- [ ] **Step 1: Regenerate and serve**

Run: `python3 scripts/gen-dashboard.py && EXPLAINER_DOCS_ROOT=$PWD python3 scripts/explainer-serve.py &`

- [ ] **Step 2: Drive it in Chrome and observe, one assertion per observation**

Open `http://127.0.0.1:7391/dashboard`. Confirm by looking, and screenshot each to `.screenshots/` (gitignored):
1. every card is one row, and appreciably more than five fit on a screen;
2. a long title ends in a real ellipsis, and **narrowing the window** moves where it clips — proving CSS owns it;
3. clicking a row opens it, the title wraps to its full sentence, and the triangle turns down;
4. an entry with a tech block shows `Raw technical detail` **inside** the opened card, at the end;
5. a single-sentence entry has **no** triangle;
6. Cmd-F for a word visible only in a clipped title finds and reveals it;
7. the theme toggle still works in both directions (the page-chrome seam is untouched but shares the stylesheet).

- [ ] **Step 3: Record the dashboard entry**

`scripts/check-dashboard-entry.py` requires a branch that changes tracked files to record one. Append an entry describing the collapse in plain words, with a `<!--tech-->` half naming the deleted cascade.

- [ ] **Step 4: Full gate sweep**

```bash
python3 scripts/gen-dashboard.py --self-test
python3 scripts/page_markup.py --self-test
python3 scripts/check-dashboard-entry.py --self-test
python3 scripts/check-docs.py
python3 scripts/check-anchors.py
python3 scripts/check-review-rounds.py
python3 scripts/check-ratchet-contract.py --self-test
python3 scripts/check-plan-code.py --mutate .
```
Expected: every one exit 0. **A "cannot run" is a FAILURE, not a pass.**

- [ ] **Step 5: Commit and open the PR**

Body in a file, `gh pr create --body-file`. **Write the roadmap/backlog tick BEFORE opening the PR.** Then STOP: **merging is a human gate.** Notify with one line leading on the decision needed.

---

## Self-Review

**Spec coverage.** §1a → T3; §1b → T3 (bare date removed) + F2; §1c → T1 + the step-7 probe; §2a → T3 (`<h3 class="row">`, F10); §2b → T3, F9; §2c → T5; §2d → T3 (`tech` inside `body`); §2e → T3 F5; §2f → T3 implementation + T4 cases; §2g → T3 F6; §3a → T1 + T2; §3b → T6; §4 F1–F13 → T1 (F1, F7, F11), T3 (F2–F6, F9, F10, F12, F13 — the last two via the existing `no duplicate DOM ids` and `every details has an id` cases), T4 (F8, F8b, F8c); §5 out-of-scope respected; §6 blast radius = T1/T2/T3/T5 files only.

> **A gap this review actually found and closed:** F9 ("every tray link resolves") had no task step in the first draft — the one falsifier covering a *cross-section* coupling, which is exactly the kind a task-by-task plan drops, because no single task owns it. It is now a case in T3 step 1, with a non-vacuity assertion on `_trayrefs` so an empty fixture cannot pass it.

**Placeholder scan.** One deliberate `<measured>` in T6 step 4, required by the Global Constraint forbidding a predicted mutation count. Every other step carries literal code. A stray `git commit -F /tmp/none` line in T1 step 8 was found and deleted.

**Type consistency.** `_first_sentence(text)` single-parameter in T1, called that way in T1 step 3's `_prose` patch and in T6's mutation 5. `_fragment(html_, eid)` defined in T3 step 1 and reused in T4 step 1 — T4 depends on T3's helper being in scope, which holds because both live in the same `--self-test` function body. `_bare_tags` defined in T1 step 1 and reused in T3 step 1 — same scope, same ordering requirement: **T1's cases must appear textually before T3's.**
