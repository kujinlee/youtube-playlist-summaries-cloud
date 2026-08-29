# Plan review — project dashboard, round 2, CLAUDE half

**Subject:** `docs/superpowers/plans/2026-08-28-project-dashboard-plan.md` (v2.2), branch
`docs/dashboard-plan-review`, HEAD `6f853ea`.
**Spec:** `docs/superpowers/specs/2026-08-28-project-dashboard-design.md` (v5, `c5fcb07`).
**Prior rounds read and folded in before starting:** `…-r1-codex.md`, `…-r1-claude.md`,
`…-r2-codex.md`. Nothing already fixed is re-reported; where a *fix* is the subject, the finding
says so.

## READY TO EXECUTE: **NO**

**Shortest must-change list:**

1. The CI ratchet **still cannot run** on a real `pull_request` checkout. The refspec fixed the
   error Codex saw and left a different one in its place (B1).
2. Task 4's Step 1 script has no `import re`, so Steps 2 and 4 both state outcomes that cannot
   occur (B2).
3. `_ADDED_ENTRY` and `HEADER` still disagree on five header shapes; the plan says they cannot (H1).
4. Spec §9's alarm — *every day with commits and no entry is visibly marked* — is not built, has no
   case, and the Self-Review marks §9 ✅ (H2).
5. Two `[resolved:]` flags on one header: the first is silently dropped (H3).
6. "Rendered in place" holds only for a file ordered newest-**first**; the store is newest-**last**
   (H4).
7. Four self-test rows cannot fail for the thing they name (H5, H6, M1, and the `#9` row).

**Counts: 2 Blocking · 8 High · 6 Medium · 5 Low.**

---

## Method — and the transcription diff, first

The brief's most important instruction is that a transcription is not a copy unless it is diffed.
I did not retype anything. I extracted **all 43 fenced blocks** from the plan programmatically by
line range, wrote each to a file, and assembled the two scripts from those files. Then I proved the
assembly is byte-exact:

```
135 contiguous-in-my-file: True | in-plan: True
272 contiguous-in-my-file: True | in-plan: True
390 contiguous-in-my-file: True | in-plan: True
427 contiguous-in-my-file: True | in-plan: True
573 contiguous-in-my-file: True | in-plan: True
594 contiguous-in-my-file: True | in-plan: True
652 contiguous-in-my-file: True | in-plan: True
756 contiguous-in-my-file: True | in-plan: True
986 contiguous-in-my-file: True | in-plan: True
--- per-line audit: any line in my file NOT present in the plan?
none
```

Every plan block appears **contiguously** in my copy, and no line of my copy is absent from the
plan. Round 2's headline Blocking cannot recur here by construction.

Results of the assembled suites, matching the plan's own claim:

```
$ python3 gen-dashboard.py --self-test
58/58 passed
gen_rc=0

$ python3 check-dashboard-entry.py --self-test
32/32 passed
gate_rc=0
```

**NOT RUN, stated rather than inferred:** Task 3 Step 6 and Task 5 Steps 1/5 (browser: fold survival
across live reload, the Ask tray on screen, the marked bar as pixels) — these need a running server
and a human eye, and I did not open a browser. Task 6 Step 5's *"falsify it in CI"* — I cannot run
GitHub Actions; B1 below is a local reproduction of the Actions checkout shape and says so.

---

# Blocking

## B1 — the CI ratchet still cannot run: the refspec fixed the error message, not the gate

**Claim (Task 6 Step 5):** *"The `+refs/heads/X:refs/remotes/origin/X` form creates the ref."* and
in the Round 2 table: *"**Reproduced and re-verified here**: bare form → `origin/master MISSING`,
`diff rc=128`; refspec form → ref created, diff clean"*.

**What I checked.** I rebuilt the shape `actions/checkout@v4` actually produces for
`on: pull_request` — `.github/workflows/ci.yml:13-14,31` has **no `fetch-depth:`**, so the default
is 1, and the ref checked out is the synthesised PR **merge** ref. I created an origin with
`master`, a feature branch and `refs/pull/1/merge`, then cloned it exactly the way the action does
(`--depth=1` on the merge ref), then ran the plan's fetch and the ratchet verbatim.

