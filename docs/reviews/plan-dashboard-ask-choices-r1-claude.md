# Adversarial plan review — dashboard ask-choices, round 1 (Claude half)

**Subject:** `docs/superpowers/plans/2026-08-31-dashboard-ask-choices.md` (commit `7417264`, branch
`feat/dashboard-ask-choices`), against spec v3 (`77f63f3`).

**Method — this review was EXECUTED, not read.** Working copy at
`…/scratchpad/plan-review/repo` (a `shutil.copytree` of `scripts/` plus the real store; **nothing in
the repo was modified**). Every Python and JSON block in the plan was extracted and parsed; Tasks
1–6 were applied verbatim to the copy by `apply.py` (every anchor asserted to occur exactly once);
the plan's own test blocks were appended verbatim by `add_cases.py`; both suites were run; `gh` was
counted with a PATH shim; and fifteen hand-written mutations were applied to the code the plan
produces to look for survivors.

**Headline measurements, before any argument:**

| Plan says | Measured |
|---|---|
| `check-dashboard-entry.py --self-test` → **72/72** after Task 3 | **70/70** |
| `gen-dashboard.py --self-test` → **259/259** after Task 6 | **254/256** — two RED |
| Task 2 Step 7 "before" → `3 / 0 / True` | **`0 / 0 / True`** |
| the suite is pure | **31 real `gh` subprocesses per run**, incl. a live `gh pr view 181` |
| Task 7 → `0 survivors` | one mutation cannot produce its named red case at all; **9 further one-line deletions in the plan's own new code survive the plan's own suite** |

---

## Blocking

### B1 · Task 6, Steps 1 + 3 — the `missing` case cannot pass against the `missing` branch
**VERIFIED BY EXECUTION** (`t6_cases.py`, then the full applied suite).

The stub is `_mk(1, "")` — `returncode=1`, **`stderr=""`**. `_gh_json` (`gen-dashboard.py:498-499`)
therefore returns `(None, "gh exited 1: ")`. `pr_state`'s branch tests
`"not found" in err.lower() or "no pull requests" in err.lower()` — neither substring is present, so
it returns `"unknown"`.

```
[FAIL] a missing PR reads missing
    got:  'unknown'
    want: 'missing'
```

**Why it matters.** Task 6 Step 7 states `PASS at 259/259`; it cannot be reached. Worse, the
`missing` branch — the one the brief singles out as string-matching an error message that can change
— ends up with **no passing coverage in either direction**, and the implementer's obvious repair
(loosen the branch, or edit the stub to inject `stderr`) is a decision the plan does not make for
them. `_gh_json` also *truncates* stderr to 200 chars (`:499`), so the substring test is being run
against a prefix, not the message.

**Suggested fix:** make the stub `_mk(1, "", err="GraphQL: Could not resolve to a PullRequest…")`
and add a paired negative (`_mk(1, "", err="dial tcp: i/o timeout")` → `"unknown"`), so both sides
of the string match are asserted.

---

### B2 · Task 4, Step 4 — it breaks a pre-existing case, and Step 6's stated tally is unreachable
**VERIFIED BY EXECUTION** — applying Tasks 1–6 alone (before adding any new case) takes the suite
from **217/217 to 216/217**.

```
[FAIL] a gh failure still shows the store's needs IN THAT SECTION
    got:  False   want: True
```

`gen-dashboard.py:1246` builds the fixture
`ents3 = parse_entries("## 2026-08-28 [needs-you]\nDecide the thing.\n<!--tech-->\nPR #1.\n")` — an
**unresolved** `[needs-you]` entry with **no `**Decide:**` block**. Under Task 4's tray it becomes a
`broken` row, so its title leaves the What-needs-you section, and the case at `:1310-1312` — which
exists *specifically* to assert on that section rather than the whole page — goes red.

**Why it matters.** Task 4 Step 6 says `Expected: PASS at 237/237`. The real result is 236/237. An
implementer who sees only Task 4 meets a red case in an unrelated part of the file with no
instruction. Structurally this is the §11 hazard the spec spent a round on, displaced: the plan
verified the real **store** (where all three asks are resolved) and never the **suite's fixtures**
(where they are not). `ents3` is reused by several later cases, so any repair has blast radius.

