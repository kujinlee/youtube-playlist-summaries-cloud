# Plan review — project dashboard, ROUND 3, Claude half

**Subject:** `docs/superpowers/plans/2026-08-28-project-dashboard-plan.md` (v3), branch
`docs/dashboard-plan-review`, HEAD `af9dccc`.
**Spec:** `docs/superpowers/specs/2026-08-28-project-dashboard-design.md` (v5).

# READY TO EXECUTE: NO

**2 Blocking, 4 High, 7 Medium, 7 Low.**

Must-change list, shortest form:

1. Give `gen-dashboard.py` an import block. The plan supplies none, anywhere, so **Task 2 Step 1
   dies at import** — `NameError: name 're' is not defined`. This is round 2's B2, fixed for the
   gate and shipped for the other file.
2. Show `no_entry_prs`, `commit_dates` and `open_prs`. All three are prose only; the round-2 fix
   table says of `no_entry_prs` *"The finished function is shown"*. It is not. `commit_dates` also
   silently drops spec §5's `git log --first-parent`.
3. Add a case for the day anchors, and correct the evidence. Deleting every `id="day-…"` leaves the
   suite **70/70 green** — the mutation the plan itself names, in a suite it certifies as
   `19/19 caught`, on a finding round 2 already filed (r2-claude M5).
4. `exemption_reason` compares fence *characters* and ignores fence *length*, so a `NO-ENTRY:` line
   that CommonMark renders as inert code **exempts the branch**. Same class as the v2.1 HTML-comment
   fix, re-shipped.
5. Pass 2's three-way diagnostic never fires for a bad-date target — the canonical malformed entry
   and the plan's own example. v2.1 records this as fixed.
6. Task 2 Step 4 states *"exit 0, no `[FAIL]` lines"*; the only self-test in the plan raises
   `NameError: name 'unresolved' is not defined` at that point.

---

## Method, and what it cost

Every fenced block was extracted **programmatically by line range** (26 blocks, 11 Python) into
`blocks.json` and assembled by index — nothing retyped, so the round-2 transcription failure cannot
recur in this review. The assembled files reproduce the plan's stated evidence exactly:

```
gate      --self-test   42/42 passed   rc=0
generator --self-test   70/70 passed   rc=0     (only after imports were ADDED — see B1)
controls A–F            A rc=1  B rc=0  C rc=1  +## not-a-date present  D rc=1  E rc=0
                        all five previously-waved-through shapes rc=1
```

**On v3's own extraction claim** ("33 symbols, verified byte-for-byte against the running copy"):
the *byte-for-byte* half is **NOT CHECKABLE** — the executed files are not in the repo, so there is
nothing to diff against. The *count* half does not reconcile: an `ast` parse of the plan's eleven
Python blocks yields **32** top-level definitions (27 unique), and the two constants given in prose
(`TECH_MARKER`, `BLOCK`) make **34**. No counting I can construct gives 33. Filed Low; the claim
should be dropped rather than corrected, since it is a claim about files nobody else can open.

Mutations run: **59** across three passes (four were no-ops on inspection and were rewritten).

---

# Blocking

## B1 — `gen-dashboard.py` has no imports anywhere in the plan; Task 2 Step 1 cannot execute

**Quoted claim (Task 2 Step 1, plan:493-522):** *"**Step 1: The module header and the grammar
import**"* … *"with `TECH_MARKER = "<!--tech-->"` and `BLOCK = re.compile(r"^##\s*\S")` above them."*

**What I checked.** Assembled `gen-dashboard.py` from exactly what the plan gives — the prose
constants, then block `496-519` — and ran it.

**Actually true:**

```
Traceback (most recent call last):
  File ".../scripts/gen-dashboard.py", line 3, in <module>
    BLOCK = re.compile(r"^##\s*\S")
            ^^
NameError: name 're' is not defined. Did you forget to import 're'?
rc=1
```

