# Dashboard Ask Choices — Implementation Plan

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them — without reading the chat transcript.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (the project default, `docs/dev-process.md` Phase 3) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Spec:** [`2026-08-31-dashboard-ask-choices-design.md`](../specs/2026-08-31-dashboard-ask-choices-design.md) **v3**, commit `77f63f3`.

⚠ **Never write the word `resolved` in ALL CAPS anywhere in this plan — prose, comment or test-case
name.** `check-docs.py:52` treats that one spelling as an undocumented decision marker and adds the
document to the roadmap's "spec docs holding decisions with no ADR" triage list. Measured
2026-08-31: a single test-case name using the shouted spelling moved that derived count 21 → 22, and
then **the warning first written here re-tripped it twice by quoting the word it was warning
about** — the check matches **vocabulary, not property**, so even describing the trap springs it.
This plan documents no decision the ADRs lack; the lower-case spelling is used throughout, and the
case is named `a cleared ask is never validated`.

**Goal:** A dashboard ask states the decisions it is asking the reader to make, with named options and live pull-request links; anything that merely needs awareness says so separately.

**Architecture:** Renderer-only enforcement (spec §2 — the CI gate half is backlog #78). `scripts/check-dashboard-entry.py` owns the grammar and gains `decision_errors`; `scripts/gen-dashboard.py` imports it and calls it **after** `unresolved()`, over unresolved entries only. `decision_errors` never writes `entry["error"]`, which is what keeps historical entries intact and keeps a malformed ask visible instead of filtered away.

**Tech Stack:** Python 3 stdlib only. In-file `--self-test` suites (no pytest). Mutation coverage via `scripts/mutations/*.json` + `EXPECTED_MUTATIONS` in `scripts/check-plan-code.py`.

## Global Constraints

- **Python 3 stdlib only.** No new dependencies in `scripts/`.
- **`decision_errors` MUST NOT set `entry["error"]`** (spec §8b). Writing that field re-creates the five-entry cascade and the "Nothing needs you." fall-through.
- **Validate only UNRESOLVED entries** (spec §8b, §11). There is no cutover date.
- **`**Decide:**` is recognised only outside fenced code, indented code, HTML comments and blockquotes** (spec §4) — reuse `check-dashboard-entry.py`'s existing scanner, do not write a fifth one.
- **PR references are the literal token `PR #N`, never a bare `#N`** (spec §4).
- **PR lookup budget: at most 10 distinct lookups and 60 seconds per render**; exhaustion renders `could not check — PR lookup budget exhausted`, distinct from `could not check` (spec §6).
- **Coverage cannot shrink.** `EXPECTED_MUTATIONS` currently holds `gen-dashboard.py: 47`, `check-dashboard-entry.py: 12` (`scripts/check-plan-code.py:443,:445`). Both rise; neither falls.
- **Baselines to preserve:** `gen-dashboard.py --self-test` = 217/217 + 6/6 cannot-run; `check-dashboard-entry.py --self-test` = 46/46. Every task raises these, never lowers them.
- **Run from the repo root.** `python3 scripts/<name>.py`.
- ⚠ **EVERY "Expected: PASS at N/N" tally in this plan is an ESTIMATE, and round 1 proved several
  wrong.** Take the real number from the run. What is binding is the *direction* — the count must
  **rise** by at least the cases the task adds, and no previously-passing case may go red. If one
  does, that is a finding, not a number to update.
- ⚠ **A step that says "run it to verify it fails" must actually go red.** Round 1 found four cases
  that already passed before their implementation (Task 4's cleared-ask pair, Task 5's fold and
  empty-heading pair). They are useful **regression guards**, not red-phase evidence — do not report
  a red phase you did not observe.

---

### Task 1: The `heads-up` flag reaches the parser without killing the page

**Files:**
- Modify: `scripts/check-dashboard-entry.py:26` (`FLAG`)
- Modify: `scripts/gen-dashboard.py:369-383` (the flag `if/elif/else`), `:356` (entry dict)
- Test: both files' in-file `_self_test`

**Interfaces:**
- Consumes: nothing.
- Produces: `FLAG` accepts `heads-up`; `parse_entries` returns entries with a new key `heads_up: bool` alongside the existing `needs_you: bool`. Later tasks read `e["heads_up"]`.

⚠ **Why these two edits are ONE task:** `gen-dashboard.py:369-383`'s own comment records that adding an alternative to `FLAG` while leaving the parser's `else` alone left the gate's suite **fully green** and raised `IndexError` on **every** render — the page stopped existing. Splitting them would ship that state.

- [ ] **Step 1: Write the failing tests**

In `scripts/gen-dashboard.py`'s `_self_test`, after the existing `typo = parse_entries(...)` cases:

```python
    hu = parse_entries("## 2026-08-28 [heads-up]\nWorth knowing.\n")
    case("heads-up parses", hu[0]["error"], None)
    case("heads-up sets heads_up", hu[0]["heads_up"], True)
    case("heads-up is not needs_you", hu[0]["needs_you"], False)
    both = parse_entries("## 2026-08-28 [needs-you] [heads-up]\nBoth.\n")
    case("both flags is an error", both[0]["error"] is not None, True)
    ny = parse_entries("## 2026-08-28 [needs-you]\nAn ask.\n")
    case("needs-you does not set heads_up", ny[0]["heads_up"], False)
```

In `scripts/check-dashboard-entry.py`'s `_self_test`, beside the existing flag cases:

```python
    case("a heads-up header counts", _added_entry_line("+## 2026-08-28 [heads-up]"), True)
    case("heads-up header_error is None", header_error("## 2026-08-28 [heads-up]"), None)
    case("a typo'd heads-up does NOT count", _added_entry_line("+## 2026-08-28 [heads-u]"), False)
```

- [ ] **Step 2: Run both suites to verify they fail**

```bash
python3 scripts/gen-dashboard.py --self-test
python3 scripts/check-dashboard-entry.py --self-test
```

Expected: FAIL. `gen-dashboard` reports `[FAIL] heads-up parses` (the flag falls to the `else` and becomes `unrecognised flag [heads-up]`), and `KeyError: 'heads_up'` or `[FAIL] heads-up sets heads_up`. `check-dashboard-entry` reports `[FAIL] a heads-up header counts`.

- [ ] **Step 3: Widen the grammar**

`scripts/check-dashboard-entry.py:26`:

```python
FLAG = re.compile(r"\[(needs-you|heads-up|resolved:\s*[^\]]*)\]")
```

- [ ] **Step 4: Teach the parser the new alternative**

`scripts/gen-dashboard.py:356` — add the key to the entry dict:

```python
        entry = {"raw": "\n".join(b), "error": None, "needs_you": False,
                 "heads_up": False, "resolves": [],
                 "date": None, "ordinal": 0, "id": None, "would_be_id": None,
                 "title": "", "plain": "", "tech": None}
```

`scripts/gen-dashboard.py:378-383` — handle it explicitly, and refuse both flags at once (spec §4):

```python
                if f == "needs-you":
                    entry["needs_you"] = True
                elif f == "heads-up":
                    entry["heads_up"] = True
                elif f.startswith("resolved:"):
                    entry["resolves"].append(f.split(":", 1)[1].strip())
                else:
                    entry["error"] = f"unrecognised flag [{f}]"
```

- [ ] **Step 4b: The both-flags refusal goes in `header_error`, NOT in the parser**

⚠ **Round-1 review, execution-verified.** Putting it only in the parser makes the gate and the
renderer disagree: `header_error` strips every flag via `FLAG.sub` (`check-dashboard-entry.py:51`),
so `header_error("## 2026-08-28 [needs-you] [heads-up]")` returns `None` — the **gate accepts** a
header the **renderer** would mark malformed. `header_error`'s own docstring (`:38-45`) says it is
*"shared by the parser and the ratchet so they CANNOT disagree about what a header is"* and records
five measured divergences; this would be the sixth. Spec §9 lists it as a falsifier by name.

In `scripts/check-dashboard-entry.py`, inside `header_error`, after the `leftover` check:

```python
    flags = FLAG.findall(m.group(2))
    if "needs-you" in flags and "heads-up" in flags:
        return ("an entry is [needs-you] OR [heads-up], never both — "
                "a heads-up asks for nothing")
```

The parser needs no both-flags branch: `parse_entries` already assigns `err = header_error(b[0])`
(`gen-dashboard.py:359`) and returns the entry with that error.

Add to `check-dashboard-entry.py`'s `_self_test`:

```python
    case("both flags is a header error",
         header_error("## 2026-08-28 [needs-you] [heads-up]") is not None, True)
    case("both flags does not count as an added entry",
         _added_entry_line("+## 2026-08-28 [needs-you] [heads-up]"), False)
```

- [ ] **Step 5: Run both suites to verify they pass**

```bash
python3 scripts/gen-dashboard.py --self-test
python3 scripts/check-dashboard-entry.py --self-test
```

Expected: PASS, at 222/222 and 49/49 (217+5, 46+3).

- [ ] **Step 6: Prove the page still renders**

```bash
python3 scripts/gen-dashboard.py && python3 scripts/check-docs.py
```

Expected: `wrote /Users/…/explainers/dashboard.html (26 entries, window 14)` and `Documentation integrity OK`. This is the falsifier for the recorded `IndexError` — a green suite is not sufficient evidence here.

- [ ] **Step 7: Commit**

```bash
git add scripts/check-dashboard-entry.py scripts/gen-dashboard.py
git commit -m "feat(dashboard): heads-up flag, refused when combined with needs-you"
```

---

### Task 2: Badges are derived, not authored — the defect the user reported

**Files:**
- Modify: `scripts/gen-dashboard.py:439-451` (`unresolved`), `:768` (the badge)
- Test: in-file `_self_test`

**Interfaces:**
- Consumes: `e["heads_up"]` from Task 1.
- Produces: `cleared_ids(entries) -> set[str]`, `unresolved_heads_up(entries) -> list[dict]`, and `badge_of(entry, cleared) -> str` (`""`, `"needs you"`, `"heads-up"`, `"resolved"`). Task 4 reuses `cleared_ids`; **Task 5 calls `unresolved_heads_up`**. `unresolved(entries)` keeps its existing signature and behaviour.

- [ ] **Step 1: Write the failing test**

In `_self_test`:

```python
    st = parse_entries(
        "## 2026-08-28 [needs-you]\nAn open ask.\n"
        "## 2026-08-29 [heads-up]\nWorth knowing.\n"
        "## 2026-08-30 [resolved: 2026-08-28/1]\nDone with it.\n"
        "## 2026-08-31\nOrdinary entry.\n")
    cl = cleared_ids(st)
    case("the resolved ask is cleared", "2026-08-28/1" in cl, True)
    case("resolved ask badges as resolved", badge_of(st[0], cl), "resolved")
    case("open heads-up badges as heads-up", badge_of(st[1], cl), "heads-up")
    case("the clearing entry has no badge", badge_of(st[2], cl), "")
    case("an ordinary entry has no badge", badge_of(st[3], cl), "")
    op = parse_entries("## 2026-08-28 [needs-you]\nStill open.\n")
    case("an open ask badges as needs you", badge_of(op[0], cleared_ids(op)), "needs you")
```

- [ ] **Step 2: Run to verify it fails**

```bash
python3 scripts/gen-dashboard.py --self-test
```

Expected: FAIL with `NameError: name 'cleared_ids' is not defined`.

- [ ] **Step 3: Extract `cleared_ids` and add `badge_of`**

Replace `scripts/gen-dashboard.py:439-451` with:

```python
def cleared_ids(entries: list[dict]) -> set[str]:
    """Ids cleared by a LATER [resolved: <id>] (spec §6.2).

    Split out of `unresolved` so the BADGE and the tray answer from one
    computation. §1a of the ask-choices spec is exactly what happens when the
    card answers "does this need you?" from a different source than the tray.
    """
    by_id = {e["id"]: e for e in entries if e["id"] and not e["error"]}
    cleared = set()
    for e in entries:
        if e["error"]:
            continue
        for r in e["resolves"]:
            t = by_id.get(r)
            if t is not None and _pos(e) > _pos(t):
                cleared.add(t["id"])
    return cleared


def unresolved(entries: list[dict]) -> list[dict]:
    """needs-you entries not cleared by a LATER [resolved: <id>] (spec §6.2)."""
    cleared = cleared_ids(entries)
    return [e for e in entries
            if e["needs_you"] and not e["error"] and e["id"] not in cleared]


def unresolved_heads_up(entries: list[dict]) -> list[dict]:
    """heads-up entries not cleared. Same mechanism, no second protocol."""
    cleared = cleared_ids(entries)
    return [e for e in entries
            if e["heads_up"] and not e["error"] and e["id"] not in cleared]


def badge_of(entry: dict, cleared: set[str]) -> str:
    """The card's badge, DERIVED (spec §5c).

    Before this, `:768` printed the raw authored `needs_you` flag, which nothing
    ever cleared — so three asks the tray had correctly dropped still wore a
    "needs you" chip. The page answered one question two ways.
    """
    if entry["error"] or not (entry["needs_you"] or entry["heads_up"]):
        return ""
    if entry["id"] in cleared:
        return "resolved"
    return "needs you" if entry["needs_you"] else "heads-up"
```

- [ ] **Step 4: Render the derived badge**

`scripts/gen-dashboard.py`, in `build`, before the entry loop that contains `:768`, compute once:

```python
    _cleared = cleared_ids(entries)
```

Then replace the `flag = ...` line at `:768`:

```python
            _b = badge_of(e, _cleared)
            flag = (f' <span class="flag {"resolved" if _b == "resolved" else ""}">'
                    f'{_html.escape(_b)}</span>') if _b else ""
```

- [ ] **Step 5: Add the muted style**

In the page's CSS block, beside the existing `.flag` rule, add:

```css
.flag.resolved{background:transparent;border:1px solid currentColor;opacity:.55;font-weight:400}
```

- [ ] **Step 6: Run to verify it passes**

```bash
python3 scripts/gen-dashboard.py --self-test
```

Expected: PASS at 228/228.

- [ ] **Step 7: Prove it against the REAL store — the reported defect**

```bash
python3 scripts/gen-dashboard.py
python3 - <<'PY'
import pathlib, re
h = (pathlib.Path.home() / "explainers/dashboard.html").read_text()
print("needs-you badges:", len(re.findall(r'class="flag ">needs you<', h)))
print("resolved badges :", len(re.findall(r'class="flag resolved">resolved<', h)))
print("tray says       :", "Nothing needs you." in h)
PY
```

Expected: `needs-you badges: 0`, `resolved badges : 3`, `tray says: True`. **Before this task the same script prints 3 / 0 / True — the contradiction the user reported.**

- [ ] **Step 8: Commit**

```bash
git add scripts/gen-dashboard.py
git commit -m "fix(dashboard): derive the entry badge so a resolved ask stops saying it needs you"
```

---

### Task 3: `decision_errors` — the validator, blind to inert markdown

**Files:**
- Modify: `scripts/check-dashboard-entry.py` (new function, near `exemption_reason`)
- Test: `scripts/check-dashboard-entry.py` `_self_test`

**Interfaces:**
- Consumes: the module's existing fence/indent/comment/blockquote scanning used by `exemption_reason` (`:83-138`).
- Produces: `decision_errors(plain: str, category: str) -> list[str]` — `category` is `"needs-you"` or `"heads-up"`. Empty list means valid. Also `decisions(plain: str) -> list[dict]` with keys `question: str`, `options: list[dict]`, each option `{"text": str, "recommended": bool}`. Tasks 4 and 6 consume `decisions`.

- [ ] **Step 1: Write the failing tests**

In `scripts/check-dashboard-entry.py`'s `_self_test`:

```python
    GOOD = ("An ask.\n\n**Decide:** Merge it\n- merge PR #181 [recommended]\n"
            "- hold it and tell me what to change\n")
    case("a good decision parses", len(decisions(GOOD)), 1)
    case("its question", decisions(GOOD)[0]["question"], "Merge it")
    case("two options", len(decisions(GOOD)[0]["options"]), 2)
    case("recommended is marked", decisions(GOOD)[0]["options"][0]["recommended"], True)
    case("recommended stripped from text",
         decisions(GOOD)[0]["options"][0]["text"], "merge PR #181")
    case("a good needs-you passes", decision_errors(GOOD, "needs-you"), [])

    case("no decision at all fails",
         len(decision_errors("Just prose.\n", "needs-you")), 1)
    case("one option fails",
         len(decision_errors("**Decide:** Q\n- only one\n", "needs-you")), 1)
    case("empty question fails",
         len(decision_errors("**Decide:**\n- a\n- b\n", "needs-you")), 1)
    case("empty option text fails",
         len(decision_errors("**Decide:** Q\n- [recommended]\n- b\n", "needs-you")), 1)
    case("two recommendations fail",
         len(decision_errors("**Decide:** Q\n- a [recommended]\n- b [recommended]\n",
                             "needs-you")), 1)
    case("a heads-up that asks fails",
         len(decision_errors(GOOD, "heads-up")), 1)
    case("a heads-up with prose passes", decision_errors("Worth knowing.\n", "heads-up"), [])

    FENCED = ("Announcing the grammar.\n\n```\n**Decide:** Not a real ask\n- a\n- b\n```\n")
    case("a fenced Decide is not a decision", decisions(FENCED), [])
    case("a fenced Decide does not break a heads-up",
         decision_errors(FENCED, "heads-up"), [])
    QUOTED = "> **Decide:** quoted\n> - a\n> - b\n"
    case("a blockquoted Decide is not a decision", decisions(QUOTED), [])
    COMMENTED = "<!--\n**Decide:** hidden\n- a\n- b\n-->\n"
    case("a commented Decide is not a decision", decisions(COMMENTED), [])
    INDENTED = "    **Decide:** indented code\n    - a\n    - b\n"
    case("an indented Decide is not a decision", decisions(INDENTED), [])
    STARS = "**Decide:** Q\n* a\n* b\n"
    case("star markers are options", len(decisions(STARS)[0]["options"]), 2)
    ADJACENT = "**Decide:** One\n- a\n- b\n**Decide:** Two\n- c\n- d\n"
    case("adjacent decisions both parse", len(decisions(ADJACENT)), 2)
    GAP = "**Decide:** Q\n\n- a\n- b\n"
    case("a blank line after the opener means no options",
         len(decisions(GAP)[0]["options"]), 0)

    # ── round-1 review: every one of these FAILED against the first implementation ──
    NEST2 = "**Decide:** Q\n- merge PR #1\n  - it is green\n- hold it\n"
    case("a 2-space nested item is not a peer option",
         [o["text"] for o in decisions(NEST2)[0]["options"]],
         ["merge PR #1 it is green", "hold it"])
    NEST4 = "**Decide:** Q\n- merge PR #1\n    - it is green\n- hold it\n"
    case("a 4-space nest does not DROP the options after it",
         len(decisions(NEST4)[0]["options"]), 2)
    LAZY = "**Decide:** Q\n- merge PR #1\n  because it is green\n- hold it\n"
    case("a lazy continuation joins its option",
         len(decisions(LAZY)[0]["options"]), 2)
    TABBED = "**Decide:** Q\n- merge PR #1\n\t- it is green\n- hold it\n"
    case("a tab-indented continuation does not drop options",
         len(decisions(TABBED)[0]["options"]), 2)
    INLINE_C = "x <!--\n**Decide:** hidden\n- a\n- b\n-->\n"
    case("an INLINE <!-- makes the block inert too", decisions(INLINE_C), [])
    QUOTED_OPTS = "**Decide:** Q\n> - a\n> - b\n"
    case("a blockquoted option list yields no options",
         len(decisions(QUOTED_OPTS)[0]["options"]), 0)
```

- [ ] **Step 2: Run to verify it fails**

```bash
python3 scripts/check-dashboard-entry.py --self-test
```

Expected: FAIL with `NameError: name 'decisions' is not defined`.

- [ ] **Step 3: Implement, reusing the existing scanner**

Add to `scripts/check-dashboard-entry.py`, after `exemption_reason`:

```python
OPENER = "**Decide:**"
OPT = re.compile(r"^\s*[-*+]\s+(?P<text>.*)$")
REC = "[recommended]"


def _inert_lines(text: str) -> set[int]:
    """Indices of lines inside fenced code, indented code, HTML comments or
    blockquotes — the four contexts `exemption_reason` already learned to skip.

    ⚠ Written as ONE scanner shared with the NO-ENTRY reader on purpose. Each of
    those four branches records a MEASURED escape; a second implementation would
    re-earn all four.
    """
    inert, fence, comment = set(), None, False
    for i, line in enumerate(text.split("\n")):
        s = line.strip()
        if comment:
            inert.add(i)
            if "-->" in line:
                comment = False
            continue
        if fence is not None:
            inert.add(i)
            m = FENCE.match(line)
            # CommonMark: a closing fence is at least as long as the opener.
            if m and m.group("ch")[0] == fence[0] and len(m.group("ch")) >= len(fence):
                fence = None
            continue
        m = FENCE.match(line)
        if m:
            fence = m.group("ch")
            inert.add(i)
            continue
        # ⚠ `<!--` ANYWHERE in the line, not just at its start. Round-1 review,
        # execution-verified: `s.startswith("<!--")` diverged from `exemption_reason`,
        # which scans the whole line — so `x <!--` followed by a Decide block parsed as
        # a REAL decision here while the gate reads it as inert. The docstring claimed
        # parity; a near-copy that diverges is worse than an honest second
        # implementation, because the comment stops anyone checking.
        if "<!--" in line:
            inert.add(i)
            if "-->" not in line.split("<!--", 1)[1]:
                comment = True
            continue
        # ⚠ The blockquote half of this branch is currently DEAD and is kept
        # deliberately: `> **Decide:**` is already not an opener, because the caller
        # requires `lstrip().startswith(OPENER)` and `lstrip()` leaves the `>`. Round-1
        # review measured that deleting `s.startswith(">")` left the suite green. The
        # case below therefore tests a blockquoted OPTION LIST under a live opener,
        # which only this branch can catch.
        if s.startswith(">") or _indented(line):
            inert.add(i)
    return inert


def decisions(plain: str) -> list[dict]:
    """Every decision block in an entry's plain prose (spec §4)."""
    lines = plain.split("\n")
    inert = _inert_lines(plain)
    out: list[dict] = []
    i = 0
    while i < len(lines):
        if i in inert or not lines[i].lstrip().startswith(OPENER):
            i += 1
            continue
        question = lines[i].lstrip()[len(OPENER):].strip()
        options: list[dict] = []
        base_indent = None            # column of the FIRST option; deeper = continuation
        j = i + 1
        while j < len(lines):
            line = lines[j]
            if line.strip() == "" or line.lstrip().startswith(OPENER):
                break
            m = OPT.match(line)
            indent = len(line) - len(line.lstrip())
            if m and (base_indent is None or indent <= base_indent):
                if base_indent is None:
                    base_indent = indent
                text = m.group("text").strip()
                rec = text.endswith(REC)
                if rec:
                    text = text[: -len(REC)].strip()
                options.append({"text": text, "recommended": rec})
                j += 1
                continue
            if options and base_indent is not None and indent > base_indent:
                # ⚠ Spec §4 Nesting. Round-1 review, execution-verified: WITHOUT this,
                # a 4-space nested item ENDED the option list, the remaining options
                # VANISHED from the page, and decision_errors then reported
                # "offers 1 option(s)" about an ask that had three. On a feature whose
                # whole purpose is listing the reader's choices, silently dropping
                # choices is the worst failure available.
                extra = m.group("text").strip() if m else line.strip()
                options[-1]["text"] = f'{options[-1]["text"]} {extra}'.strip()
                j += 1
                continue
            break
        out.append({"question": question, "options": options})
        i = j
    return out


def decision_errors(plain: str, category: str) -> list[str]:
    """Why this entry's decision blocks are not usable. Empty list = fine.

    ⚠ The CALLER must not turn these into `entry["error"]` (spec §8b). That
    field feeds `unresolved`'s filter, and an ask filtered out of the tray
    renders as "Nothing needs you." — the defect this whole change closes.
    """
    ds = decisions(plain)
    if category == "heads-up":
        return (["a heads-up asks for nothing, but this one has a **Decide:** block — "
                 "flag it [needs-you] instead"] if ds else [])
    if category != "needs-you":
        return []
    if not ds:
        return ["flagged [needs-you] but names no decision — add a "
                "'**Decide:** <question>' line with at least two options"]
    problems = []
    for d in ds:
        label = d["question"] or "(unnamed)"
        if not d["question"]:
            problems.append("a **Decide:** line with no question after it")
        if len(d["options"]) < 2:
            problems.append(f"decision {label!r} offers "
                            f"{len(d['options'])} option(s); at least two are needed")
        if any(not o["text"] for o in d["options"]):
            problems.append(f"decision {label!r} has an option with no text")
        if sum(1 for o in d["options"] if o["recommended"]) > 1:
            problems.append(f"decision {label!r} marks more than one option "
                            f"[recommended]")
    return problems
```

- [ ] **Step 4: Run to verify it passes**

```bash
python3 scripts/check-dashboard-entry.py --self-test
```

Expected: PASS at 72/72 (49 + 23).

- [ ] **Step 5: Commit**

```bash
git add scripts/check-dashboard-entry.py
git commit -m "feat(dashboard): decision_errors, blind to fenced, quoted, commented and indented Decide lines"
```

---

### Task 4: The tray lists decisions, and a malformed ask gets louder

**Files:**
- Modify: `scripts/gen-dashboard.py` `build` (`:690-716`)
- Test: in-file `_self_test`

**Interfaces:**
- Consumes: `decisions`, `decision_errors` from Task 3 (via `_GATE`, looked up at **call time**); `unresolved`, `cleared_ids` from Task 2.
- Produces: the `What needs you` block's HTML. Task 5 appends its block directly after.

⚠ **Look `decision_errors` up at call time off `_GATE`, exactly as `_exemption_reader` does** (`gen-dashboard.py:318-330`). Binding it at import (`_DE = _GATE.decision_errors`) turns a later rename in the gate into an import-time `AttributeError` and there is no page left to degrade.

- [ ] **Step 1: Write the failing test**

```python
    ASK = ("## 2026-08-28 [needs-you]\nAn ask.\n\n"
           "**Decide:** Merge it\n- merge PR #181 [recommended]\n- hold it\n")
    html = build(parse_entries(ASK), [], [], None, None, 14, [], None,
                 "docs/dashboard-entries.md", None)
    case("the question is in the tray", "Merge it" in html, True)
    case("an option is in the tray", "hold it" in html, True)
    case("recommended is shown", "recommended" in html, True)
    case("options are not folded",
         html.split('<h2>What needs you</h2>')[1].split('<h2>')[0].count("<details"), 0)

    BAD = "## 2026-08-28 [needs-you]\nAn ask with no decision.\n"
    bad_html = build(parse_entries(BAD), [], [], None, None, 14, [], None,
                     "docs/dashboard-entries.md", None)
    case("a malformed ask does NOT read as an all-clear",
         "Nothing needs you." in bad_html, False)
    case("a malformed ask names itself", "2026-08-28/1" in bad_html, True)
    case("a malformed ask says what is missing", "names no decision" in bad_html, True)

    CLEARED = ("## 2026-08-28 [needs-you]\nOld ask, no decision block.\n"
               "## 2026-08-29 [resolved: 2026-08-28/1]\nDone.\n")
    ok_html = build(parse_entries(CLEARED), [], [], None, None, 14, [], None,
                    "docs/dashboard-entries.md", None)
    case("a cleared ask is never validated",
         "Nothing needs you." in ok_html, True)
    case("and it is not marked broken",
         "Could not parse this entry" in ok_html, False)
```

- [ ] **Step 2: Run to verify it fails**

```bash
python3 scripts/gen-dashboard.py --self-test
```

Expected: FAIL — `[FAIL] the question is in the tray` (the tray still renders only titles), and `[FAIL] a malformed ask does NOT read as an all-clear`.

- [ ] **Step 3: Add the call-time reader**

Beside `_exemption_reader` in `scripts/gen-dashboard.py`:

```python
def _decision_reader():
    """`decision_errors`/`decisions` off the already-imported `_GATE`, AT CALL
    TIME — same rule as `_exemption_reader`, same reason: a rename in the gate
    must degrade one section, not kill the page at import.
    """
    return getattr(_GATE, "decisions"), getattr(_GATE, "decision_errors")
```

- [ ] **Step 4: Rebuild the tray**

Replace the `need`/`rows` block at `scripts/gen-dashboard.py:690-694`:

```python
    # ─── What needs you ───
    REC_SPAN = ' <span class="rec">recommended</span>'
    need = unresolved(entries)
    rows, broken = [], []
    try:
        _decisions, _decision_errors = _decision_reader()
    except AttributeError as exc:
        _decisions = _decision_errors = None
        broken.append(f'<li class="unknown">I could not check whether the asks '
                      f'state their choices — {_html.escape(str(exc))}. '
                      f'Treat this as NOT CHECKED.</li>')
    for e in need:
        problems = _decision_errors(e["plain"], "needs-you") if _decision_errors else []
        if problems:
            # NEVER e["error"]: that field feeds `unresolved`'s filter and would
            # DELETE this ask from the tray (spec §7, §8b). Louder, not quieter.
            broken.append(
                f'<li class="unknown">Could not read one ask — '
                f'<a href="#{_slug(e["id"])}">{_html.escape(e["id"])}</a>: '
                f'{_html.escape("; ".join(problems))}</li>')
            continue
        for d in (_decisions(e["plain"]) if _decisions else []):
            # ⚠ Built in a loop, NOT a nested f-string conditional. A backslash
            # inside an f-string expression is a SyntaxError before Python 3.12,
            # and the escaped quotes this markup needs would put one there.
            opt_items = []
            for o in d["options"]:
                rec = REC_SPAN if o["recommended"] else ""
                opt_items.append(f'<li>{_inline(o["text"])}{rec}</li>')
            opts = "".join(opt_items)
            rows.append(
                f'<li><span class="q">{_inline(d["question"])}</span> '
                f'<span class="when">{_html.escape(e["date"])} · '
                f'<a href="#{_slug(e["id"])}">{_html.escape(e["id"])}</a></span>'
                f'<ul class="opts">{opts}</ul></li>')
    rows += broken
```

Then extend the empty-state condition at `:711-716` so it cannot fire over a broken ask:

```python
    if rows:
        needs_html = '<ul class="needs">' + "".join(rows) + "</ul>" + store_note + pr_note
    elif store_error or pr_error:
        needs_html = store_note + pr_note
    else:
        needs_html = '<p class="none">Nothing needs you.</p>'
```

(`rows` already contains `broken`, so the third branch is unreachable while any ask is malformed.)

- [ ] **Step 5: Add the option styles**

```css
.needs .q{font-weight:600}
.needs .opts{margin:.35rem 0 .6rem 1.1rem;padding:0}
.needs .opts li{margin:.15rem 0}
.needs .rec{font-size:.78em;opacity:.75;border:1px solid currentColor;border-radius:3px;padding:0 .3em}
```

- [ ] **Step 6: Run to verify it passes**

```bash
python3 scripts/gen-dashboard.py --self-test
```

Expected: PASS at 237/237.

- [ ] **Step 6b: Repair the SUITE's own fixture — it is not resolved**

⚠ **Round-1 review, execution-verified: applying Tasks 1–6 takes the suite 217 → 216 before a single
new case is added.** `gen-dashboard.py:1246` builds

```python
ents3 = parse_entries("## 2026-08-28 [needs-you]\nDecide the thing.\n<!--tech-->\nPR #1.\n")
```

— an **unresolved** `[needs-you]` with no `**Decide:**` block. Under this task's tray it becomes a
`broken` row, its title leaves the What-needs-you section, and the case at `:1310-1312` — which
exists precisely to assert on that section — goes red:

```
[FAIL] a gh failure still shows the store's needs IN THAT SECTION
```

**This is spec §11's hazard displaced.** The plan verified the real *store*, where all three asks are
resolved, and never the *suite's fixtures*, where this one is not.

**Fix:** give `ents3` a decision block, keeping its existing title so the assertion still matches:

```python
    ents3 = parse_entries("## 2026-08-28 [needs-you]\nDecide the thing.\n\n"
                          "**Decide:** Decide the thing\n- do it\n- do not\n"
                          "<!--tech-->\nPR #1.\n")
```

⚠ `ents3` is reused by later cases — after editing it, run the whole suite, not just the case above.

- [ ] **Step 7: Prove the real store is untouched**

```bash
python3 scripts/gen-dashboard.py
grep -c "Could not parse this entry" ~/explainers/dashboard.html || true
grep -c "Could not read one ask" ~/explainers/dashboard.html || true
```

Expected: `0` and `0` — all three historical asks are resolved, so none is validated (spec §11).

- [ ] **Step 8: Commit**

```bash
git add scripts/gen-dashboard.py
git commit -m "feat(dashboard): the tray lists decisions and options, and a malformed ask cannot read as an all-clear"
```

---

### Task 5: The "Worth knowing" block, and an honest glossary

**Files:**
- Modify: `scripts/gen-dashboard.py` `build`, `GLOSSARY` (`:676-681`), the page template (`:906`)
- Test: in-file `_self_test`

**Interfaces:**
- Consumes: `unresolved_heads_up`, `cleared_ids` (Task 2); `decision_errors` (Task 3).
- Produces: `worth_html`, inserted directly after `needs_html` in the page body.

- [ ] **Step 1: Write the failing test**

```python
    HU = ("## 2026-08-28 [heads-up]\nCI now checks the plan against the code.\n\n"
          "It will turn red until the plan is edited to match.\n")
    hu_html = build(parse_entries(HU), [], [], None, None, 14, [], None,
                    "docs/dashboard-entries.md", None)
    case("worth-knowing heading appears", "<h2>Worth knowing</h2>" in hu_html, True)
    case("its first paragraph is on the page",
         "CI now checks the plan against the code." in hu_html, True)
    case("it is NOT inside the fold",
         hu_html.split("<h2>Worth knowing</h2>")[1].split("<h2>")[0].count("<details"), 0)
    case("a heads-up does not appear under needs-you",
         "CI now checks" in hu_html.split("<h2>What needs you</h2>")[1]
         .split("<h2>")[0], False)

    none_html = build(parse_entries("## 2026-08-28\nOrdinary.\n"), [], [], None, None,
                      14, [], None, "docs/dashboard-entries.md", None)
    case("no heads-ups means no heading", "Worth knowing" in none_html, False)

    err_html = build([], [], [], None, None, 14, [], None,
                     "docs/dashboard-entries.md", "boom")
    case("an unreadable store still shows the heading",
         "<h2>Worth knowing</h2>" in err_html, True)
    case("and says it was not checked",
         "NOT CHECKED" in err_html.split("<h2>Worth knowing</h2>")[1], True)

    case("glossary gloss is trimmed",
         any(g[0] == "needs you" and "nothing else on the page" not in g[1]
             for g in GLOSSARY), True)
    case("glossary defines heads-up",
         any(g[0] == "heads-up" for g in GLOSSARY), True)
```

- [ ] **Step 2: Run to verify it fails**

```bash
python3 scripts/gen-dashboard.py --self-test
```

Expected: FAIL — `[FAIL] worth-knowing heading appears`.

- [ ] **Step 3: Build the block**

In `build`, after `needs_html` is assigned:

```python
    # ─── Worth knowing ───
    # ⚠ The omit-when-empty rule applies ONLY when the store was READ. Zero
    # parsed heads-ups from an unreadable store would omit the heading, and a
    # missing heading reads as "nothing worth knowing" — absence and denial
    # looking alike, which is the confusion this page exists to prevent.
    hu_rows = []
    for e in unresolved_heads_up(entries):
        # ⚠ Round-1 review, BOTH halves: v1 declared a dependency on `decision_errors`
        # here and then never called it, so a [heads-up] carrying a live **Decide:**
        # block rendered as valid. Spec §4 makes that malformed; without this call
        # §4's "a heads-up cannot ask" has NO enforcement point anywhere in the slice.
        hu_problems = _decision_errors(e["plain"], "heads-up") if _decision_errors else []
        if hu_problems:
            hu_rows.append(
                f'<li class="unknown">Could not read one heads-up — '
                f'<a href="#{_slug(e["id"])}">{_html.escape(e["id"])}</a>: '
                f'{_html.escape("; ".join(hu_problems))}</li>')
            continue
        first = e["plain"].split("\n\n")[0].strip()
        hu_rows.append(
            f'<li><a href="#{_slug(e["id"])}">{_html.escape(e["id"])}</a> '
            f'<span class="when">{_html.escape(e["date"])}</span>'
            f'<div class="prose">{_prose(first, drop_headline=False)}</div></li>')
    if hu_rows:
        worth_html = ('<h2>Worth knowing</h2><ul class="worth">'
                      + "".join(hu_rows) + "</ul>" + store_note)
    elif store_error:
        worth_html = "<h2>Worth knowing</h2>" + store_note
    else:
        worth_html = ""
```

- [ ] **Step 4: Place it on the page**

`scripts/gen-dashboard.py:906` — insert immediately after the needs block:

```python
<h2>What needs you</h2>{needs_html}
{worth_html}
<h2>The last 14 days</h2>...
```

(keep the existing surrounding template text exactly; only the `{worth_html}` line is new)

- [ ] **Step 5: Correct the glossary**

`scripts/gen-dashboard.py:676-681`:

```python
GLOSSARY = [
    # ⚠ The second clause — "nothing else on the page is asking for anything" —
    # was already untrue of the open-PR rows in the same tray, and a
    # "Worth knowing" block makes it plainly false. Trimmed to the true part.
    ("needs you", "a decision is waiting on you, and the page lists your choices"),
    ("heads-up", "worth knowing, but nothing is being asked of you"),
    ("resolved", "this was an ask or a heads-up, and a later entry closed it"),
    ("entry", "one dated block you or the assistant wrote, in plain words, about what changed"),
    ("no entry recorded", "a branch was merged with its entry deliberately skipped, and said why"),
    ("shipped with no entry", "a day with commits and nothing written about them — the gap the entry rule exists to close"),
]
```

- [ ] **Step 6: Run to verify it passes**

```bash
python3 scripts/gen-dashboard.py --self-test && python3 scripts/gen-dashboard.py
```

Expected: PASS at 247/247, and the page writes.

- [ ] **Step 7: Commit**

```bash
git add scripts/gen-dashboard.py
git commit -m "feat(dashboard): a Worth knowing block, and a glossary that stops overclaiming"
```

---

### Task 6: Live PR state, bounded and honest about exhaustion

**Files:**
- Modify: `scripts/gen-dashboard.py` (new resolver + the tray's option rendering from Task 4)
- Test: in-file `_self_test`

**Interfaces:**
- Consumes: `_gh_json` (`:490`), the option dicts from Task 3.
- Produces: `PR_TOKEN` (compiled regex), `pr_state(n, cache, budget) -> str` returning one of `open`, `merged`, `closed`, `missing`, `unknown`, `exhausted`.

- [ ] **Step 1: Write the failing test**

```python
    case("PR token matches the literal form",
         [m.group(1) for m in PR_TOKEN.finditer("merge PR #181 now")], ["181"])
    case("a bare number is NOT a PR",
         PR_TOKEN.findall("close backlog #74"), [])
    case("a lone hash is NOT a PR", PR_TOKEN.findall("issue #12"), [])

    _R = type("R", (), {})
    def _mk(rc, out):
        r = _R(); r.returncode, r.stdout, r.stderr = rc, out, ""
        return r
    b = {"calls": 0, "seconds": 0.0}
    cache = {}
    case("an open PR reads open",
         _with_run(lambda *a, **k: _mk(0, '{"number":1,"state":"OPEN"}'),
                   lambda: pr_state(1, cache, b)), "open")
    case("a merged PR reads merged",
         _with_run(lambda *a, **k: _mk(0, '{"number":2,"state":"MERGED"}'),
                   lambda: pr_state(2, cache, b)), "merged")
    # ⚠ The stub must carry gh's REAL stderr. Round-1 review: a bare returncode=1 with
    # empty stderr yields err="gh exited 1: ", which matches nothing and returns
    # "unknown" — the case could never have gone green.
    def _mk_err(msg):
        r = _R(); r.returncode, r.stdout, r.stderr = 1, "", msg
        return r
    case("a missing PR reads missing",
         _with_run(lambda *a, **k: _mk_err(
             "GraphQL: Could not resolve to a PullRequest with the number of 3."),
             lambda: pr_state(3, cache, b)), "missing")
    case("a transport failure reads unknown, NOT missing",
         _with_run(lambda *a, **k: _mk_err("dial tcp: lookup api.github.com: no such host"),
                   lambda: pr_state(31, {}, {"calls": 0, "seconds": 0.0})), "unknown")
    case("a bad shape reads unknown",
         _with_run(lambda *a, **k: _mk(0, '{"number":4}'),
                   lambda: pr_state(4, cache, b)), "unknown")
    case("a cached PR costs no call",
         (pr_state(1, cache, b), b["calls"]), ("open", 4))
    spent = {"calls": 10, "seconds": 0.0}
    case("an exhausted budget reads exhausted",
         pr_state(99, {}, spent), "exhausted")
    over = {"calls": 0, "seconds": 61.0}
    case("an exhausted clock reads exhausted", pr_state(98, {}, over), "exhausted")
```

- [ ] **Step 2: Run to verify it fails**

```bash
python3 scripts/gen-dashboard.py --self-test
```

Expected: FAIL with `NameError: name 'PR_TOKEN' is not defined`.

- [ ] **Step 3: Implement the resolver**

```python
# ⚠ The LITERAL token, never a bare `#N`. This repo writes `#N` for backlog rows
# constantly — "backlog #74", "#76/#77" — and a bare rule would resolve pull
# request 74 and render a confident, wrong link (spec §4).
PR_TOKEN = re.compile(r"\bPR #(\d+)\b")

PR_MAX_CALLS = 10
PR_MAX_SECONDS = 60.0


def pr_state(n: int, cache: dict, budget: dict) -> str:
    """Live state of pull request `n`, bounded (spec §6).

    ⚠ `_gh_json` times out PER CALL (`:495`), so ten PRs is ten timeouts. The
    budget bounds the RENDER, and exhaustion is its OWN answer — a partial
    render that looked "checked" would be the absence/denial confusion again.
    """
    if n in cache:
        return cache[n]
    if budget["calls"] >= PR_MAX_CALLS or budget["seconds"] >= PR_MAX_SECONDS:
        return "exhausted"
    t0 = _time.monotonic()
    data, err = _gh_json(["pr", "view", str(n), "--json", "number,state"])
    budget["calls"] += 1
    budget["seconds"] += _time.monotonic() - t0
    if err is not None:
        # ⚠ Round-1 review, execution-verified by BOTH halves. v1 matched "not found"
        # and "no pull requests"; the real tool says
        #   GraphQL: Could not resolve to a PullRequest with the number of 999999.
        # so neither substring matched and the "missing" branch was unreachable — the
        # test could not have gone green, and the real path was broken too.
        low = err.lower()
        state = ("missing"
                 if "could not resolve to a pullrequest" in low or "no pull requests found" in low
                 else "unknown")
    elif not isinstance(data, dict) or not isinstance(data.get("state"), str):
        state = "unknown"          # shape is validated; _gh_json only parses
    else:
        state = {"OPEN": "open", "MERGED": "merged",
                 "CLOSED": "closed"}.get(data["state"].upper(), "unknown")
    cache[n] = state
    return state
```

Add `import time as _time` beside the existing imports.

- [ ] **Step 4: Resolve the repo slug once, and degrade to unlinked**

Add beside `pr_state`:

```python
PR_NOTE = {
    "open": "",
    "merged": ' <span class="stale">stale — already merged</span>',
    "closed": ' <span class="stale">stale — already closed</span>',
    "missing": ' <span class="stale">no such pull request</span>',
    "unknown": ' <span class="unknown">could not check</span>',
    "exhausted": ' <span class="unknown">could not check — '
                 'PR lookup budget exhausted</span>',
}


def repo_slug() -> str | None:
    """`owner/name` for building PR links, or None.

    None means the option renders as PLAIN TEXT with its state note — never a
    guessed URL. A wrong link is worse than no link on a page whose job is to
    send the reader somewhere real.
    """
    data, err = _gh_json(["repo", "view", "--json", "nameWithOwner"])
    if err is not None or not isinstance(data, dict):
        return None
    slug = data.get("nameWithOwner")
    return slug if isinstance(slug, str) and "/" in slug else None
```

- [ ] **Step 5: Render the state on each option**

Replace Task 4's `opt_items` loop body with the complete version:

```python
            opt_items = []
            for o in d["options"]:
                rec = REC_SPAN if o["recommended"] else ""
                m = PR_TOKEN.search(o["text"])
                if not m:
                    opt_items.append(f'<li>{_inline(o["text"])}{rec}</li>')
                    continue
                n = int(m.group(1))
                note = PR_NOTE[pr_state(n, _pr_cache, _pr_budget)]
                if _repo:
                    body = (f'<a href="https://github.com/{_html.escape(_repo)}'
                            f'/pull/{n}">{_inline(o["text"])}</a>')
                else:
                    body = _inline(o["text"])
                opt_items.append(f'<li>{body}{rec}{note}</li>')
            opts = "".join(opt_items)
```

And create the three per-render values **once**, immediately after `REC_SPAN` in `build`:

```python
    _pr_cache: dict[int, str] = {}
    _pr_budget = {"calls": 0, "seconds": 0.0}
    _repo_box: list = []          # lazily filled: [] = not looked up yet
```

and resolve the slug **only on the first `PR #N` match**, via:

```python
def _repo_once(box: list):
    """⚠ Round-1 review, both halves. `_repo = repo_slug()` at the top of `build`
    made EVERY render a network call — including renders with no PR options, and
    including CI, which runs `--self-test` and then builds. It also sat outside the
    10-call/60s budget, so the "bounded render" guarantee was false.
    """
    if not box:
        box.append(repo_slug())
    return box[0]
```

with the option loop calling `_repo_once(_repo_box)` instead of reading `_repo`.

- [ ] **Step 6: Add the stale style**

```css
.needs .stale{font-size:.78em;opacity:.8;font-style:italic}
```

- [ ] **Step 7: Run to verify it passes**

```bash
python3 scripts/gen-dashboard.py --self-test
```

Expected: PASS at 259/259.

- [ ] **Step 8: Commit**

```bash
git add scripts/gen-dashboard.py
git commit -m "feat(dashboard): resolve PR #N to live state, bounded, with exhaustion as its own message"
```

---

### Task 7: Mutation coverage — prove every new guard is load-bearing

**Files:**
- Modify: `scripts/mutations/gen-dashboard.json`, `scripts/mutations/check-dashboard-entry.json`
- Modify: `scripts/check-plan-code.py:443,:445` (`EXPECTED_MUTATIONS`)

**Interfaces:**
- Consumes: every guard added in Tasks 1–6.
- Produces: nothing downstream. This is the task that proves the others.

⚠ **Take `expect` FROM THE RUN, never from prediction.** The harness has refused predicted case names four times on record. Run the suite, copy the exact failing case name.

- [ ] **Step 1: Add mutations for the load-bearing decisions**

Append to `scripts/mutations/check-dashboard-entry.json` (each entry `{"name", "file", "edits": [[find, replace]], "expect": [case names]}`):

```json
{
  "name": "decision_errors stops requiring two options",
  "file": "scripts/check-dashboard-entry.py",
  "edits": [["if len(d[\"options\"]) < 2:", "if len(d[\"options\"]) < 1:"]],
  "expect": ["one option fails"]
},
{
  "name": "the inert-line scanner is switched off",
  "file": "scripts/check-dashboard-entry.py",
  "edits": [["inert = _inert_lines(plain)", "inert = set()"]],
  "expect": ["a fenced Decide is not a decision"]
},
{
  "name": "a heads-up may carry a decision",
  "file": "scripts/check-dashboard-entry.py",
  "edits": [["if category == \"heads-up\":", "if False:"]],
  "expect": ["a heads-up that asks fails"]
},
{
  "name": "two recommendations are tolerated",
  "file": "scripts/check-dashboard-entry.py",
  "edits": [["if sum(1 for o in d[\"options\"] if o[\"recommended\"]) > 1:",
             "if sum(1 for o in d[\"options\"] if o[\"recommended\"]) > 2:"]],
  "expect": ["two recommendations fail"]
}
```

Append to `scripts/mutations/gen-dashboard.json`:

```json
{
  "name": "the badge reverts to the authored flag",
  "file": "scripts/gen-dashboard.py",
  "edits": [["if entry[\"id\"] in cleared:", "if False:"]],
  "expect": ["resolved ask badges as resolved"]
},
{
  "name": "a malformed ask is filtered out of the tray",
  "file": "scripts/gen-dashboard.py",
  "edits": [["rows += broken", "pass"]],
  "expect": ["a malformed ask does NOT read as an all-clear"]
},
{
  "name": "resolved entries are validated after all",
  "file": "scripts/gen-dashboard.py",
  "edits": [["for e in need:", "for e in entries:"]],
  "expect": ["a cleared ask is never validated"]
},
{
  "name": "the worth-knowing heading is omitted on an unreadable store",
  "file": "scripts/gen-dashboard.py",
  "edits": [["elif store_error:\n        worth_html = \"<h2>Worth knowing</h2>\" + store_note",
             "elif False:\n        worth_html = \"\""]],
  "expect": ["an unreadable store still shows the heading"]
},
{
  "name": "a bare #N is treated as a pull request",
  "file": "scripts/gen-dashboard.py",
  "edits": [["PR_TOKEN = re.compile(r\"\\bPR #(\\d+)\\b\")",
             "PR_TOKEN = re.compile(r\"#(\\d+)\")"]],
  "expect": ["a bare number is NOT a PR"]
},
{
  "name": "the PR budget stops bounding the render",
  "file": "scripts/gen-dashboard.py",
  "edits": [["if budget[\"calls\"] >= PR_MAX_CALLS or budget[\"seconds\"] >= PR_MAX_SECONDS:",
             "if False:"]],
  "expect": ["an exhausted budget reads exhausted"]
},
{
  "name": "gh output shape is no longer validated",
  "file": "scripts/gen-dashboard.py",
  "edits": [["elif not isinstance(data, dict) or not isinstance(data.get(\"state\"), str):",
             "elif not isinstance(data, dict):"]],
  "expect": ["a bad shape reads unknown"]
},
{
  "name": "unresolved_heads_up ignores the cleared set",
  "file": "scripts/gen-dashboard.py",
  "edits": [["if e[\"heads_up\"] and not e[\"error\"] and e[\"id\"] not in cleared]",
             "if e[\"heads_up\"] and not e[\"error\"]]"]],
  "expect": ["a cleared heads-up leaves the Worth knowing block"]
},
{
  "name": "a heads-up may carry a decision after all (renderer side)",
  "file": "scripts/gen-dashboard.py",
  "edits": [["hu_problems = _decision_errors(e[\"plain\"], \"heads-up\") if _decision_errors else []",
             "hu_problems = []"]],
  "expect": ["a heads-up carrying a Decide block is called out"]
}
```

- [ ] **Step 2: Run the mutation harness and take the real case names**

```bash
python3 scripts/check-plan-code.py --mutate .
```

Expected: it reports either `0 survivors` or, for any entry whose `expect` name does not match, `anchor NOT FOUND` / a name mismatch. **Correct the `expect` entries to the names the run prints. Do not adjust the guard to match a predicted name.**

- [ ] **Step 3: Raise the pin**

`scripts/check-plan-code.py:443,:445` — set each to the count the run reports:

```python
    "scripts/gen-dashboard.py": 54,          # 47 + 7
    "scripts/check-dashboard-entry.py": 16,  # 12 + 4
```

⚠ If the run's real counts differ, use the run's numbers. The comment is the arithmetic, not the authority.

- [ ] **Step 4: Verify no survivors and no shrink**

```bash
python3 scripts/check-plan-code.py --mutate .
python3 scripts/check-ratchet-contract.py
python3 scripts/check-guard-coverage.py
```

Expected: `0 survivors` with clean controls; `ratchet contract OK`; guard coverage OK.

- [ ] **Step 5: Full green sweep**

```bash
python3 scripts/gen-dashboard.py --self-test
python3 scripts/check-dashboard-entry.py --self-test
python3 scripts/check-docs.py
python3 scripts/check-anchors.py
python3 scripts/gen-dashboard.py
```

Expected: all pass; the page writes.

- [ ] **Step 6: Commit**

```bash
git add scripts/mutations/ scripts/check-plan-code.py
git commit -m "test(dashboard): mutation coverage for the ask-choices guards"
```

---

## Task ordering and why

| Task | Depends on | Independently valuable? |
|---|---|---|
| 1 — `heads-up` flag | — | Yes: the grammar accepts the category |
| 2 — derived badges | 1 (`heads_up` key) | **Yes — this alone fixes the defect the user reported** |
| 3 — `decision_errors` | — (pure, in the gate) | Yes: the validator, self-tested |
| 4 — tray decisions | 2, 3 | Yes: asks state their choices |
| 5 — Worth knowing | 1, 2 | Yes: heads-ups become visible |
| 6 — PR state | 3, 4 | Yes: options link and show staleness |
| 7 — mutations | all | Proves the rest |

**Task 2 is the one to ship first if the branch is ever cut short** — it is the visible contradiction the user reported, and it depends on nothing but Task 1's dict key.

## Verification against the spec

| Spec section | Task |
|---|---|
| §3 two categories | 1, 5 |
| §4 grammar, inert contexts, `PR #N` | 1, 3, 6 |
| §5a tray, unfolded, card asymmetry | 4 |
| §5b Worth knowing, unfolded, NOT CHECKED | 5 |
| §5c derived badges | 2 |
| §5d glossary | 5 |
| §6 PR state, budget, exhaustion | 6 |
| §7 cannot-run rows | 4, 5, 6 |
| §8a validator placement, call-time lookup | 3, 4 |
| §8b runs after `unresolved`, never sets `error` | 4 |
| §9 falsifiers | every task's tests; 7 proves them load-bearing |
| §11 no cutover, historical entries intact | 4 (Step 7) |

**Not covered by any task, and stated rather than hidden:** §10's limits (option wording is not validated beyond structure; the gate defends shape, not quality) are non-goals, and §2's out-of-scope gate half is backlog #78.

---

## Round 1 review — fold record

Both halves NOT CONVERGED. Reviews at `docs/reviews/plan-dashboard-ask-choices-r1-{codex,claude}.md`.
Codex `gpt-5.5`: 2 Blocking, 2 High, 2 Medium, 2 Low. Claude: 4 Blocking, 6 High, 6 Medium, 7 Low.
**Most findings were verified by EXECUTION, which is what this gate was for** — the two spec rounds
could only read.

| Finding | Sev | Fixed in |
|---|---|---|
| **Nested options are counted as peers; a 4-space nest silently DROPS every later option** and `decision_errors` then reports "offers 1 option(s)" about an ask that had three | Blocking | T3 — indent tracking + 4 fixtures |
| **The suite goes 217 → 216 before any new case**: `ents3` (`:1246`) is an unresolved `[needs-you]` with no decision block | Blocking | T4 Step 6b |
| **The `missing` PR case can never go green** — real `gh` says *"Could not resolve to a PullRequest"*, matching neither substring | Blocking ×2 | T6 — real stderr in both the branch and the stub, plus a transport-failure case |
| **`decision_errors` is never called for a `heads-up`**, so §4's "a heads-up cannot ask" had no enforcement point at all | Blocking ×2 | T5 |
| **Gate and renderer made to disagree** — `header_error` strips both flags, so the gate accepts what the renderer marks malformed (a sixth divergence in a function whose docstring records five) | High | T1 Step 4b — refusal moves into `header_error` |
| `_inert_lines` diverges from `exemption_reason` on an INLINE `<!--` | High ×2 | T3 |
| `build()` becomes a network call on every render, including CI, outside the budget | High ×2 | T6 — `_repo_once`, lazy |
| The blockquote branch is DEAD; its case passes for another reason | Medium | T3 — comment + a fixture only that branch can satisfy |
| `unresolved_heads_up` ignoring `cleared` survives mutation | Medium | T7 mutation + T5 case |
| Predicted case tallies are wrong at T3, T5, T6 | Medium | Global Constraints — take the number from the run |
| Four "failing tests" already pass before their implementation | Low | Global Constraints — regression guards, not red-phase evidence |
| The `gh output shape` mutation crashes the suite instead of reddening its case | Blocking | T7 — weakened to `not isinstance(data, dict)` |
| A `python`-fenced block that is HTML | Low | Fence corrected |

**Verified by execution after folding** (`scratchpad/probe2.py`, against the real `FENCE` and
`_indented`): all 15 fixtures pass, including every one of the six shapes round 1 broke — 2-space
nest, 4-space nest, lazy continuation, tab continuation, inline `<!--`, blockquoted option list.

**Not folded, dispositioned instead:** whole-page render assertions (Claude H3) — the tray/worth
sections are asserted by substring within their own `<h2>` slice in T4/T5, which is the same
technique the existing suite uses at `:1310`; tightening every render assertion is its own slice.