**Suggested fix:** name this in Task 4 — give `ents3` a decision block, or add a second fixture —
and correct Step 6's expected tally.

---

### B3 · Task 7, Step 1 — the `gh output shape` mutation crashes the suite instead of reddening its case
**VERIFIED BY EXECUTION.**

The mutation turns `elif not isinstance(data, dict) or not isinstance(data.get("state"), str):` into
`elif False:`. Control flow then reaches `data["state"].upper()` with `data == {"number": 4}`:

```
RAISED KeyError: 'state'  -> the suite CRASHES, so no
'[FAIL] a bad shape reads unknown' line is ever printed
```

`check-plan-code.py:679` sets `caught = rc == 1` (an uncaught exception exits 1, so `caught` is
True), but `fails` is **empty** — the print never happens. `:711-712` then finds
`len(matches) != 1` and `:719-726` reports
*"`expect` 'a bad shape reads unknown' matched 0 red case(s) — it was caught by something else"*.

**Why it matters.** Task 7 Step 2 instructs *"correct the `expect` entries to the names the run
prints."* **The run prints no name.** Step 4's `0 survivors` is unreachable without redesigning the
mutation, and this is precisely the *"a report format is a CONTRACT"* class — a failure shape the
harness cannot parse.

**Suggested fix:** mutate only the first conjunct (`elif not isinstance(data, dict):`), which leaves
`data.get("state")` reachable and still reddens the named case.

---

### B4 · Task 3, Step 3 — spec §4's **Nesting** rule is not implemented, and its absence drops options silently
**VERIFIED BY EXECUTION** (`t3_probe.py`, section A).

Spec §4: *"**Nesting** — a list item indented more than the first option is a **continuation of it**,
not a new option."* `decisions()` implements nothing for this, and `OPT = ^\s*[-*+]\s+` swallows any
indent. Measured against the plan's own implementation:

| Author writes | Result |
|---|---|
| `- merge PR #1` / `  - it is green` / `- hold it` (2-space nest) | **3 options** — the sub-bullet is counted as a peer |
| `- merge PR #1` / `    - it is green` / `- hold it` (4-space nest) | **1 option**; `- hold it` **silently vanishes**; `decision_errors` → *"offers 1 option(s); at least two are needed"* |
| `- merge PR #1` / `  because it is green` (lazy continuation) | **1 option**; same false error |
| tab-indented continuation | **1 option**; same false error |

The 4-space and tab cases are the `_inert_lines` indented-code branch firing inside an option list:
the inner loop's `j not in inert` terminates it, and the outer loop then skips past every remaining
option.

**Why it matters.** A correctly-authored ask renders as *"Could not read one ask — …"* while its
real options disappear from the page. On a slice whose entire purpose is *"the page lists your
choices"*, silently dropping choices is the worst available failure. No task tests any of these
shapes.

**Suggested fix:** record the first option's indent column and fold deeper items into the previous
option's text; add the four fixtures above as cases.

---

## High

### H1 · Task 6, Step 5 — `build()` becomes a network call, and CI runs it
**VERIFIED BY EXECUTION** — PATH shim logging every `gh` invocation.

`_repo = repo_slug()` is created *inside* `build`, unconditionally, on **every** call. Measured on
the applied copy:

```
one `gen-dashboard.py --self-test` run:  30 × `gh repo view --json nameWithOwner`
                                          1 × `gh pr view 181 --json number,state`
runtime: 0.209s (HEAD)  ->  1.814s (Tasks 1-6, warm + authenticated)
```

The live `pr view 181` comes from Task 4's own `ASK` fixture (`merge PR #181`). `.github/workflows/ci.yml:212-213`
runs this step. `_gh_json` bounds each call at `timeout=30`, so a hung `gh` gives a worst case of
~15 minutes in one CI step with no message.

This also inverts the file's established seam: `build` already receives `prs` and `pr_error` as
**parameters** precisely because `main` does the collecting (`:2400-2406`). Task 6 puts two
collectors back inside the renderer.