**Actually true:**

```
--- shallow? YES ; commits reachable: 1
--- origin/master present before the fetch: MISSING

=== the plan's Task 6 Step 5 fetch, verbatim ===
 * [new branch]      master     -> origin/master
fetch_rc=0
--- origin/master now: 6beeb86

=== the ratchet ===
CANNOT RUN — git diff exited 128: fatal: origin/master...HEAD: no merge base
Treat this as NOT CHECKED.
ratchet_rc=2
```

The refspec **does** create `origin/master` — that half of the fix works. But the gate still exits
**2 on every PR**, for a second reason the fix never addressed: `HEAD` is a depth-1 graft, so
`origin/master...HEAD` has no computable merge base. Same outcome as before (`ratchet_rc=2`,
`CANNOT RUN`), different sentence.

This is the plan's own standard turned on the plan: *"the failure was loud … but a gate that
reliably cannot run is not a gate, so this had to be fixed rather than tolerated."* It was verified
against the **symptom Codex reported** (does `origin/master` exist?) rather than the **outcome**
(does the ratchet run?), in a scratch repo that was not shallow at `HEAD` and therefore could not
observe this.

**The remedy, measured, not guessed.** Deepening `HEAD`'s own ref clears the graft and the gate then
does its job:

```
=== remedy A: also deepen the PR merge ref ===
shallow file still present? no
REFUSED — 1 tracked file(s) changed and no entry was added to docs/dashboard-entries.md. …
ratchet_rc=1

=== what the diff actually contains now ===
lib/x.ts
```

Simplest form: give the existing `- uses: actions/checkout@v4` a `with: fetch-depth: 0`, and drop
the bespoke fetch entirely. Whatever is chosen, Task 6 Step 5's acceptance criterion (*"seen to
refuse on GitHub"*) is the only thing that can close this — it is precisely the observation the
local verification could not make.

**VERIFIED** (local reproduction of the Actions checkout shape; the Actions run itself is NOT RUN).

---

## B2 — Task 4's Step 1 file has no `import re`; Steps 2 and 4 both state outcomes that cannot occur

**Claim (Task 4, Step 2):** *"Run: `python3 scripts/check-dashboard-entry.py --self-test` /
Expected: `NotImplementedError`."*
**Claim (Task 4, Step 4):** *"Run … Expected: exit 0, no `[FAIL]` lines."*

**What I checked.** `block_1105` (plan lines 1106-1251) written to a file and run as the plan says.
Its imports are `from __future__ import annotations` and `import sys` (plan lines 1117-1118), and
line 1128 is `FENCE = re.compile(...)`. `import re` first appears at plan line 1294 — **Task 4
Step 5**.

**Actually true:**

```
=== Step 2 expected: NotImplementedError ===
    FENCE = re.compile(r"^(?P<ind> {0,3})(?P<ch>`{3,}|~{3,})")
            ^^
NameError: name 're' is not defined. Did you forget to import 're'?
step1 rc=1

=== Step 4 expected: exit 0, no [FAIL] ===
    FENCE = re.compile(r"^(?P<ind> {0,3})(?P<ch>`{3,}|~{3,})")
            ^^
