# Adversarial review — dashboard "ask choices" design spec, ROUND 2 (Claude half)

**Subject:** `docs/superpowers/specs/2026-08-31-dashboard-ask-choices-design.md` **v2**, commit
`3158e99`, branch `feat/dashboard-ask-choices`.
**Reviewer:** Claude (the Claude half of the dual gate). **Date:** 2026-08-31.
**Focus, per the brief:** §8a's rewritten gate seam, §11's cutover, §7's fourth row, §9's rewritten
falsifiers — i.e. the material written to fix round 1 and reviewed by nobody.

Every code claim below was verified by opening the file, and every behavioural claim by running it.
Commands and outputs are quoted where they are load-bearing.

---

## Blocking

### B1 — §8a: "`collect()` returns the added entry ids" has no derivation. An id cannot be computed from the patch, and cannot be matched to the working tree. **REGRESSION INTRODUCED BY THE ROUND-1 FIX.**

**Where:** spec §8a; `scripts/gen-dashboard.py:366-368`; parent spec §6.2 ("Entry id" and "Id
assignment is unchanged"); `scripts/check-dashboard-entry.py:241-254`.

**What is wrong.** An entry id is a *positional ordinal within its date, in file order*:

```python
seen[date] = seen.get(date, 0) + 1
entry["id"] = f"{date}/{seen[date]}"        # gen-dashboard.py:366-368
```

`collect()` runs `git diff -U0 {base}...HEAD -- docs/dashboard-entries.md` (`:245-247`). That patch
contains the added header line — `+## 2026-08-31 [needs-you]` — and nothing about how many entries
of that date precede it in the file. **The ordinal is not in the patch, so the id is not derivable
from it.** The spec asserts the return value without naming a mechanism that can produce it.

The obvious repair — parse the working tree and match added header lines by text — does not work
either, because header lines are not unique. Measured against the live store:

```
$ grep "^## " docs/dashboard-entries.md | sort | uniq -c | sort -rn | head -4
  14 ## 2026-08-29
   4 ## 2026-08-30
   2 ## 2026-08-31
   2 ## 2026-08-30 [needs-you]
```

Fourteen entries share one header line. A diff that adds a fifteenth `## 2026-08-29` gives the gate a
string that matches fourteen existing working-tree entries and the new one, with nothing to
discriminate. The gate would then validate an arbitrary entry — plausibly a grandfathered one, whose
`decision_errors` list is non-empty by construction — and refuse the branch naming an entry the
author did not write.

**And the two sources are read at different revisions.** `.github/workflows/ci.yml:39-41` uses
`actions/checkout@v4` on a `pull_request` event, which checks out the **merge ref**, not the PR head.
So in CI the working tree is *the branch merged into base*, while the diff is
`origin/$GITHUB_BASE_REF...HEAD`. If another branch merged an entry with the same date while this PR
was open, the merge tree renumbers this branch's entry: the id computed from the working tree is not
the id the entry has on the branch, and — because a standing `[resolved: <id>]` points at a
positional ordinal — is not necessarily even the same entry. The spec says "the working tree" without
saying *which* working tree, and in the one caller that matters it is not the branch's.

**Why it matters.** The whole point of the round-1 rewrite was to give the gate a body to validate.
It now has a body it cannot reliably associate with the entry the diff added, in a gate whose failure
mode is refusing an honest branch or passing a broken one.

**Suggested fix:** drop ids from the seam — have `collect()` return the *added entry blocks* (the
contiguous runs of `+` lines, which the patch does contain, see H1), and validate those; if an id is
wanted for the message, compute it from the same tree the diff was taken against (`git show
HEAD:docs/dashboard-entries.md`), never from an ambient working tree.

---

### B2 — §8a: "parses it with the shared parser" inverts the dependency arrow the code forbids, and the reciprocal import does not terminate. **REGRESSION INTRODUCED BY THE ROUND-1 FIX.**

**Where:** spec §8a, §8 ("one validator, two callers"); `scripts/gen-dashboard.py:294-312`;
`scripts/check-dashboard-entry.py:24`.

**What is wrong.** `parse_entries` lives in `gen-dashboard.py:339`. The gate imports nothing; the
arrow runs generator → gate, and the generator says so explicitly:

```python
"""Load scripts/check-dashboard-entry.py for the grammar it owns.

The dependency arrow points generator -> gate, never the reverse: a GATE
must not import the thing it guards, but a page importing a gate is what
keeps their readings identical by construction. ...
"""                                        # gen-dashboard.py:294-301
_GATE = _gate_module()          # the GRAMMAR is required to parse at all  (:312)
```

§8a asks the gate to parse the store "with the shared parser". Taken literally that is
gate → generator, i.e. the gate importing the artifact it guards.

**It is not merely stylistic — it does not run.** `_gate_module()` never registers its module in
`sys.modules`, so a reciprocal module-level import re-execs each file endlessly. Measured, using
copies of the real loader shape:

```
$ python3 …/cyc/scripts/… (gate.py imports gen.py at module level; gen.py keeps line 312)
RecursionError: maximum recursion depth exceeded
```

A lazy, in-function import in the gate would terminate — but at the cost of two distinct module
objects holding two reads of the grammar, which is precisely the hazard `_exemption_reader`'s
docstring (`:330-335`) exists to avoid.

**Why it matters.** §8's stated principle is "one implementation, two callers"; the spec picked the
one arrangement that cannot deliver it. The spec also never says where `parse_entries` should live,
so a plan written from v2 will discover this at the first import.

**Suggested fix:** state it outright — `parse_entries` (and the entry-id rule) **moves into
`check-dashboard-entry.py`** alongside `HEADER`/`FLAG`/`header_error`, and `gen-dashboard.py` imports
it exactly as it already imports the grammar; the arrow stays generator → gate.

---

### B3 — §7's fourth row is an outcome with no mechanism, and it contradicts §8b in the same document.

**Where:** spec §7 (row 4), §5c, §8b; `scripts/gen-dashboard.py:439-451`, `:691-716`, `:759-764`.

**What is wrong.** §7 promises: *"the tray renders 'could not read one ask', naming the entry id."*
Every path that could carry that string is closed by the design in §8b:

- §8b routes a decision-block failure through `entry["error"]` (`parse_entries` sets it).
- `unresolved()` returns `[e for e in entries if e["needs_you"] and not e["error"] …]` (`:450-451`) —
  the errored entry is gone.
- `build` derives its rows solely from that list: `need = unresolved(entries)` (`:691`), `rows = […
  for e in need]` (`:692-694`).
- With `rows` empty and `store_error` `None`, `build` reaches
  `'<p class="none">Nothing needs you.</p>'` (`:716`).

§5c independently says a malformed entry gets **"no badge; *'Could not parse this entry'*
— unchanged"**, which is the entry-card treatment, not a tray note. So §5c and §8b specify the
behaviour §7 forbids, and §7 names no third input — no new `build` parameter, no `ask_errors` list,
no change to `unresolved`. The spec diagnoses the trap in a ⚠ box and then does not fit a mechanism.

**Why it matters.** §7 is the section that exists because "cannot run is a failure". As written, a
plan implementing §8b faithfully produces the exact defect §7 calls *"§1a, rebuilt by its own fix"* —
and it will pass §9's "Malformed ask is louder, not quieter" only if someone invents the missing
seam.

**Suggested fix:** name the seam — `build` gains an `ask_errors: list[tuple[id, str]]` parameter
(no default, like `store`/`store_error` at `:684-689`), populated from entries whose error came from
`decision_errors`, and rendered above `rows` so the tray can never be empty while one exists.

---

## High

### H1 — §8a's stated premise is false: with `-U0` the added entry body **is** in the patch. Measured. **REGRESSION INTRODUCED BY THE ROUND-1 FIX** (it is the justification the whole rewrite rests on).

**Where:** spec §8a: *"With zero context lines the entry **body is not in the patch at all**. There is
no `plain` to pass."*

**What is wrong.** `-U0` suppresses *context* lines. An appended entry is entirely additions, so
every line of it appears with a leading `+`. Measured on the last commit that appended one:

```
$ git diff -U0 7183111~1...7183111 -- docs/dashboard-entries.md | head -12
@@ -973,0 +974,38 @@ contrast guard checking the OLD palettes while reporting green.
+
+## 2026-08-31
+Every page this project generates now has a light/dark switch and tells you when — and from what — it
+was built. …
```

38 added lines: header, prose, `<!--tech-->` and all. The `plain` half is the added lines before the
marker, and it is right there.

**Why it matters.** v1's real defect was narrower than stated — `collect()` *discards* the body by
reducing the patch to a boolean, not that the body is unavailable. Round 1 fixed a wrongly-stated
cause, and the fix chosen because of it (read an ambient working tree at a different revision) is
what produced B1. This project's own memory names the shape: *the control refuted the premise*.

**Suggested fix:** correct §8a's sentence, and reconsider the cheaper design it rules out —
`collect()` returns the added blocks straight from the patch, which needs no second revision, no
ordinal, and no text-matching.

### H2 — the gate can pass having validated nothing: an entry-only branch returns success before any decision check runs.

**Where:** spec §8a ("Ordering with `NO-ENTRY:`" discusses only the exemption branch);
`scripts/check-dashboard-entry.py:145-148`, `:21`, `:183`.

**What is wrong.** `verdict` short-circuits *above* both the added-entry branch and the exemption
branch:

```python
real = [p for p in changed if not _is_exempt(p)]
if not real:
    return 0, "no tracked files changed outside the exempt paths"   # :146-148
```

`docs/dashboard-entries.md` is in `EXEMPT_FILES` (`:21`), and the self-test pins the behaviour:
`case("entry-only branch is exempt", verdict(["docs/dashboard-entries.md"], False, "")[0], 0)`
(`:183`). So a branch that changes **only** the store — adding a `[needs-you]` entry with a broken or
absent decision block — never reaches the validation §8a adds. §8a states "`verdict()` fails when any
added entry's list is non-empty" without touching this ordering.

There is a second, larger hole around the same gate: it runs only
`if: github.event_name == 'pull_request'` (`ci.yml:252-253`), while `.agents/skills/dashboard/SKILL.md:8,76`
appends the entry and regenerates the page immediately (with a `PostToolUse` hook doing it
automatically, `:87`). **The reader sees the page long before the gate sees the branch.** The gate is
therefore not the mechanism that keeps a malformed ask off the page — B3's tray note is.

**Why it matters.** §9's "Gate sees bodies" falsifier is satisfied by a fixture that also touches
`lib/x.ts`, so it goes green while the entry-only path stays fail-open — a falsifier that passes over
the live hole.

**Suggested fix:** state in §8a that decision validation runs on *added entries* regardless of whether
any non-exempt file changed, and add a §9 row: *fails if a branch changing only
`docs/dashboard-entries.md` with a malformed decision block passes.*

### H3 — §11's cutover date is a literal nobody can know when it is written, keyed on a field the author controls. **REGRESSION INTRODUCED BY THE ROUND-1 FIX.**

**Where:** spec §11 (*"the cutover date, which is the date this change merges"*), §12 row 6, §9 row 1.

Three separate defects in one rule:

1. **It is not knowable at authoring time, and merging is a human gate.** Whoever writes the constant
   guesses a date. If the merge slips two days, every entry written in the gap — by the `/dashboard`
   skill, which appends daily — was authored under the old grammar and becomes retroactively subject
   to the new one the moment the branch lands. That is B1 (five broken entries) recurring, on a
   smaller store, with nobody watching. If the merge lands early, entries written under the new rule
   are silently grandfathered.
2. **§9's first falsifier cannot see that gap.** It asserts against *"the store at `7183111`"* — a
   commit that predates the branch. Entries added between `7183111` and the merge are outside the
   fixture, which is exactly the population at risk.
3. **The key is the author-written header date, not a commit date.** Nothing verifies the two agree.
   Writing `## 2026-08-30` today grandfathers an entry out of the grammar permanently, and no check in
   §9 would notice. A rule with a one-token opt-out is a convention, not a gate.

Also unstated: **where the constant lives.** The gate and the renderer both need it; two copies is the
drift this project has measured repeatedly.

**Suggested fix:** make the cutover a property of the *store*, not of the calendar — e.g. a
one-line sentinel appended to `docs/dashboard-entries.md` in this branch (`<!--decisions-required-from-here-->`),
so "before/after" is a position in the append-only file that no merge date and no authored date can
move; own it in `check-dashboard-entry.py` and import it into the renderer.

### H4 — §11 fixes the instance and asserts dormancy for the class: post-cutover, the `unwritten` false alarm and the pass-2 cascade both come back.

**Where:** spec §11 ⚠ box (*"the cutover is what keeps it dormant"*);
`scripts/gen-dashboard.py:458`, `:651`, `:418`, `:427-429`.

**What is wrong.** The ⚠ box is true of *today's* store and only of it. The mechanism is unchanged for
every future entry:

- `with_entry = {e["date"] for e in entries if not e["error"]}` (`:458`) → a day whose only entry
  carries a decision-block error has `has_entry` False;
- `unwritten = day["commits"] > 0 and not day["has_entry"] and not store_unknown` (`:651`) → that day
  renders **"SHIPPED WITH NO ENTRY"**, an alarm about a day that has an entry;
- it also drops out of `flagged` (`:459`, via `unresolved`), so the day loses its orange
  needs-you colour while a real ask is outstanding;
- and pass 2 cascades: `ids` is built from `not e["error"]` (`:418`), so a later
  `[resolved: <that id>]` fails with *"names an entry that could not be parsed"* (`:427-429`) —
  one typo breaks two cards, which is how three broken entries became five in §11's own measurement.

**Why it matters.** The cutover grandfathers the five entries that exist. It does nothing for the
sixth, and the spec's phrasing invites a reader to believe the coupling is handled. *"After fixing,
search for the class"* is this project's own rule.

**Suggested fix:** re-word §11 to say the coupling is live for post-cutover entries, and require that
`decision_errors` failures set a **separate** field (e.g. `entry["ask_error"]`) that the tray reads
(B3) and that `with_entry`/`ids`/`unresolved` do **not** treat as a parse failure.

### H5 — §5a's "rendered as ordinary markdown by the shared renderer, with no special-casing" is not achievable: the shared renderer has no lists.

**Where:** spec §5a ⚠ box; `scripts/page_markup.py` (whole file); `scripts/gen-dashboard.py:220`,
`:223-274`, `:774-776`.

**What is wrong.** `page_markup` is an **inline** renderer, and nothing else — its entire public
surface is `escape`, `safe_href`, `trim_url_tail`, `scan`, `render_inline`, `orphaned_delimiters`
(`:122-273`). `render_inline` is `escape` then `scan` (`:242-250`). There is no block layer: no `<ul>`,
no `<li>`, no line-level handling at all. The card's prose goes through `_prose`
(`gen-dashboard.py:223-274`), which splits on **blank lines only** (`:235`) and emits one `<p>` per
paragraph with `_inline(p)` — so the four lines of §4's own example

```
**Decide:** Merge the mutation-harness change
- merge PR #181 [recommended]
- hold it and tell me what to change
- close it unmerged
```

are one paragraph, and HTML collapses their newlines into spaces. The card renders a single run-on
line — `Decide: Merge the mutation-harness change - merge PR #181 [recommended] - hold it and tell me
what to change - close it unmerged` — with the `PR #181` unlinked, while §5a requires the tray to show
the same options as an unfolded list with the PR linked.

The very next sentence of §5a says *"the card must not silently render a **different** option list
from the tray's."* Under "no special-casing" it necessarily does.

**Why it matters.** This is the one place v2 specifies a *rendering* by asserting an existing
component's behaviour, and the assertion is wrong about the component. Round 1's fold record lists
this box as the fix for a Medium; the fix states a property the code does not have.

**Suggested fix:** either accept and *state* the degraded card rendering explicitly (with a §9 row
pinning it), or add list rendering to `page_markup` as its own scoped change — but do not describe the
current behaviour as equivalent to the tray's.

---

## Medium

### M1 — §6's "total budget" is not a number, so §9's bound falsifier cannot be evaluated.

**Where:** §6 ⚠ box; §9 row *"PR lookups are bounded"*; `gen-dashboard.py:490-503`.
§6 says the render is *"bounded by a total budget across all PR lookups"* and never says what the
budget is (seconds? calls? both?). §9 then asks whether a render *"exceeds the total budget"* — a
falsifier over an undefined quantity, which is the shape §9's own preamble sets out to remove.
Note also that `_gh_json`'s `timeout=30` is per call (`:495`), so a wall-clock budget smaller than 30s
can be blown by a single hung call and a call-count budget does not bound time at all.
**Fix:** state both — *at most 8 distinct PR lookups and at most 20s total per render, whichever binds
first.*

### M2 — §6's "no such PR" row cannot be distinguished from "gh failed" through `_gh_json`.

**Where:** §6 table rows 3 and 4; `gen-dashboard.py:498-499`.
`_gh_json` collapses every non-zero exit into one error string
(`f"gh exited {r.returncode}: {r.stderr…}"`). Measured:

```
$ gh pr view 999999 --json number,state
GraphQL: Could not resolve to a PullRequest with the number of 999999. (repository.pullRequest)
exit=1
```

Same shape as auth failure, rate limiting or no network. Rendering *"no such pull request"* therefore
requires matching stderr text, which the spec neither authorises nor describes — and getting it wrong
in the confident direction tells the reader a PR does not exist when `gh` merely could not be asked.
**Fix:** say explicitly that "no such pull request" is claimed **only** on a matched
`Could not resolve to a PullRequest` stderr, and everything else is "could not check".

### M3 — §4's "both categories at once is malformed" has no home in the specified validator signature.

**Where:** §4 last two rows; §8's `decision_errors(plain: str, category: str)`.
`decision_errors` receives the *body* and a *category*; it can enforce "a `heads-up` must not ask", but
it never sees the header, so it cannot detect `[needs-you] [heads-up]` on one line. That rule belongs
to `header_error`/`FLAG` (`check-dashboard-entry.py:37-54`), and the spec says nothing about extending
them for it — while §9 carries a falsifier ("One category per entry") that nothing is specified to
satisfy.
**Fix:** add one line to §8 — `header_error` gains the mutual-exclusion check; `decision_errors` owns
the body rules only.

### M4 — §9's "paired positive and negative fixture" is asserted over rows that cannot have a pair, and two rows are still one-sided.

**Where:** §9 preamble and rows 1, 2.
The preamble says **every** row requires a paired positive and negative fixture. Row 1 ("No historical
entry breaks") has no meaningful positive — its subject is a single real store at one commit — and row
2 ("Badge is derived") states only the failing observation. Nothing defines what "paired" means
operationally (same store with one line changed? two fixture files? one run of the generator or two?),
so two implementers will produce different things and both will claim compliance.
**Fix:** define the pair once — *"one fixture that violates the rule and must be reported, and one
minimally-different fixture that satisfies it and must be reported clean, both asserted on the
generator's own output string"* — and mark the rows where only one side exists, with the reason.

### M5 — the gate's new working-tree read has no cannot-run rule.

**Where:** §8a; `check-dashboard-entry.py:358-361`.
`main` has exactly one CANNOT RUN path, for `collect`'s git errors (`:358-361`, exit 2). §8a adds a
file read and says nothing about what happens when `docs/dashboard-entries.md` is missing, unreadable,
or parses to zero entries while the diff reported additions. Silence here defaults to whatever the
implementer writes, and the cheap default is "no entries to check → pass" — a gate that passes
loudest exactly when it saw nothing. The project rule is explicit: *"cannot run" is a FAILURE, never a
pass.*
**Fix:** one sentence in §8a — an unreadable store, or an added id with no matching entry, exits **2**
with `NOT CHECKED`.

### M6 — v2 is too large for one plan, and the user's reported defect is the smallest part of it.

**Where:** §2 scope; §11's closing paragraph.
Scope now spans: a new entry category, a new block grammar with six recognition rules, derived badges,
a new page section, live PR resolution over `gh`, a validator with two callers, a cutover regime, and
19 falsifiers plus mutation entries in two manifests. §11 states plainly that *"the grammar work
changes nothing on the page as it stands"* — meaning the defect the user actually reported (§1a, three
stale `needs you` badges) is closed entirely by §5c, which needs none of the grammar.
**Fix:** split — **(A)** §5c derived badges + §5d glossary (closes the reported defect, no grammar,
no cutover); **(B)** §4 grammar + §8 validator + §7's tray note + §11 cutover; **(C)** `heads-up` and
§5b "Worth knowing"; **(D)** §6 live PR state. A ships in a day and is independently verifiable.

---

## Low

### L1 — §8a repurposes `EXEMPT_FILES` as the store's location.
`EXEMPT_FILES` (`check-dashboard-entry.py:21`) means *"changing this file does not require an entry"*.
§8a reads it as *"here is where the store lives"* — two meanings on one tuple, so adding a second
exempt file, or moving the store, silently changes the other. **Fix:** a separate `STORE = ROOT /
"docs" / "dashboard-entries.md"` constant, with `EXEMPT_FILES` referring to it.

### L2 — a pre-cutover `needs-you` that is never resolved renders a choice-less ask forever, unmarked.
§11 grandfathers old entries; §5c keeps showing their `needs you` badge and the tray keeps listing
them. Today `unresolved` is `[]` so nothing is visible, but the design permits an ask with no options
to sit in the tray permanently with nothing saying it predates the grammar. **Fix:** one row in §5a —
a pre-cutover ask renders with a muted *"written before choices were required"* note.

### L3 — v2 is presented as a folded, reviewable version while carrying an open user decision.
§3's box, the header ⚠, §12 row 3 and §13 all record that the no-expiry justification was withdrawn
and the decision is open. Phase 1's gate is user approval of the spec; a round-3 fold cannot close
while a §12 row is open. **Fix:** put the expiry question to the user before the next round rather
than after it — it is one sentence and it blocks the section it sits in.

---

## What I tried that did *not* produce a finding

- **§3's replacement reasoning for "no expiry"** — checked whether it leans on anything unverified.
  It does not: *"absence and denial must not look alike"* is parent §4's own requirement, and *"a
  second answer to 'is this item finished with'"* is an argument from this design's own structure. It
  is sound without borrowed authority, and the box says so honestly.
- **§4's `FLAG` regex** — `re.compile(r"\[(needs-you|heads-up|resolved:\s*[^\]]*)\]")` is correctly
  escaped and composes with `header_error`'s `FLAG.sub("", …).strip()` leftover check
  (`check-dashboard-entry.py:51-53`); `[needs-yo]` still fails, per `:232`.
- **The `:369-383` `else`-branch warning** — re-read; accurate, and §4's ⚠ box requires the parser
  change in the same commit.
- **§4's `PR #N`-not-`#N` rule and §9's matching row** — consistent across §4, §6, §9 now.
- **`NO-ENTRY:` ordering in §8a** — correct as stated: `verdict` consults `exemption_reason` only on
  the `added_entry`-false branch (`:151-158`), so an exemption branch is genuinely unaffected. (The
  ordering problem is one branch *above* it — H2.)
- **Contradiction with the parent spec** — none found in §4/§5/§6.2/§7 beyond what v2 already records
  (the title first-line/first-sentence divergence, §13's last row). The chart-colour rule and the
  `[resolved:]` semantics are preserved.

---

## Verdict

**NOT CONVERGED** — 3 Blocking, 5 High, 6 Medium, 3 Low. **Four of the eight Blocking/High findings
are regressions introduced by the round-1 fix** (B1, B2, B3 and H1 all live inside §8a/§7's new
material; H3 lives inside §11's).

The pattern is worth naming for round 3: round 1 correctly identified that the gate had no body to
validate, mis-stated the *cause* (H1 — the body is in the patch), and repaired it by reaching for a
second source of truth at a different revision. Every Blocking above is a consequence of that reach.
The cheapest route back is to validate the added blocks the patch already carries, and to move
`parse_entries` into the gate so "one validator, two callers" points the way the code already does.