**Why it matters.** A pure 0.2s unit suite becomes an authenticated network client. Under a
redirected `HOME` (the mutation harness) `gh` is unauthenticated, so the suite silently exercises a
*different* code path from the one a developer runs — the two are no longer the same test.

**Suggested fix:** resolve `repo_slug()` and the PR states in `main` and pass them into `build`, like
`prs`/`pr_error`; stub `gh` in every test that renders an option carrying `PR #N`.

---

### H2 · Task 5 — nothing ever validates a `heads-up`, so §4's *"a heads-up cannot ask"* has no enforcement point
Task 5's **Interfaces** block declares *"Consumes: … `decision_errors` (Task 3)"*. Step 3's code
never calls it:

```python
    hu_rows = []
    for e in unresolved_heads_up(entries):
        first = e["plain"].split("\n\n")[0].strip()
        hu_rows.append(…)
```

`decision_errors(plain, "heads-up")` therefore has an implementation (Task 3), a unit test (Task 3),
a mutation (Task 7) — and **no caller on the page**. Spec §4 (*"In a `heads-up` — a recognised
`**Decide:**` is malformed"*), §7's row table and §9's *"Heads-up cannot ask"* falsifier are all
satisfied only at the function level. The plan's coverage table nonetheless maps *"§7 cannot-run
rows"* to Tasks 4, **5**, 6.

**Suggested fix:** give Task 5 the same `broken`/`_decision_reader` treatment as Task 4, and a case
asserting a `[heads-up]` carrying a `**Decide:**` renders a "could not read" row.

---

### H3 · Tasks 4 and 5 — the render assertions are whole-page, so five render behaviours survive deletion
**VERIFIED BY EXECUTION** — mutations applied to the code the plan produces, against the plan's own
appended suite:

```
SURVIVED  the option-list rendering is deleted        (opts = "")
SURVIVED  PR_NOTE loses every note                    (stale is no longer marked)
SURVIVED  the PR link is dropped entirely
SURVIVED  repo_slug returns a GUESSED slug instead of None on failure
SURVIVED  the heads-up row's prose is dropped
```

The cause is that `case("an option is in the tray", "hold it" in html, True)`,
`case("the question is in the tray", "Merge it" in html, True)` and
`case("its first paragraph is on the page", "CI now checks…" in hu_html, True)` search the **whole
page** — and the same text is also rendered by the entry card's prose fold. This is verbatim the
defect the file already records at `:1307-1309`:

> *"H5's real assertion: the store's needs survive a gh failure IN THEIR OWN SECTION. Asserting
> against the whole page passed on the title's copy in 'What changed' — i.e. on exactly the defect
> it names."*

Consequently spec §9's *"Stale PR is marked"*, *"`gh` failure is loud"* (at render level) and
*"Heads-up explains on sight"* (which explicitly fails on *"rendered only inside the fold"*) are all
vacuous as written, and no Task 7 mutation covers `PR_NOTE`, `repo_slug` or the `<a href>`.

**Suggested fix:** scope every tray/worth assertion through the existing `_section(html, heading)`
helper (`:1239-1244`), and add mutations for `PR_NOTE["merged"]` and `repo_slug`'s `return None`.

---

### H4 · Task 2, Step 7 — the stated "before" measurement is wrong, and the check is vacuous in the direction that matters
**VERIFIED BY EXECUTION** against the live page at `~/explainers/dashboard.html`:

```
PLAN's needs-you regex  : 0        <- plan asserts "before: 3"
PLAN's resolved regex   : 0
tray says Nothing needs : True
actual flag spans       : ['<span class="flag">needs you</span>'] × 3
```

Today's markup is `class="flag"`. The plan's regex requires `class="flag "` — a trailing space that
only exists **after** Task 2's `f'<span class="flag {"resolved" if … else ""}">'`. So the before-run
prints `0 / 0 / True`, not the claimed `3 / 0 / True`, and `needs-you badges: 0` reads identically
before and after. Only the `resolved badges : 3` line discriminates.

**Why it matters.** The plan calls this *"the reported defect"* and *"the contradiction the user
reported"*. Half the evidence step is an assertion that cannot fail, over a before-state that was
never run.

**Suggested fix:** measure `<span class="flag[^"]*">([^<]*)</span>` and print the captured labels;
correct the before-state to `0 / 0 / True` and say which line is the falsifier.

---

### H5 · Task 3, Step 3 — `_inert_lines` diverges from `exemption_reason` on HTML comments, in both directions, while its docstring claims parity
**VERIFIED BY EXECUTION** (`t3_probe.py`, section B).

The docstring says these are *"the four contexts `exemption_reason` already learned to skip"* and
*"a second implementation would re-earn all four."* `exemption_reason` scans **within** a line for
`<!--`/`-->` (`:116-132`); `_inert_lines` only tests `s.startswith("<!--")`.

| Input | plan `decisions()` | real `exemption_reason` |
|---|---|---|
| `Some prose <!--` then `**Decide:** hidden` … | **parses it as a live decision** | inert (`None`) |
| `<!-- hint --> **Decide:** Q` | **invisible** (whole line inert) | live (`'real one'`) |
| `<!--` / `c` / `--> **Decide:** Q` | **invisible** | live (`'real one'`) |

The fence and indent halves *do* match — verified across the short-fence, mixed-marker and
3-space-indent probes. The comment half does not.

**Why it matters.** Row 1 is the false positive the ⚠ box exists to prevent: an entry that opens an
HTML comment mid-line and quotes `**Decide:**` inside it becomes a decision. A near-copy whose
comment *asserts* parity is worse than an honest second implementation, because nobody re-checks it.

**Suggested fix:** either lift the probe loop from `exemption_reason` into a shared helper both call,
or delete the parity claim and state the narrower rule the code actually implements.

---

### H6 · Task 1 — the gate and the renderer are made to disagree about `[needs-you] [heads-up]`
**VERIFIED BY EXECUTION** (`header_error` with Task 1's widened `FLAG`):

```
header_error("## 2026-08-28 [needs-you] [heads-up]")  -> None
_added_entry_line("+## 2026-08-28 [needs-you] [heads-up]") -> True
```

`header_error` strips both flags via `FLAG.sub` (`:51`), so the **gate accepts** the header while
Task 1 Step 4 makes the **renderer** set `entry["error"]` and print *"Could not parse this entry"*.

Spec §9 lists exactly this falsifier: *"**Gate and renderer agree** — fails if the gate accepts an
entry the renderer marks malformed."* And `header_error`'s own docstring (`:38-45`) says it is
*"Shared by the parser and the ratchet so they CANNOT disagree about what a header is"*, recording
five previously-measured divergences. Task 1 adds a sixth. No task addresses it.

**Suggested fix:** move the both-flags refusal into `header_error` (where the ratchet also sees it),
and have the parser read the same verdict.

---

## Medium

### M1 · Case arithmetic is wrong at Tasks 3, 5 and 6 — **VERIFIED BY EXECUTION**
Counting `case(` calls in the plan's own blocks, then confirming against the applied copy:

| Step | Plan says | Actual `case()` calls | Real tally |
|---|---|---|---|
| Task 3 Step 4 | `72/72 (49 + 23)` | **21** | **70/70** |
| Task 5 Step 6 | `247/247` | **9** | **246** |
| Task 6 Step 7 | `259/259` | **10** | **256** |

Tasks 1, 2 and 4 are arithmetically correct (222, 228, 237). A stated outcome that cannot occur is
the defect this project files repeatedly; here it lands three times in a plan whose Task 7 opens with
*"Take `expect` FROM THE RUN, never from prediction."*
**Fix:** correct to 70 / 246 / 256, or drop the totals and state the delta only.

### M2 · Global Constraints attribute the cannot-run tally to the wrong script — **VERIFIED BY EXECUTION**
The plan says *"`gen-dashboard.py --self-test` = 217/217 + 6/6 cannot-run; `check-dashboard-entry.py
--self-test` = 46/46."* Measured on HEAD: `gen-dashboard` prints `217/217 passed` and **nothing
else**; `check-dashboard-entry` prints `46/46 passed` **and** `6/6 cannot-run cases passed`. The
`6/6` belongs to the second script.
**Fix:** swap them.

### M3 · The CommonMark fence-length rule in `_inert_lines` has no test — **VERIFIED BY EXECUTION**
```
SURVIVED  the CommonMark fence-length rule is dropped
          (len(m.group("ch")) >= len(fence)  ->  removed)
```
The plan carries the rule *and a comment about it*, and the ⚠ box cites `:104-111` as a measured
escape — but Task 3's fixtures use only a plain ```` ``` ```` fence. The sibling
`exemption_reason` suite has three cases for exactly this (`:200-206`).
**Fix:** port the short-fence / tilde / unterminated fixtures across.

### M4 · The blockquote branch is dead, and the case naming it passes for another reason — **VERIFIED BY EXECUTION**
```
SURVIVED  _inert_lines forgets blockquotes
          (s.startswith(">") or _indented(line)  ->  _indented(line))
```
`> **Decide:** quoted` is already not an opener, because the outer loop requires
`lines[i].lstrip().startswith(OPENER)` and `lstrip()` leaves the `>`. So
`case("a blockquoted Decide is not a decision", …)` is green with the branch deleted.
**Fix:** add a fixture that can only pass via the branch (e.g. a blockquoted option list under a live
opener), or drop the branch and say so.

### M5 · `unresolved_heads_up` ignoring `cleared` survives — **VERIFIED BY EXECUTION**
```
SURVIVED  unresolved_heads_up ignores the cleared set
```
Task 2 tests `cleared_ids` and `badge_of` on a heads-up, but nothing asserts that a **resolved**
heads-up leaves the "Worth knowing" block. Spec §3: *"Both are cleared by the same `[resolved: <id>]`
marker."*
**Fix:** one Task 5 case — a `[heads-up]` followed by its `[resolved:]` renders no Worth-knowing row.

### M6 · Spec §9's *"Validation never writes `entry["error"]`"* has no falsifier
It is the single load-bearing invariant of §8b and appears in the plan as a Global Constraint and two
code comments, but no test asserts `e["error"] is None` (or `e in unresolved(entries)`) after
`decision_errors` has run over it. Task 4's *"and it is not marked broken"* covers the **resolved**
case (falsifier 4), not this one. Only indirectly caught, via *"a malformed ask does NOT read as an
all-clear"*.
**Fix:** one direct assertion in Task 4 on the malformed-ask fixture.

---

## Low

- **L1 · Two unreachable clauses in `decisions()`** — **VERIFIED**: `OPT.match("")` is `None` and
  `OPT.match("**Decide:** Two")` is `None`, so `or lines[j].strip() == ""` and the inner
  `startswith(OPENER)` break can never fire. Both survive deletion. The case
  *"a blank line after the opener means no options"* is named for the dead clause and passes through
  `not m`. Delete both, or rewrite the case so it can only pass via the clause.
- **L2 · `class="flag "` carries a load-bearing trailing space** produced by
  `f'<span class="flag {"resolved" if … else ""}">'`. Task 2 Step 7's regex depends on it. Emit
  `class="flag resolved"` / `class="flag"` explicitly.
- **L3 · Task 7's JSON blocks are comma-separated fragments**, not appendable arrays. "Append to
  `scripts/mutations/*.json`" needs a leading comma inside the existing list; unstated, and both
  manifests are flat arrays (47 and 12 entries — both counts confirmed).
- **L4 · Task 5's Interfaces declares `cleared_ids` as consumed**; the code never references it (same
  block as H2's `decision_errors`).
- **L5 · `e["plain"].split("\n\n")[0]`** will not find a paragraph break in a CRLF store, where the
  separator is `\r\n\r\n`. `exemption_reason` has an explicit CRLF case (`:215`), so the store is not
  assumed LF-only. `decisions()` itself is CRLF-safe (verified).
- **L6 · Task 7's budget mutation makes the suite shell out.** `if budget["calls"] >= …` → `if False:`
  sends `pr_state(99, …)` and `pr_state(98, …)` to real `gh pr view` calls. It is still caught (any
  non-`exhausted` answer reddens the named case), but two live 30s-bounded lookups per mutation run
  is a cost the plan does not mention.
- **L7 · Task 7's worth-knowing mutation crashes the suite after its expected `[FAIL]`.** With
  `elif False:`, the next case's `err_html.split("<h2>Worth knowing</h2>")[1]` raises `IndexError`.
  The named case prints first, so the harness verdict is correct — but every Task 6 case after it
  goes unrun under that mutation.

---

## What was checked and found CORRECT (so round 2 need not re-open it)

- **`build()` arity.** `def build(entries, days, prs, pr_error, git_error, window, exemptions,
  exempt_error, store, store_error, generated_at="")` — 10 required positionals. Every one of the
  plan's six positional calls passes exactly 10, in the right order. Confirmed by running them.
- **Every name the plan references exists and is reachable**: `FENCE` (`:60`), `_indented` (`:63`),
  `exemption_reason` (`:83`), `_added_entry_line` (`:57`), `header_error` (`:37`), `_GATE` (`:312`),
  `_gh_json` (`:490`), `_pos` (`:435`), `_slug` (`:547`), `_inline` (`:220`), `_prose` (`:223`),
  `_with_run` (`:1554`, nested in `_self_test`), `GLOSSARY` (`:676`), `parse_entries` (`:339`),
  `unresolved` (`:439`), `EXPECTED_MUTATIONS` (`:432`, values 47 and 12 as stated).
- **All 21 of Task 3's asserted fixtures pass** against Task 3's implementation, run on the real
  `FENCE`/`_indented` — including all four inert contexts, adjacency, star markers and the
  blank-line-after-opener case. The defects above are things the fixtures do **not** ask.
- **Every mutation anchor in Task 7 appears verbatim and exactly once** in the code the plan
  produces, including the two-line `elif store_error:` anchor and the escaped
  `PR_TOKEN = re.compile(r"\bPR #(\d+)\b")`. Nine of the eleven redden the case they name.
- **Every complete Python block parses.** The three that do not (`L105`, `L725`, `L1053`) are
  deliberate fragments — a nested `if/elif`, an HTML template line, a dict body. `L105`'s
  indentation claim is correct: the trailing `if` sits at the `for`'s level and splices cleanly.
- **Task 1's arithmetic** (222 / 49), **Task 2's** (228) and **Task 4's** (237, modulo B2) are right,
  and the store holds 26 entries as Step 6 states.
- `check-docs.py` and `check-anchors.py` are green on the plan as committed.

## Spec-coverage audit (the plan's table, checked rather than trusted)

| Spec item | Plan claims | Measured |
|---|---|---|
| §4 Nesting rule | Tasks 1, 3, 6 | **absent** — B4 |
| §4 "a heads-up cannot ask", at the page | Tasks 1, 3, 6 / §7 → 4, 5, 6 | **no caller** — H2 |
| §4 both flags at once | Task 1 | renderer only; gate disagrees — H6 |
| §5a "an option carrying `PR #N` is linked" | Task 6 | no assertion; deletion survives — H3 |
| §5b "unfolded" for Worth knowing | Task 5 | asserted on the whole page; deletion survives — H3 |
| §6 stale/missing/exhausted rendering | Task 6 | `pr_state` only; `PR_NOTE` untested — H3 |
| §9 "Validation never writes `entry["error"]`" | "every task's tests" | no direct falsifier — M6 |
| §9 "Gate and renderer agree" | "every task's tests" | **fails by construction** — H6 |
| §3, §5c, §5d, §7 (tray half), §8a, §8b, §11 | 1/2/4/5 | present and correctly placed |

---

**Verdict: NOT CONVERGED** — 4 Blocking, 6 High, 6 Medium, 7 Low.

Two of the plan's own tests are red against its own implementation, one pre-existing test is broken
with no mention, one Task 7 mutation cannot produce the verdict Task 7 requires, and nine one-line
deletions in the new code leave the new suite green.