NameError: name 're' is not defined. Did you forget to import 're'?
step3 rc=1
```

The module does not import at all, so the TDD loop the task is built around cannot run: Step 2's
red is the wrong red (an implementer chasing `NotImplementedError` will conclude the stub is wrong),
and **Step 4's green is unreachable** — `verdict` is implemented in Step 3 but `import re` does not
arrive until Step 5, two steps later.

Why round 2 missed it: `FENCE` was added in v2.1, after the block that would have imported `re`, and
both reviewers assembled the *final* file, where Step 5's import is present. The intermediate states
the task prescribes were never executed. Fix is one line — put `import re` in the Step 1 block.

**VERIFIED.**

---

# High

## H1 — `_ADDED_ENTRY` and `HEADER` still disagree on five header shapes

**Claim (Round 2 table):** *"`HEADER` now requires the space … and the gate's `_ADDED_ENTRY`
requires it too — **so the two can no longer disagree about what an entry is**."* The code comment
at plan line 1297 states the same as a design property: *"a header the parser calls malformed must
not satisfy the gate, or the ratchet would pass exactly the entry the page cannot use."*

**What I checked.** Ran `gate._added_entry_line("+"+h)` against `gen.parse_entries(h + …)["error"]`
for nine header shapes.

**Actually true:**

```
header line                       gate counts it  parser verdict
## 2026-08-28                     True            OK
## 2026-08-28 [needs-you]         True            OK
##2026-08-28                      False           MALFORMED
## 2026-02-30                     False           MALFORMED
## 2026-08-28-foo                 True            MALFORMED   <-- DISAGREE
## 2026-08-28.                    True            MALFORMED   <-- DISAGREE
## 2026-08-28 [needs-yo]          True            MALFORMED   <-- DISAGREE
## 2026-08-28 [resolved: 1999-01-01/9]True         MALFORMED   <-- DISAGREE
## 2026-08-28 rambling title text True            MALFORMED   <-- DISAGREE
```

`_ADDED_ENTRY = r"^\+## (\d{4}-\d{2}-\d{2})\b"` stops at the date and a word boundary; `HEADER`
plus `_valid_date` plus the leftover-flag check and the empty-title check reject far more. So the
gate goes green on a branch whose entry the page renders under *"Could not parse this entry"* — the
exact stated failure. Note the typo'd-flag row: the plan itself argues an unknown flag matters
because *"a typo'd `[needs-you]` would otherwise silently drop an item off the page's first block"*
— and that is one of the branches the ratchet waves through.

The v2.2 fix closed exactly the two shapes Codex named. This is the instance-not-class pattern:
answer *"what else is this true of?"* with a run, not a recollection. **VERIFIED.**

## H2 — spec §9's alarm (commits, no entry) is not built, has no case, and §9 is marked ✅

**Spec §9:** *"Observable, because round 2 rightly called that unattributable alone: … **every day
with commits and no entry is visibly marked**"*. **Spec §7.3** calls this the thing the gate
*repairs*: *"'a bar with no entry' becomes a precise statement — this work shipped without an entry"*.
**Plan Self-Review:** *"§9 checks | Tasks 1, 4, 5 | ✅ self-tests"*.

**What I checked.** `_bar` (plan line 793): `marked = day["has_entry"] and day["commits"] == 0`.
That is spec **§6.1**'s requirement — an entry on a day with *zero commits*. The **inverse** — a day
with commits and no entry — has no branch anywhere in `build`.

**Actually true:**

```
day with 7 commits and NO entry  : <a class="bar" href="#day-2026-08-27" style="height:48px" title="2026-08-27: 7 commits" …>
day with 7 commits and an entry  : <a class="bar" href="#day-2026-08-26" style="height:48px" title="2026-08-26: 7 commits" …>

identical after normalising the date? True
```

Byte-identical. The alarm §7 exists to repair is not rendered, is not tested, and is not in the
Self-Review's four admitted Gaps — while its row carries a ✅. This is round 1's headline defect
(a Self-Review claiming coverage it does not have) recurring on a different row. **VERIFIED.**

## H3 — two `[resolved:]` flags on one header: the first is silently discarded

**Spec §6.2:** *"Flags | **zero or more** of `[needs-you]`, `[resolved: YYYY-MM-DD/N]`,
space-separated, after the date"*. Plural is explicitly grammatical.

**Code (plan lines 205-212):** `for f in flags: … entry["resolves"] = f.split(":", 1)[1].strip()`
— one scalar field, assigned once per flag, last write wins. No error, no leftover text (both flags
are consumed by `FLAG.sub`).

**What I checked / actually true:**

```
=== 1. TWO [resolved:] flags on one header (spec §6.2 allows 'zero or more') ===
  resolves parsed as: [None, None, '2026-08-27/1']
  errors: [None, None, None]
  STILL UNRESOLVED: ['2026-08-26/1']