`grep -n "^import\|^from" ` over every Python block for this file returns nothing. Three modules are
used and none is imported: `re` (`BLOCK`, `_slug`, and the self-test's `re.findall`), `html as _html`
(31 call sites across `_bar` and `build`), `datetime as _dt` (`bucket_days`). With them added the
suite is 70/70; without them the file will not import, so **Task 2 Steps 1–6, Task 3 and Task 4 all
state outcomes that cannot occur.**

This is verbatim the class of round 2's B2, which v3 fixed for the *other* file and announced in a
⚠ box at Task 1 Step 1 — *"`import re` belongs in THIS block"* — while the file that box does not
cover shipped with the same hole. Instance, not class. **VERIFIED.**

## B2 — the three impure collectors have no code, and the round-2 fix table says one of them does

**Quoted claim (v3's Round-2 table, plan:1604):** *"H8 | … | **The finished function is shown**; the
check is paired with a falsifier that hides the gate file"*.

**What I checked.**

```
$ grep -n "no_entry_prs\|commit_dates\|open_prs" <plan>
643, 686, 689, 698, 702, 1351, 1354, 1434, 1461, 1546      # prose and tables only
$ grep -n "def no_entry_prs\|def commit_dates\|def open_prs" <plan>
(no matches)
```

**Actually true.** No function body exists for any of the three. Consequences, each independently
material:

- **Spec §5 is dropped without being noticed.** *"Height = commits on `git log --first-parent HEAD`
  for that day — named explicitly because 'commits' is ambiguous once branches and squash-merges
  exist."* The string `first-parent` does not appear in the plan at all. The §9 alarm — *this day
  shipped with no entry* — is computed from whatever `commit_dates` counts, so the ambiguity §5
  exists to close is reintroduced at the one place it changes an alarm.
- **Spec §6.2's ref split is dropped too**: *"The renderer reads the working tree … The chart reads
  `HEAD`."* Neither ref is named in the plan.
- **Both verification steps are literal ellipses.** Task 3 Step 3 is `PATH=/usr/bin:/bin python3 -c "…"`
  (plan:709) and Task 6 Step 5 is `python3 -c "…no_entry_prs()…"` (plan:1354), each with a stated
  expected output for a command the plan does not contain.
- **§7's display is the mechanism, not a nicety.** The spec calls the gate *"the answer to the
  design's largest risk"* and requires the exemption to be **displayed**; `no_entry_prs` is that
  display, and it is a paragraph.

Round 2 asked for exactly this (*"Two fixes, both cheap: show the finished `no_entry_prs`"*,
r2-claude:417). The table records it as done. **VERIFIED.**

---

# High

## H1 — the day anchors survive deletion: `19/19 mutations caught` is false, and the Self-Review's §5 ✅ is unearned

**Quoted claim (Task 4 Step 4, plan:1163-1168):** *"Break each behaviour and confirm the named case
goes red: … **the day anchors**, `_ordered`, pass 2 … **19 of 19 mutations were caught when this
suite was written; a survivor means a case that cannot fail for the thing it names.**"*
And the Self-Review §5 row: *"✅ buckets, oldest-left direction, the under-count sentence, and the
bar→entry anchor"*.

**What I checked.** Replaced the anchor emission in `build` with `day_anchor = ""` and re-ran:

```
*** SURVIVED ***  P4  day anchors never emitted (every bar href is a dead link)
     'id="day-' still in mutated source: False
     70/70 passed   rc=0
```

**Actually true.** Every `<span class="anchor" id="day-…">` can be deleted and the suite stays green.
Spec §5's one navigational behaviour — *"Clicking a bar scrolls to that day's entries in §6"* — has
no case. `case("a bar with an entry does link", 'href="#day-' in written, True)` asserts only that
`_bar` **emits** the href; nothing asserts the target exists, and the two are written in different
functions.

This is the first half of r2-claude's M5, quoted there with the same result. v3 fixed the *second*
half (dead links on days without entries — `tag = "a" if has_entry else "span"`, mutation-caught as
M20/N-series here) and recorded the row as *"dead bar links on days without entries"*, closing the
half it saw. **The evidence line `19/19 caught` names this exact mutation.** Also note Task 4 Step 4
writes a hard count inside a step, which the plan's own Global Constraint forbids —
*"If a step names a count anywhere, that is a defect in this plan"*. **VERIFIED.**

## H2 — `exemption_reason` ignores fence LENGTH, so inert Markdown code exempts the branch

**Quoted claim (`exemption_reason` docstring, plan:207-215):** *"anything a Markdown reader treats as
inert does not count: fenced code (**closed only by its own character**), indented code…"*
And v2.1 (plan:1507): *"`exemption_reason` now tracks fences by their own character … 11 new
self-test rows cover all of it."*

**What I checked.** CommonMark requires a closing fence to be **at least as long** as the opener, so
a 3-backtick line inside a 5-backtick fence is content, not a close. Ran the gate on it:

```
  body: '`````\n```\nNO-ENTRY: sneaky\n`````\n'
  gate says -> 'sneaky'
  verdict(['lib/x.ts'], False, body) -> (0, 'exempted by declaration — sneaky')

  '~~~~\n~~~\nNO-ENTRY: sneaky2\n~~~~\n'  -> (0, 'exempted by declaration — sneaky2')
```

**Actually true.** `FENCE = re.compile(r"^(?P<ind> {0,3})(?P<ch>`{3,}|~{3,})")` captures the run but
`ch = m.group("ch")[0]` keeps only the first character, so length is discarded and a short inner
fence closes a long outer one. The branch is exempted on a line that GitHub renders as **grey code
inside a code block** — the reader sees inert text, the gate sees a decision.

The character rule was fixed in v2.1 and the length rule was never asked. It is the identical shape
to the HTML-comment case v2.1 calls *"the one that mattered"*, with the identical trigger: a PR body
that **documents this escape hatch** — which the Task 6 SKILL.md will teach people to write — and
nests it, as anyone quoting markdown-inside-markdown must.

**Not Blocking, by the plan's own precedent** (it graded the HTML-comment case latent rather than
Blocking, and nothing in the repo triggers it today: no `.github/PULL_REQUEST_TEMPLATE`, verified).
The fix is two characters — compare `len(m.group("ch"))` and require `>=` the opener.
The three self-test rows that would fail on a correct implementation do not exist. **VERIFIED.**

## H3 — pass 2's three-way diagnostic never fires for a bad-date target, which is the case that motivated it

**Quoted claim (v2.1, plan:1514-1516):** *"pass 2 said 'names no entry in this file' even when the
entry existed and was merely unparseable, sending the author to hunt for a typo that was not there.
**It now distinguishes the three cases.**"*

**What I checked.** Ran all three against the assembled parser:

```
(a) target genuinely ABSENT
    -> '[resolved: 1999-01-01/9] names no entry in this file'
(b) target EXISTS, BAD DATE
    -> '[resolved: 2026-02-30/1] names no entry in this file'          <-- WRONG
(c) target EXISTS, valid date, TYPO'D FLAG
    -> '[resolved: 2026-08-26/1] names an entry that could not be parsed — fix that entry first'
```

**Actually true.** The discriminating branch is `elif any(o["id"] == r for o in out)`, and `id` is
assigned only inside `if m is not None and _GATE.valid_date(m.group(1))`. **A block malformed by
date never gets an id**, so it can never be found, and case (b) falls through to the "names no
entry" message — sending the author to hunt for a typo that is not there, verbatim.

Bad dates are the canonical malformed entry: spec §6.2 names `2026-02-30` as the example, the plan's
own self-test uses it (`bad = parse_entries("## 2026-02-30\n…")`), and control D exercises it. Only
the narrower valid-date-bad-flag shape reaches the fix.

The branch also has **no case at all** — `case("resolve of an unknown id is an error",
ghost[0]["error"] is not None, True)` asserts non-None and never reads the message, so all three
strings are interchangeable to the suite. That is why the fix could be recorded without being run.
**VERIFIED.**

## H4 — Task 2 Step 4's stated output is unreachable: the plan's only self-test needs a Task-3 function

**Quoted claim (Task 2 Step 4, plan:602-610):** *"Cases for: … **two `[resolved:]` flags on one
header** … All are in the assembled `_self_test` in Task 4 Step 4. Expected: exit 0, no `[FAIL]`
lines."*

**What I checked.** Built the Task-2 end state (imports + `_gate_module` block + `parse_entries`
block) and ran the *only* self-test the plan provides for this file:

```
=== Task 2 Step 4 ('Expected: exit 0, no [FAIL] lines') ===
  rc= 1
  NameError: name 'unresolved' is not defined
```

**Actually true.** `unresolved` and `bucket_days` are Task **3**; `build`, `_bar` and `_ordered` are
Task **4**. The step's own bullet list names *"two `[resolved:]` flags on one header"* as a Task-2
case, and the assembled suite renders that bullet as two cases, one of which is
`case("two [resolved:] flags clear BOTH items", [x["id"] for x in unresolved(twin)], [])`.

This is the third instance of the defect round 2 filed twice — a step whose stated outcome cannot
occur at that point. The reorder eliminated the *file*-level version and left the *function*-level
one, which is why the Self-Review's answer (*"the gate is built first so no step depends on a file a
later task creates"*, plan:1444) is literally true and does not cover the case. The same gap sits at
Task 3 Step 1 (*"Write the failing tests"*, no block) and Task 4 Step 1 (*"the full assembled
`_self_test` is in Step 4"*). **VERIFIED.**

---

# Medium

## M1 — the entry title can be deleted from every entry and the suite stays green

**What I checked.** `f'<p class="title">{_html.escape(e["title"])}</p>'` → `f''`.

```
*** SURVIVED ***  N17 title not rendered in What changed        70/70 rc=0
```

**Actually true.** Spec §6.2 makes the title a named field (*"Title | the first non-blank line after
the header"*) and it is the only entry text rendered **outside** a `<details>` fold. Every assertion
that mentions a title passes on a copy elsewhere: `case("needs-you surfaces", "Decide the thing." in
html, True)` matches the "What needs you" link, and `_ordered`'s ordering assertions match the same
text inside `plain`. This is round-2 H5's shape (an assertion satisfied by the page's other copy)
surviving in the base cases that H5's `_section` fix did not touch. **VERIFIED.**

## M2 — `unresolved`'s error guard is untested, so a malformed entry can be listed as needing you

**What I checked.** `if e["needs_you"] and not e["error"] and …` → `if e["needs_you"] and …`.

```
*** SURVIVED ***  N20 needs-you entries with errors are surfaced anyway     70/70 rc=0
```

**Actually true.** `## 2026-08-28 [needs-you] [resolved: bogus]` parses with `needs_you=True` and a
non-None `error`; with the guard removed, "What needs you" gains
`<li><a href="#2026-08-28-1"></a> …` — an empty link, because `title` is unreliable when `error` is
set (the plan's own Interfaces section says so). The current code is right; nothing holds it there.
**VERIFIED.**

## M3 — the bar's HEIGHT — spec §5's defining statement — has no case

**What I checked.** `h = 4 if day["commits"] == 0 else max(6, round(48 * day["commits"] /
max(tallest,1)))` → `h = 10`.

```
*** SURVIVED ***  N21 bar height ignores commits      70/70 rc=0
```

**Actually true.** Spec §5 opens *"One bar per day. **Height = commits …**"*. Every bar could render
at a constant height and the suite would certify it. `case("commit count", days[0]["commits"], 2)`
tests `bucket_days`, not the rendering. The Self-Review §5 row claims ✅ on *"buckets, oldest-left
direction, the under-count sentence, and the bar→entry anchor"* — height is not among the four, and
it is the one §5 states first. **VERIFIED.**

## M4 — `_ordered`'s docstring cites a step that says something else, in code that ships

**Quoted claim (plan:741-742):** *"the store is written newest-at-the-END (**Task 1 Step 7,
"Append one block"**)"*.

**What I checked.** Task 1 Step 7 (plan:474-479) is **"Step 7: Commit"** — `git add
scripts/check-dashboard-entry.py`. The store is created at **Task 2 Step 5**, and the string
"Append one block" appears nowhere in the plan.

**Actually true.** The reorder moved the store and this docstring kept the old coordinates. It is a
comment inside code the plan instructs an implementer to paste, against the plan's own Global
Constraint *"Bare citations are a defect. Every path written into code comments or page output is
repo-relative and complete."* A step number in another document is the least durable citation
available; the docstring should name `docs/dashboard-entries.md`'s own header line, which states the
rule and travels with the file. **VERIFIED.**

## M5 — acceptance criterion 5 names no observation that could fail it

**Quoted claim (plan:1400):** *"5. Both `--self-test`s pass **and** their mutation checks were run."*

**Actually true.** *"Were run"* is satisfied by running them and ignoring the result. On today's
suite that criterion is tickable while a mutation the plan itself names survives (H1). The repo's
own rule is explicit — `CLAUDE.md`, *"State the observation that would make it FAIL. If none can be
named, it is a decision or an investigation wearing a checkbox"* — and `scripts/check-gate-
falsifiability.py` runs in CI for exactly this. The falsifiable form is *"every mutation named in
Task 4 Step 4 was caught"*, which is the assertion that goes red. Criteria 1–4 are all observable.
**VERIFIED.**

## M6 — spec §9's first observable is not built, has no case, and the §9 row carries ✅

**Quoted claim (Self-Review, plan:1422):** *"§9 checks | Tasks 1, 4, 5 | ✅ **including the
commits-with-no-entry alarm**, which v2 marked ✅ without building"*.

**Spec §9's five observables**, in order: *"the page names the last date an entry was written"* ·
every day with commits and no entry is marked · what-needs-you present or could-not-tell · a
resolved item leaves §4 · every fold survives a reload.

**What I checked.** `grep` for any "last entry"/"last written" statement in `build`; searched the
self-test for a case asserting one.

**Actually true.** Nothing states it and nothing asserts it. The newest entry's date is rendered in
its `<h3>`, so a reader who knows the ordering can infer it — but *"the date is rendered somewhere
on the page"* is precisely the argument round 2's H2 rejected for the bars, and the same standard
should apply to the row above it. One `<p>` and one case. **VERIFIED** (absence, by search).

## M7 — the §9 alarm marks every pre-store day, so the first render is a wall of alarms

**What I checked.** `unwritten = day["commits"] > 0 and not day["has_entry"]`, with `has_entry`
derived from the store. On the day the store is created it holds one entry.

**Actually true.** With a 14-day default window and a store one day old, thirteen of fourteen bars
render hatched-red with *"SHIPPED WITH NO ENTRY"*. The alarm is correct per its definition and
useless per its purpose: a mark that is on almost everything the first time it is seen trains the
reader to stop reading it, which is the one failure mode an alarm cannot survive. Neither the plan
nor spec §7.3 says what happens to days before the store existed. The cheapest fix is a floor — do
not mark days earlier than the store's first entry — and it needs one case. **VERIFIED** by
derivation from the two definitions; not run against a real 14-day window, since `commit_dates` has
no implementation (B2). **INFERRED** for the exact bar count.

---

# Low

**L1 — the gate's final `__main__` dispatch is never stated.** Task 1 Step 1 says to write
`if __name__ == "__main__": sys.exit(_self_test())`; Step 5 adds `main` and never says to switch.
Left as written, `--base` and `--pr-body-file` are unreachable and the CI ratchet would run the
self-test and always pass. Self-correcting: Control A goes green and the step says to stop. State
the line anyway — it is one line, and the failure it prevents is a gate that always passes.
**VERIFIED** (absence, by search).

**L2 — `_ordered`'s `-p[0]` sort component is dead.** `sorted` is stable, so with `reverse=True` and
key `(date,)` equal dates already keep input order. Dropping it is a semantic no-op:

```
*** SURVIVED ***  M12 _ordered: break tie order (drop -p[0])
```

The survivor is correct here — the mutation changes nothing — but the term reads as load-bearing and
the case named *"same-date ties keep file order"* cannot distinguish the two. **VERIFIED.**

**L3 — `exemption_reason` refuses three declarations Markdown renders as VISIBLE.** Measured:

```
blockquoted                   '> NO-ENTRY: quoted\n'         -> None
lazy continuation, 4 spaces   'text\n    NO-ENTRY: cont\n'   -> None
4 spaces after a closed comment '<!-- c -->    NO-ENTRY: x'  -> None
```

An indented code block cannot interrupt a paragraph, so case 2 renders as visible text; a blockquote
is visible by definition. All three fail **closed** (over-refuse), which is the safe direction — but
the docstring's stated rule is *"anything a Markdown reader treats as inert does not count"*, and
these are not inert. Describe what the code does, or fix the code. **VERIFIED.**

**L4 — the hover text, the aria-label and the `.vh` span each have no case.** Deleting `title=`,
`aria-label=` or `<span class="vh">` individually leaves 70/70. `_marks` excludes them deliberately
and says so, which is right for the §6.1 comparison — but it leaves the screen-reader path with no
assertion of any kind, in a page whose §6.1 argument is about what a reader can perceive.
**VERIFIED.**

**L5 — a stale cross-reference in the Round-2 table.** Plan:1546 says the `no_entry_prs` check
*"moved to **Task 4 Step 6a**"*. There is no Step 6a in v3; Task 3 Step 2's own ⛔ note correctly
says Task 6 Step 5. Historical section, but it is the pointer a reader follows. **VERIFIED.**

**L6 — a duplicated `[resolved:]` is silently accepted.** `[resolved: X] [resolved: X]` yields
`resolves=['X','X']`, no error. Harmless — `cleared` is a set — but §6.2's *"zero or more"* has now
been read as "a list", and a duplicate is the one case where the list's extra element means nothing.
**VERIFIED.**

**L7 — the `33/33 symbols byte-identical` line cannot be checked and does not reconcile.** The
executed files are not committed, so *byte-identical* has no referent. An `ast` parse of the plan's
eleven Python blocks gives 32 top-level definitions, 27 unique, 34 counting the two prose constants.
Drop the line; the reproducible claim is the one this review re-ran — assemble by line range and the
suites come out at 42/42 and 70/70. **VERIFIED.**

---

# What I checked and found SOUND

Recorded so the next round does not re-spend the time.

| Claim | Result |
|---|---|
| **Controls A–F, verbatim** | All six behave exactly as the required-output block states, including D's `+## not-a-date` grep and the five previously-waved-through shapes at `rc=1`. `set -e`'s absence and D's `mkdir -p docs` both matter as the plan says |
| **Task 1 Step 2's intermediate state** | Raises `NotImplementedError`, not `NameError`. Round 2's B2 is genuinely fixed for the gate |
| **`fetch-depth: 0`** | Reproduced both halves in scratch repos with a synthesised `refs/pull/1/merge`. Depth-1: `origin/master MISSING`, `ratchet_rc=2`, `CANNOT RUN`. Full: `origin/master YES`, merge-base resolves, diff is the PR's files, `ratchet_rc=1`. The fix works |
| **The cost of `fetch-depth: 0`** | Measured locally: `.git` 8.3M → 12M (**+3.7MB**), clone 1.50s → 2.34s (**+0.85s**). The plan's "~1.2s and ~4MB" is honest |
| **"nothing else in CI reads git history"** | True. `check-roadmap-consistency.py` imports `subprocess` and never calls it; the other three hits are comments |
| **The CI step's shell safety** | `printf '%s' "$BODY"` puts the body in the format *argument*, so `%` in a PR body is inert. Correct |
| **`fetch-depth: 0` and a slashed base ref** | Moot here: `ci.yml:14-18` restricts `pull_request` to `branches: [master]`, so `GITHUB_BASE_REF` is always `master`. Fork PRs still see `origin/*` from the base repo |
| **Repo-file citations** | `check-explainer-delivery.py:46` = `SKILLS = ROOT / ".agents" / "skills"` ✓ · `:53` = `PAGE_SKILLS` ✓ · `gen-goals-page.py:487-498` = the compose-and-fail-loudly block ✓ · `:457` = `--self-test` ✓ · `check-function-revokes.py:113` ✓ |
| **`.claude/settings.json`** | The `PostToolUse` → `"Edit|Write"` array exists with `regen-goals-page.sh` in it, as Task 6 Step 4 describes |
| **Line budget** | `docs/dev-process.md` is **214 / 220**; two pointer rows leave 216. The ⚠ to re-measure is right and the addition fits |
| **No `.github/PULL_REQUEST_TEMPLATE`** | Confirmed — `.github/` contains only `workflows/` |
| **1,398 commits on master** | Confirmed (415 first-parent) |
| **Task 2 Step 6's expected output** | The store block parses to exactly `1 entries; [None]`, title and tech both correct |
| **`_ordered` under every ordering** | malformed first / last / middle / two consecutive / entirely malformed / ties across dates / newest-first file — all render adjacent to a file neighbour, matching the docstring. Two mutations (append-at-end, drop the reverse) are caught |
| **`resolves` as a list** | Two, three, duplicated and self-referential flags all behave; a valid-then-bogus pair is still caught; a malformed entry cannot clear anything |
| **`exemption_reason`, everything except fence length** | Fence-in-comment, comment-in-fence, unclosed comment inside a fence, indented-4 fence opener, info strings, CRLF, tabs, form feed, vertical tab, NBSP, mid-line markers — all correct. Eight gate mutations, all caught |
| **`RELOAD_JS` placement** | `explainer-serve.py:668` appends it after the body, so `restoreDetails()` runs with the `<details>` already parsed. `case(name, fn)` at `:761` matches Task 5 Step 3's lambda signature |
| **Mutation coverage generally** | 49 of 59 mutations caught, including all eight on the gate and the four the plan's Self-Review calls out as previously vacuous (glossary content, both bar marks together, the `gh` half of §4, the CRLF removal) |

The suite is strong. Every finding above is a hole in a net that is otherwise unusually tight, and
five of the six must-changes are one function, one import block, or one case.

---

## On the shape of what round 3 found

Four of the six must-changes are the **same defect class as the previous round's fix, applied to the
sibling the fix did not reach**: the imports (fixed for the gate, shipped for the parser), the day
anchors (half the round-2 finding fixed), the fence rule (character fixed, length not asked), and
pass 2's diagnostic (fixed for one of the two malformed shapes). The plan's own memory names this —
*"answer 'what else is this true of?' with a grep, not a recollection"* — and it is now the dominant
shape across three rounds. That is a stronger signal than any individual finding: the fixes are
correct and they are being scoped to the instance that was demonstrated.

The other constant is that **the evidence block is the least reliable part of the document.** `19/19
caught` is false, `33 symbols byte-identical` is uncheckable, and `The finished function is shown`
describes a function that is not there. Everything the plan says about *code* reproduced exactly;
everything it says about *its own verification* did not. If one thing changes for v4, it should be
that the Standing Evidence block is regenerated by a script that runs the mutations, rather than
written by the person who ran them.

**NOT CONVERGED**