```

An author clearing two items in one entry clears one. The other stays on "What needs you" forever,
with `error: None` — nothing on the page says why. That is verbatim the failure the plan spends
pass 2 on (lines 231-235: *"the author appends `[resolved: …]`, believes an item is cleared, and it
stays on 'What needs you' forever with nothing anywhere saying why"*), in the sibling case the fix
did not consider. Either make `resolves` a list, or make a second `[resolved:]` malformed — but not
silent. **VERIFIED.**

## H4 — "rendered in place" holds only for a file ordered newest-first; the store is newest-last

**Claim (plan line 765 and the H3 row of *What v2 changed*):** *"a malformed block stays adjacent to
its file neighbours (spec §6.2, 'rendered in place')"*, asserted by
`case("malformed renders BETWEEN its neighbours, not at the bottom", …)`.

**What I checked.** The plan's own fixture (plan lines 697-699) lists `2026-08-28`, then the
malformed block, then `2026-08-27` — i.e. **newest first**. But the store the plan creates says the
opposite (Task 1 Step 7, plan line 340): *"One `## YYYY-MM-DD` block per entry; **newest at the
end**"*, and the skill (Task 6 Step 2) says *"Append one block"*. I ran the same three entries in
both orders.

**Actually true:**

```
The plan's own case, verbatim (file ordered NEWEST-FIRST):
  order: [('Newest good.', 3722), ('Broken middle.', 4000), ('Older good.', 4193)]

The SAME three entries in the order the store actually uses (newest at the END):
  order: [('Newest good.', 3722), ('Older good.', 4007), ('Broken middle.', 4283)]
  in place (Newest < Broken < Older)? False
```

On a store written the way the plan says to write it, a malformed block between two entries renders
**at the bottom of the page** — the precise defect H3 filed (*"it always rendered at the very bottom
of the page, furthest from the context that would explain it"*). The fix inherits the *preceding*
valid date, which after a newest-first sort pushes the block below both neighbours whenever the file
is append-ordered. The case that certifies the fix is built on the one ordering where the bug is
invisible. **VERIFIED.**

## H5 — the marked-bar row cannot detect its own regression

**Claim (plan lines 726-732, the H4 fix):** *"The mark must differ **OUTSIDE** the visually-hidden
span, or 'visible rather than invisible' is false on screen."*

**What I checked.** Mutated `_bar` to remove **both** on-screen marks — the dot and `cls += " marked"`
— leaving only the tooltip/aria text, then ran the suite and printed the two bars.

**Actually true:**

```
*** SURVIVES *** marked bar loses BOTH the dot and the .marked class

  marked bar: <a class="bar" href="#day-D" style="height:4px" title="D: 0 commits, entry with no commits" aria-label="D: 0 commits, entry with no commits"></a>
  plain  bar: <a class="bar" href="#day-D" style="height:4px" title="D: 0 commits" aria-label="D: 0 commits"></a>
  the H4 row still sees them as DIFFERENT: True
```

`_strip_vh` removes the `.vh` span but not `title=` and `aria-label=`, which still carry
`, entry with no commits`. So the row passes on a build where the difference is **hover text and a
screen-reader label** — exactly what Task 3 Step 6 says must not be the difference (*"no hover, no
screen reader"*). Deleting the `.bar.marked` CSS rule also survives. The row moved the assertion one
layer out and stopped at the same class of defect.

A row that can fail: compare `class=` and the child elements only, ignoring every attribute whose
content is announced rather than drawn. **VERIFIED.**

## H6 — the `gh` half of §4 has no self-test at all, and §4 is marked ✅ four cases

**Spec §4:** *"Sources: entries flagged `needs-you` that are not yet resolved (§6.2), **plus
`gh pr list`**."* **Self-Review:** *"§4 what-needs-you | Task 3 Step 3 | ✅ four cases"*.

**What I checked.** Every `_B(...)` call in Task 3 Step 1 either omits `prs` (default `()`) or
passes `prs=None`. **No case ever passes a non-empty PR list.** Mutation confirms:

```
*** SURVIVES — no row goes red ***  kill the OPEN-PR rows in 'what needs you' (spec §4, gh half)
```

Half of §4's stated sources can be deleted and the suite stays green. One of the four cases is a
`gh` **failure** case, so nothing anywhere exercises `gh` **succeeding** with content. Not in the
Gaps. **VERIFIED.**

## H7 — `exemption_reason`'s indented-code rule is bypassable two ways; inert Markdown still exempts

**Claim (docstring, plan lines 1141-1152):** *"anything a Markdown reader would treat as inert text
does not count. Four constructs are skipped … an indented code block — 4+ leading spaces, Markdown's
own rule."*

**What I checked.** 18 probes against the assembled reader.

**Actually true:**

```
A. 4-space indent + a comment later on the line
    got='sneaky' expected=None <-- DIVERGES        (body: "    NO-ENTRY: sneaky <!-- c -->")
B. TAB-indented (Markdown indented code block)
    got='tabbed' expected=None <-- DIVERGES        (body: "\tNO-ENTRY: tabbed")
C. plain 4-space indent (control, should be None)
    got=None expected=None
```

Two holes in one rule:

* **Tabs.** CommonMark expands a leading tab to the 4-space tab stop *before* block parsing, so a
  tab-indented line **is** an indented code block. `probe.lstrip(" ")` counts spaces only. A
  tab-indented `NO-ENTRY:` renders as inert code and exempts the branch.
* **The head path.** When a line contains `<!--`, the text *before* it is tested with
  `head.strip().startswith(NO_ENTRY)` (plan lines 1180-1182) — which never applies the 4-space rule.
  So an indented declaration exempts as soon as the line also contains a comment.

This is the same class as the HTML-comment hole v2.1 fixed, and the same threat model the plan names
(*"the gate's own refusal message contains the literal string `NO-ENTRY: <reason>` — which is
exactly what makes quoting it back an accident waiting to happen"*). Both fixes are one line:
`lstrip(" \t")` with a tab counted as 4, and route the head through the same indent check.

Twelve other constructs I tried — a fence opened inside a comment, a comment opened inside a fence,
an unterminated comment, CRLF bodies, NBSP, blockquotes, list items, a 4-space-indented fence,
two comments on one line — all behaved correctly. **VERIFIED.**

## H8 — Task 2 Step 5's "replace the direct call" has a literal reading that silently returns "no exemptions", and Step 6a cannot tell

**Claim (Task 2 Step 5, plan lines 592-599):** *"and in `no_entry_prs`, **replace the direct call**
with:"* followed by a 4-space-indented `try/except` that binds the name `exemption_reason` and
returns on failure. The finished function is never shown. The direct call it names,
`reason = exemption_reason(p.get("body") or "")`, is at 8 spaces, **inside the `for p in data` loop**.

**What I checked.** I ran the charitable reading (block at function level, call retained) — that is
the version whose suite I report as 58/58. Then I ran the literal one: the block substituted for the
call line.

**Actually true** — it does not crash, it parses, and:

```
LITERAL reading of Task 2 Step 5's 'replace the direct call with':
([], None)
```

The resulting body:

```python
    out = []
    for p in data:
        if not isinstance(p, dict):
            return None, "gh returned JSON in an unexpected shape"
    try:
        exemption_reason = _gate_module().exemption_reason
    except Exception as exc:
        return None, f"could not load the gate's exemption reader: {exc}"
        if reason:
            out.append({...})
    return out, None
```

The `if reason:` block becomes unreachable code inside `except`, and `no_entry_prs` returns
`([], None)` — a confident *"No branch has skipped its entry"* on every page. That is the
false-healthy state §7 exists to prevent, and the plan's own note says a failure here *"is a
CANNOT RUN, never a silent 'no exemptions'"*.

**Worse, Task 4 Step 6a cannot distinguish it.** Its expected output is `no-entry: 0 err: None` —
which today is *also* the correct answer (I confirmed: 40 merged PRs scanned, zero exemptions read).
And its falsifier still fires, because `_gate_module()` is still called. Both halves of the step pass
on the broken build.

Two fixes, both cheap: show the finished `no_entry_prs`, and have Step 6a assert against a
**synthetic** body carrying a real `NO-ENTRY:` so a `0` cannot be mistaken for a `[]`.
**VERIFIED.**

---

# Medium

## M1 — newest-first ordering is untested; both ordering cases pass with no sort at all

**What I checked.** Mutation: `for i, e in enumerate(_ordered(entries))` → `enumerate(entries)`.

```
*** SURVIVES — no row goes red ***  kill _ordered (render in file order)
```

Both fixtures that touch ordering (`mixed`, `tie`) are already written newest-first, so file order
equals sorted order and the sort is a no-op for the suite. Spec §6.2's *"rendered newest-date-first"*
has no case that can fail. (Mutating the sort *direction* inside a surviving `_ordered` is caught —
but only by the "in place" row, which H4 shows is itself built on the wrong fixture order.) Fixing
H4's fixture to the store's real order fixes this too. **VERIFIED.**

## M2 — Task 6 Step 6 tells the implementer to add a roadmap entry that the plan's own commit already added

**Claim (Task 6 Step 6):** *"Also add the dashboard to `docs/roadmap-to-launch.md`. It has a merged
spec and a merged plan and **no roadmap entry at all**"*, and *What v2 changed*: *"The roadmap has no
dashboard entry at all. Added | 6 Step 6"*.

**What I checked:**

```
$ grep -in 'dashboard' docs/roadmap-to-launch.md
1331:## Project dashboard — anchor `status-visibility` — ⏳ SPEC + PLAN MERGED, NO CODE WRITTEN
…
$ git log --oneline -L 1331,1332:docs/roadmap-to-launch.md
4077817 docs(plan): dashboard plan v2 — and writing the rule down did not stop me breaking it twice
+## Project dashboard — anchor `status-visibility` — ⏳ SPEC + PLAN MERGED, NO CODE WRITTEN
```

The section was added by **`4077817` — the same commit that shipped plan v2 with this instruction**.
There is a full roadmap section including a status line, an artifacts table and the exemption-cost
analysis. An implementer following the step writes a second one. Restate the step as *update the
existing section* and name its line. **VERIFIED.**

## M3 — Task 2 Step 6's falsifier expects an output its own snippet cannot print, and forbids it in the same step

**Claim (Task 2 Step 6):** *"Expected: `prs: None err: could not run gh: …` **and the same for
`no-entry`**."* The snippet directly above prints only `dates:` and `prs:`; and the ⛔ note earlier in
the same step says *"**Do NOT verify `no_entry_prs()` here**"*.

**What I checked.** Ran the step's positive snippet and its falsifier with cwd = the real repo:

```
=== the Step 6 falsifier, as written: PATH=/usr/bin:/bin ===
dates: 74 err: None
prs: None err: could not run gh: [Errno 2] No such file or directory: 'gh'
```

There is no `no-entry` line, and there cannot be. If an implementer adds the call to satisfy the
stated expectation, at Task 2 the gate file does not exist yet, so it prints
`no-entry: None err: could not load the gate's exemption reader: …` — which **also** matches
*"the same for `no-entry`"*, i.e. the control would pass for a completely different cause than the
one it is testing. Leftover wording from the v2.2 edit that moved this to Step 6a. **VERIFIED.**

## M4 — two in-scope spec requirements are absent from the plan and from its Gaps

**Spec §3:** *"**In:** what-needs-you · what-changed · one chart · the entry gate (§7) · plain links
· **a folded glossary**."*
**Spec §5:** *"It under-counts uncommitted work, **and the page says so**."*

```
--- 'glossary' in the PLAN:      (no occurrences)
--- 'glossary' in the SPEC:  51:**In:** … · a folded glossary.
--- 'under-count' / 'uncommitted' in the PLAN:   (no occurrences)
--- in the SPEC: 71-72: It under-counts / uncommitted work, and the page says so.
```

Neither appears in `build`, in any task, in the Self-Review's coverage table (which has no §3 row at
all), or in the four stated Gaps. Both are small — a `<details>` glossary and one sentence under the
chart — but "stated rather than hidden" is the section's whole claim. **VERIFIED.**

## M5 — the bar→entry anchor is untested, and is dead for any day without an entry

**Spec §5:** *"Clicking a bar scrolls to that day's entries in §6."*

**What I checked.** `_bar` always emits `href="#day-{date}"`, but the matching
`<span class="anchor" id="day-…">` is emitted only while iterating **entries**. A day with commits
and no entry — the common case — has a link to an id that does not exist. Mutation:

```
*** SURVIVES — no row goes red ***  day anchors never emitted (clicking a bar goes nowhere)
```

Deleting every anchor leaves the suite green, so the one navigational behaviour §5 specifies has no
case. **VERIFIED.**

## M6 — ordinals are unstable: a malformed entry consumes none, so repairing one silently rebinds later resolutions

**Spec §6.2:** *"Entry id | `YYYY-MM-DD/N`, N = 1-based ordinal **within that date, in file order**"*
— not "within the valid entries". In the code, `seen[date] += 1` happens *after* the date and flag
checks `continue`, so a block malformed by date or flag takes no ordinal.

**What I checked / actually true:**

```
=== 2. ordinal instability: a malformed entry consumes NO ordinal ===
  ids while the typo is unfixed: [(None, "unrecognised text in header: '[needs-yo]'"),
                                  ('2026-08-28/1', 'The real one.'), ('2026-08-29/1', 'Cleared.')]
  unresolved: []
  ids AFTER fixing the typo:    [('2026-08-28/1', 'Typo flag entry.'),
                                 ('2026-08-28/2', 'The real one.'), ('2026-08-29/1', 'Cleared.')]
  unresolved: [('2026-08-28/2', 'The real one.')]
```

A standing `[resolved: 2026-08-28/1]` clears *"The real one."* before the repair and *"Typo flag
entry."* after it — and the item it was written for silently reopens. Pass 2's own diagnostic
(*"names an entry that could not be parsed — **fix that entry first**"*) instructs exactly the edit
that triggers this. Numbering every block, valid or not, makes the id positional and stable.
**VERIFIED.**

---

# Low

**L1 — a cited line number is wrong, twice.** The plan says
`scripts/check-explainer-delivery.py:45` sets `SKILLS = ROOT / ".agents" / "skills"` (File Structure
note and Task 6 Step 2). It is line **46**; `:53` for `PAGE_SKILLS` is correct. The plan's own Global
Constraint calls bare citations a defect; a wrong one is worse. **VERIFIED** (`grep -n`).

**L2 — a visible declaration after a closed comment is not read.** `<!-- hint -->    NO-ENTRY: real one`
→ `None`, because the residual text keeps ≥4 leading spaces and trips the indent rule. GitHub renders
that line as an ordinary paragraph. Fails **closed** (the branch is refused), so it is not dangerous —
but the self-test's *"after a CLOSED comment"* row uses a single space and cannot see it. **VERIFIED.**

**L3 — one self-test row passes for a reason unrelated to the mechanism it names.**
`("one-line HTML comment", "<!-- NO-ENTRY: nope -->\n", None)` survives deleting comment tracking
entirely: with comments off, the line does not *start* with `NO-ENTRY:` and is rejected by the
line-leading rule instead. Only the multi-line row goes red under that mutation. **VERIFIED**
(mutation `start = probe.find("<!--")` → `start = -1`).

**L4 — the chart's left-to-right direction is untested.** Mutation dropping `reversed(days)` (so the
newest day draws leftmost) leaves the suite green. **VERIFIED.**

**L5 — Task 6 Step 4's verification mutates an existing entry.** *"append a scratch line to
`docs/dashboard-entries.md` with the Edit tool"* — a line appended to a store whose last block is an
entry becomes part of **that entry's** `plain` text and renders inside it. The step's defence (*"the
store is append-only for entries, and a scratch line was never an entry"*) is true of intent, not of
the parser. Append a whole throwaway `## <date>` block instead. **VERIFIED** by reading
`parse_entries`' block splitter.

---

# What I checked and could NOT break

Recorded so the fixes that hold are not re-litigated next round.

* **B2's fix (the composer) is correct end to end.** Run against a scratch out-path so the real
  `~/explainers` was untouched:
  ```
  compose rc=0
  has <!doctype>      : True
  has charset         : True
  has the Ask tray    : True
  has the entry title : True
  ```
  and the fail-loud half, with `brief-compose.py` hidden:
  ```
  FAILED — brief-compose did not write out.html: … No such file or directory
  rc=1
  out.html exists: no
  ```
  It matches `scripts/gen-goals-page.py:487-498` line for line in shape, and `brief-compose.py`
  accepts `--content/--slug/--title/--out` (`:211-216`).

* **The gate loader is loud in all four failure modes,** and importing the gate has no side effects
  (`__name__` is `_dash_gate`, the `if __name__ == "__main__"` guard holds):
  ```
  MOVED AWAY   → err: could not load the gate's exemption reader: [Errno 2] No such file or directory
  BROKEN SYNTAX→ err: … invalid syntax (check-dashboard-entry.py, line 232)
  UNREADABLE   → err: … [Errno 13] Permission denied
  EMPTY        → err: … module '_dash_gate' has no attribute 'exemption_reason'
  ```

* **Controls A–E reproduce exactly as stated**, with `set -e` correctly absent:
  ```
  A rc=1   B rc=0   C rc=1   +## not-a-date   D rc=1   E rc=0
  ```
  I checked D specifically for a wrong-reason pass: at D the branch diff carries `lib/x.ts` plus a
  `## not-a-date` header, `real` is non-empty and `added` is False **because of the date rule**, and
  E confirms the same commit with a real date passes. D is sound.

* **The gate's own self-test is genuinely load-bearing — 8 of 8 mutations caught,** including fence
  tracking, comment tracking, the indent rule, the mismatched-fence toggle, path-vs-prefix matching,
  the three-valued `reason` collapse, `_ADDED_ENTRY`'s date validation, and its space requirement.

* **The could-not-tell contract holds** with `gh` off the `PATH`:
  `prs: None err: could not run gh: …`, `no-entry: None err: could not run gh: …`, while
  `dates: 74 err: None` (git is still on `/usr/bin`).

* **Pass 2's three diagnoses are correct and distinguishable**, including the "names an entry that
  could not be parsed" branch, and `resolves` is treated as three-valued by both of its consumers.

* **Task 5's rows are syntactically valid against the real helper.** `scripts/explainer-serve.py`'s
  `case(name, callable)` (`:906-921`) takes a lambda, as the plan's rows do — and `RELOAD_JS` is
  **appended** to the body (`:668`), so `restoreDetails()` runs after the DOM exists.

* **The hook and its registration match the repo.** `.claude/settings.json`'s `PostToolUse`
  `"Edit|Write"` array holds three commands beside which the new one fits, and
  `.claude/hooks/regen-goals-page.sh` uses the identical stdin-parsing shape.

* **`check_skill_symlinks` (`scripts/check-docs.py:212-228`) confirms the `.agents/skills` + symlink
  claim** — it fails on a real directory under `.claude/skills/`, exactly as the plan says.

* **The `docs/dev-process.md` budget claim holds today:** `214` lines against `LINE_BUDGETS` `220`
  (`scripts/check-docs.py:190-191`). Two rows fit.

* **Task 1 Step 8 is accurate:** the store from Step 7 parses as `1 entries; [None]`.

* **Task 4 Step 6a's expected `no-entry: 0 err: None` is true today** — 40 merged PRs scanned, zero
  exemptions. PRs #170 and #171 do contain the literal `NO-ENTRY`, and are correctly ignored because
  the marker is mid-line, not by any of the four inert-construct guards.

---

## On the Self-Review and its four Gaps

Checked the same way round 1 checked v1's. The four stated Gaps are all real and correctly stated.
**Four further shortfalls are unadmitted:** §9's commits-without-entry alarm (H2), the `gh` half of
§4 (H6), §3's folded glossary and §5's under-count sentence (M4). Two ✅ marks do not survive
execution: §9's, and §4's *"four cases"*.

The claim *"**Placeholders:** none"* holds — every code step carries code. The type-consistency
paragraph is accurate.

---

**NOT CONVERGED**
