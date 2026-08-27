# Adversarial review — PR #102 `docs/premise-discipline` (Claude half)

**Subject:** working tree at `docs/premise-discipline` (`6c763cd`), diffed against `master` (`2c56045`).
**Date:** 2026-08-14.
**Verdict: NOT CONVERGED — 1 Blocking, 3 High, 3 Medium, 3 Low.**

Everything below was run, not reasoned about. Commands and their output are quoted.

---

## Summary

| Severity | Count |
|---|---|
| Blocking | 1 |
| High | 3 |
| Medium | 3 |
| Low | 3 |

The script is well-built for what it does and its docstring is unusually honest about its limits. The
Blocking is not that it is careless — it is that the thing it can see (a heading word) and the thing
it must catch (a premise stated as a fact) are almost disjoint, and I demonstrated that on the real
artifact rather than a contrived one.

**The thesis is not wrong, but it is a minority explanation stated as the explanation, and the
project's own Phase 6 review contradicts its emphasis one day earlier.** See H3.

---

## BLOCKING

### B1 — The ratchet passes on the very spec it was written for, with all five premises untagged

The brief asked for a spec that passes while carrying an untagged load-bearing premise. I did not
have to invent one. **The #36 spec itself passes after a one-line edit that the script's own error
message invites.**

The #36 spec lives at `docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md` on branch
`fix/cloud-blob-key-encoding`, which is **not an ancestor of this PR** (`git merge-base --is-ancestor
4054928 HEAD` → false). I extracted all eight versions and audited each.

On v1 — the version carrying all five premises — the script reports exactly one violation:

```
spec-v1.md: violations=['premise section carries no tag: ## 2. What was measured']
```

That looks like a hit. It is not. **The premises are not in that section.** `## 2. What was measured`
has a body of **174 characters**, and it is entirely about probe hygiene:

> All storage probes ran against the **local** Supabase stack. Each probe script refuses to run unless
> the URL is `127.0.0.1`/`localhost`, and cleans up the objects it wrote.

The five premises live in `### 2.1` … `### 2.6` and `### 3.3` (`spec-v1.md:48,67,93,106,119,149,212`),
none of which match `PREMISE_HEADING_RE` (`scripts/check-premises.py:57`), because `sections()`
(`:64-75`) ends a section at the next heading of **any** level. So the one violation reported is
against a paragraph containing no premise, and the six subsections containing every premise are never
audited.

Now do what the error message asks — put a tag in the flagged section:

```
BEFORE: ['premise section carries no tag: ## 2. What was measured']
AFTER : NO VIOLATIONS -> PASSES
  untagged lines still mentioning '267': 7
  untagged lines still mentioning 'invert the encoding': 1
  untagged lines still mentioning '149': 4
```

The added tag was `[VERIFIED: scripts/probe-storage-charset.ts:12]` appended to the sentence about
cleaning up objects. Verified end-to-end through the **real globs and the real script**, by copying
the patched spec into `docs/superpowers/specs/`:

```
untagged/unsafe premises: 0  baseline: 0
COVERAGE: 1/80 specs have a premise section.
exit=0
```

Exit 0, with the 267-character premise that cost rounds 3–7 sitting untagged seven lines below.

**Five further bypasses, all confirmed passing** (`audit()` returns `[]`):

| # | Shape | Why it escapes |
|---|---|---|
| A | `## Assumptions` heading | not in `PREMISE_HEADING_RE`'s vocabulary |
| B | `[ASSUMPTION]` in `## Premises`, the fence in `## Design` | rule 2 (`:90-92`) is **section-scoped** |
| C | `## Background` / `## Constraints` / `## Prior art` | not in the vocabulary |
| D | premise table, one tagged row, nine untagged | one `VERIFIED_RE` hit satisfies the whole section |
| E | tag appearing in an unrelated sentence | same — `VERIFIED_RE.search(body)` is existential |

Case **A** is the sharpest: the most natural heading for a premises section is **`## Assumptions`**,
and it is not recognised. Case **B** is the most consequential: `review-method.md`'s actual rule is
*"a safety fence, credential, or invariant may not be designed on an `[ASSUMPTION]`"* — and a
well-structured spec states assumptions in a table and builds on them elsewhere, which is precisely
the layout the check cannot see. The rule fires only on the **badly**-structured spec that puts both
in one section.

Accepted heading vocabulary, enumerated:

```
miss  ## Assumptions      miss  ## Constraints    miss  ## Background
miss  ## Facts            miss  ## Given          miss  ## Invariants
miss  ## Prerequisites    miss  ## Ground truth   miss  ##### Premises   miss  # Premises
MATCH ## Premises         MATCH ## What was measured
```

**Why Blocking.** Per the brief and `CLAUDE.md`: a green check over the wrong subject is worse than no
check. This one will be green on any spec whose author does not volunteer the word "premise" — and the
defect class it targets is *"written as a fact rather than as a premise"* (`portable-practices.md`
entry 11), i.e. exactly the author who would not write that heading.

**Repair options** (the cheapest first; this is a judgment call for the author):
1. Make the premise section **mandatory** rather than conditional — a Phase-1 spec with no premise
   section is a violation, not a pass. That converts the script from "check the labelled part" to
   "check the spec", and it is the only version of this that binds.
2. Tag-per-**row/claim**, not per section: require every row of a premise table to carry a tag.
3. Make rule 2 document-scoped, not section-scoped.
4. Widen the vocabulary to include `assumptions|constraints|background|invariants|prerequisites`.

(4) alone is not sufficient — D and E survive it.

---

## HIGH

### H1 — Rule 1 violated: a run that measures nothing exits 0

`docs/process-checklists.md:271` — *"'Cannot run' is a FAILURE, never a pass. The single most
important line here."* The script honours this per-file (`:112-114`, `OSError` → `sys.exit(1)`), but
not for the case where the globs match nothing:

```
scanned=0 covered=0 violations={}
main() exit code = 0   <-- PASS while measuring NOTHING
```

Rename `docs/superpowers/specs/` or `docs/design-spec.md` and this ratchet reports success forever,
silently. Compare `check-ratchet-contract.py:192`, which handles exactly this — *"FAILED: discovered
ZERO ratchets, which cannot be right. Treat this as NOT RUN."*

The weaker form is live **today**. The real run is:

```
untagged/unsafe premises: 0  baseline: 0
COVERAGE: 0/78 specs have a premise section.
  ⚠ This ratchet is almost entirely INERT on the existing corpus.
exit=0
```

The coverage figure is computed and printed, and the docstring at `:99-104` explains precisely why it
matters — but **it never gates anything**. It is advisory prose inside a script whose reason for
existing is that advisory prose does not fire. `portable-practices.md` §2, which entry 11 itself
cites, is the rule being broken.

Suggested: exit 1 when `scanned == 0`; and treat `covered == 0` as at minimum a distinct, non-green
status rather than a print.

### H2 — "It survived two rounds" is false; it was caught in round 1

`docs/review-method.md` (added by this PR) states of the 267-character premise:

> The number was recorded in a section titled *What was measured* and used to eliminate three design
> alternatives. **It survived two rounds.**

And `portable-practices.md` entry 11's table bills it at *"eliminated 3 alternatives, ~2 rounds"*.

Both are wrong. It was caught by the **first** reviewer in the **first** round, with a counter-measurement
(`spec-blob-key-encoding-r1-claude.md:23`):

> | H2 | High | §2.2's measured bound is wrong. The limit is **255 characters per path segment**, not
> 267 for the whole path — and the wrong number is the *only* recorded reason for rejecting the
> reversible encodings, one of which measurably fits |

and at `:241,263`, an independent probe:

```
seg 255 + seg 10  (total 306 chars)   -> accepted
seg 256 + seg 10  (total 307 chars)   -> REJECTED 500
four segs of 200 each (total 843)     -> accepted
```

It was corrected in the immediately following spec version. Occurrences of `267` and `255` per version:

| | v1 | v2 | v3 | v4 | v5 | v6 | v7 | v8 |
|---|---|---|---|---|---|---|---|---|
| `267` | 7 | 3 | 3 | 3 | 2 | 2 | 2 | 0 |
| `255` | 1 | 18 | 19 | 19 | 9 | 9 | 9 | 0 |

v2 retitles the section *"§2.2 The length limit — 255 characters per SEGMENT"* (`spec-v2.md:77`) and
annotates the correction in place (`:79`). The premise survived **one** spec version and **zero**
review rounds beyond the first opportunity to catch it.

**Why this is High rather than a typo.** This is the worked example the PR uses to teach *"could this
experiment have returned the other answer?"* A document teaching measurement discipline, misstating by
2× how long its own exemplar survived, in the direction that makes its case stronger, is the failure
mode it is about. It also matters for the thesis: for P1 the review process performed **optimally** —
first pass, immediate correction — which is evidence against, not for, "the rule never fired".

**And P1 is not the only wrong row.** Entry 11 bills P4 (*"the store needs ASCII-safe keys"*) at
**"rounds 3–7 entirely"**. The reviews' own verdict paragraphs say rounds 5–7 were about something
else — a repeatedly-missed **write entrance**:

- `spec-blob-key-encoding-r5-claude.md:6,16-17` — *"1 Blocking, 5 High"* … *"What it did not fix is the
  pattern that produced the last four rounds: **the spec keeps enumerating the write entrances and
  keeps missing one**, and **the rows it nominates as its own falsifiers cannot be constructed from the
  inputs they name**."*
- `spec-blob-key-encoding-r6-claude.md:6,9,12,14` — *"**Everything v6 changed, it changed correctly.**
  … **If the finding below were absent I would say CONVERGED.** It is not absent. There is a **fourth
  write entrance** — `reconcileCloudBase`."*
- `spec-blob-key-encoding-r7-claude.md:6,8` — *"the branded type does not do the thing §3.5.1 says it
  does … it enumerates *calls to the branded function*, not *writes of a summary key*. A fifth entrance
  compiles clean."*

Round 6 states in terms that it would have converged but for the fourth write entrance — which has
nothing to do with ASCII-safety.

I then enumerated every Blocking and High across all 15 review files (per-file counts reconcile with
each Claude review's own headline verdict line, so they are checkable). **Total Blocking+High = 34**
(16 B, 18 H), excluding `r5-codex-STALE-v4-brief.md` which the corpus itself adjudicates out at `:76`
(*"⚠ ADJUDICATION — THIS REVIEW DOES NOT APPLY TO v5"*). Row by row against entry 11's table:

| | Claimed cost | Blocking/High findings whose stated root it is | Status |
|---|---|---|---|
| P1 267-char limit | "3 alternatives, ~2 rounds" | 1 — `r1-claude:23` | **contradicted**: round 1, and `r1-claude:287` says *"This does **not** make §3's design wrong"* — zero design churn |
| P2 `list()` inversion | "~1 round" | **0** | not corroborated — its only findings are Medium (`r1-codex:63`) and Low (`r1-claude:29`) |
| P3 `readdir` | "wrong fix to a Blocking" | **0** | not corroborated — no review states this premise |
| P4 ASCII-safe keys | "rounds 3–7 entirely" | 2 — `r2-claude:27`, `r4-claude:66` | **contradicted**: first appears round **2**, and rounds 5–7 are the write-entrance pattern |
| P5 branded type | "the whole scope decision" | 2 — `r7-claude:113`, `r7-codex:3` | corroborated as a defect, but see below |

**Strict ratio: 5 of 34 Blocking+High findings (14.7%) have a P1–P5 premise as their stated root.** A
deliberately generous upper bound — counting every finding whose *consequence* is the P4 servability
shape (`r3-codex` B, `r5-claude` B1, `r5-claude` H3, `r6-claude` B1, `r6-codex` B) — reaches **10/34
(29.4%)**. Either way, **≥70% are ordinary defects**, and the strict figure is roughly 5× smaller than
"seven rounds" implies.

**P5 also breaks the PR's own sentence** *"each a full round after the design had been built on it"*.
The branded type was a **reviewer's recommendation** (`r6-claude:128-130` — *"A branded
`CloudSummaryKey` type constructed only by the validator is the same idea enforced by `tsc`"*), adopted
in v7 and refuted in round 7 — the first round in which it existed. More pointedly: **the instrument
this PR proposes could not have caught P5**, because the premise did not enter the spec from the author
writing it. An author-side authoring-time tag has no purchase on a premise arriving in a review
finding.

**A better lesson is sitting in that evidence and the PR does not draw it.** Rounds 5, 6 and 7 are one
failure repeated: a **hand-maintained enumeration** of write entrances that was wrong three times, and
whose attempted fix (the branded type) was *itself* an enumeration overclaim. That is the same shape as
`portable-practices.md`'s own *"write entries by ENUMERATING, not by recalling"* — and it wants a
mechanical enumerator (`tsc`, a grep with a declared scope), not a premise tag. A premise tag on *"the
branded type enumerates write sites"* would have demanded a `file:line`, which is genuinely what round
7 supplied — so the tag helps here — but the durable repair is the enumerator, and entry 11 files the
whole episode under routing instead.

### H3 — The thesis is a minority explanation, and the project's own Phase 6 review names a different cause

The thesis is not false. P4 in particular holds up: commit `4054928` records that
`assertCloudSummaryMdKey`'s own docstring said the requirement was *"a SINGLE path component"* and
that the allowlist existed because *"slugify never emits anything outside the allowed class"* — so a
`[VERIFIED: file:line]` demand would plausibly have forced that read. That is a real, specific,
cheap-to-check premise, and the PR's account of it is corroborated.

But four things cut against the PR's framing that this explains the seven rounds. The first is the
arithmetic in H2: **5 of 34 Blocking+High findings (14.7%), or 10/34 (29.4%) on a generous reading.**
The rest follow.

**(a) The author's own contemporaneous diagnosis, across four commits, says something else:**

```
ca856de  v3 — round 2 showed v2 patched one decision 4x
20acdb7  v4 — delete the Unicode equivalence; three rounds were all one mistake
6e331d5  v5 — rewrite (720->347); servability is the precondition, not storability
4054928  v8 — the "servable" constraint was self-imposed; delete the machinery it justified
```

Corroborated by the round verdicts quoted in H2: rounds 5–7 were a missed write entrance found three
times running, not a premise defect. That is repeated local patching of a wrong shape and a
self-imposed constraint — the failure the
**stop condition** in `review-method.md` was armed for on 2026-08-09 (`bc43a6c`): *"If a component
produces findings caused by the PREVIOUS round's fixes in two consecutive rounds, it escalates from
FIX to REDESIGN."* That rule lives in `review-method.md` with the read-trigger *"a review round is
starting"* — which is the **correct** trigger for it, since it is evaluated during review — and #36
still ran to seven rounds. A rule in the right document for the right phase also did not fire.

**(b) A rule in exactly the right place did not fire inside this very PR.** See M2:
`portable-practices.md:8` says its counts are *"re-enumerated, not recalled, whenever this file is
edited."* This PR edits that file, adding 48 lines, and leaves the counts stale. The reader was in the
file, the rule is 280 lines above the edit, the trigger is "editing this file" — and it still did not
fire. That is direct counter-evidence to *placement* being the operative variable.

**(c) Phase 6 ran on this exact spec, one day earlier, and concluded differently.**
`docs/reviews/architecture-review-2026-08-14.md` (on `fix/cloud-blob-key-encoding`, triggered by the
four-round condition):

> **The architecture is sound and the churn was a specification problem.** … **But one architectural
> cause is real and it is what made four rounds necessary:** *"is this key acceptable?"* is answered
> by four independent predicates at four layers … That is an instance of a pattern this subsystem uses
> **five times**: safety carried by *"nothing currently calls that"* or *"nothing currently produces
> that shape."* … Nobody counts them, and no instrument in this repo can. **That count is the
> composition defect.**

Its finding 8 is labelled *"the composition defect"*. **PR #102 does not cite, mention, or reconcile
with that review.** The two diagnoses overlap at P4 but are not the same instrument: Phase 6 asks for
a *count of "safe because nothing does X yet" arguments*; this PR builds a premise-tag ratchet.

**(d) The premise framing is retrospective, and nothing in the review record uses it.** Searching all
15 review files for `review-method`, `[VERIFIED]`, `[ASSUMPTION]`, or a premise-tag rule returns
**zero hits**; `grep -rni premise` returns 3 incidental uses (`r1-claude:525`, `r2-claude:62`,
`r4-claude:24`). This cuts both ways and I want to be fair about it: it **supports** the PR's claim
that the rule never fired. But it also means the five "premises" are a **post-hoc reconstruction** by
the author, not a category the reviewers were working in — which is exactly the condition under which
a narrative fits the evidence because it was fitted to it. Two of the five rows (P2, P3) produced no
Blocking or High at all, which is what that looks like from outside. The reviewers found these defects
without the concept, by reading code.

Round 6 states the dominant pattern outright, and it is not premises (`r6-claude:124`):

> **Stop enumerating entrances in prose.** Six enumerations across six rounds have each missed one.

**What I am asking for.** Not withdrawal. The premise-routing lesson is real and worth keeping. But
`portable-practices.md` entry 11 currently presents it as *the* explanation of seven rounds, and it
should either (i) be scoped honestly — premise defects explain rounds 1–4, and the cost column must be
corrected per H2 — or (ii) name the Phase 6 finding and the missed-write-entrance pattern as co-causes
and say which instrument covers which. As written, merging it risks displacing a diagnosis the project
reached one day earlier with more evidence behind it.

**Concretely, the smallest honest fix:** state the ratio (5 of 34 Blocking+High, or 10/34 generously)
instead of "seven rounds"; drop or downgrade the P2 and P3 rows, which no Blocking or High supports;
correct the P1 and P4 cost cells per H2; and add one sentence saying the last three rounds were a
different failure — a hand-maintained enumeration that was wrong six times — with a different repair.
That keeps the lesson, which I believe is real, and stops it overreaching. A measured 15% cause is
still worth a script; it is just not the story of the seven rounds.

---

## MEDIUM

### M1 — The script's own measurement contradicts the script's own output

`scripts/check-premises.py:101-102`:

> *"Measured 2026-08-14: **1 of 77** specs had one, so this ratchet starts almost entirely INERT"*

The script prints `COVERAGE: 0/78`, and `portable-practices.md` entry 11 says *"0 of 78 specs had a
premises section at all"*. Three numbers, two of them agreeing, one not.

The cause is diagnosable: the only spec in the repo with a matching heading is the #36 spec, which is
on `fix/cloud-blob-key-encoding` and not on this branch. So `1 of 77` was measured on a **different
tree** than the one this PR ships, and never re-run against the shipping tree. `git ls-tree -r
--name-only HEAD docs/superpowers/specs/ | grep -c '\.md$'` → **77**, plus `docs/design-spec.md` = 78
scanned, 0 covered.

This is the same defect class as H2, in the file whose docstring is arguing for measurement.

### M2 — `portable-practices.md`'s own re-enumeration rule was broken by this edit

`docs/portable-practices.md:8`: *"see *Not yet mined*, whose counts are re-enumerated, not recalled,
whenever this file is edited."*

The block (`:287`) still reads **"Re-enumerated 2026-08-13 … 61 memory files, 633 review documents"**,
and the diff leaves it untouched (it appears only as context). Enumerated now:

```
tracked review docs at HEAD : 640     (file claims 633)
memory files                : 62      (file claims 61)
```

Fix is one line. Its analytical significance is larger, and is (b) in H3.

### M3 — `BASELINE = 0` was set against a corpus that does not contain the subject

`scripts/check-premises.py:50`. The baseline is honest for *this* tree. But the one spec that has a
premise section is about to land from `fix/cloud-blob-key-encoding`, and v8 of it produces **three**
violations:

```
spec-v8.md: violations=['premise section carries no tag: ## 1. Purpose and premises',
                        'premise section carries no tag: ### 1.1 Premises this design rests on',
                        'premise section carries no tag: ## 2. What was measured']
```

So whichever of the two branches merges second turns master's CI red. That is arguably the ratchet
working as intended — but it should be a **deliberate** choice made now, not a surprise later, because
the tempting response under pressure is to raise `BASELINE` to 3, which permanently unarms it. Flagging
so the author decides: tag §1/§1.1/§2 of the #36 spec as part of that branch.

(Note the interaction with B1: tagging those three sections is a three-line edit that silences the
check without tagging a single one of the five premises.)

---

## LOW

### L1 — Ratchet rule 2 (all three exit directions) is neither reachable nor tested

`docs/process-checklists.md:277` requires testing all three directions. With `BASELINE = 0` and
`count` a sum of `len()`, `count < BASELINE` is unreachable, so `:196-197` is permanently dead code.
Separately, `self_test()` (`:144-169`) exercises `audit()` only — it never calls `main()`, so **no
exit code is tested at all**. The rule that *"the first revision of the newest ratchet returned 1 at
baseline, which would have broken CI the moment it merged"* (`:278-279`) is the one this does not check.

### L2 — Rule 4's mutation loop covers 3 of the 4 discriminators

`:155-159` mutates `PREMISE_HEADING_RE`, `LOAD_BEARING_RE`, `VERIFIED_RE`. `ASSUMPTION_RE` (`:55`) is
a discriminator too — used at `:86` and `:91` — and is absent from the loop, which advertises itself
as *"each discriminator must kill at least one case"*. I mutated it manually and it is incidentally
covered by the corpus:

```
ASSUMPTION_RE never matches   : kills 1 case(s)
ASSUMPTION_RE matches anything: kills 4 case(s)
```

So this is a completeness gap in the declared loop, not a live blind spot. Add the two lines.

The three declared mutations are genuinely independent discriminators (3 / 1 / 3 kills), and the eight
cases are balanced 4 expect-violation / 4 expect-clean, so the corpus is not trivially satisfiable.
`--self-test` proves what it claims, within L2's scope.

### L3 — CI runs the instrument's self-test *after* trusting its verdict

`.github/workflows/ci.yml:118-124` orders `check-premises.py` then `--self-test`. No masking occurs —
they are separate steps and both must pass — but if the real run fails, the self-test step is skipped
by default, so you learn a verdict before learning whether the instrument works. Swapping the two
steps costs nothing. No cost concern: both are pure-Python, no network, sub-second.

---

## Ratchet contract scorecard

| Rule | Verdict |
|---|---|
| 1. Cannot run = FAILURE | ✗ **H1** — per-file yes, zero-subject no |
| 2. Exit semantics all three directions | ✗ **L1** — third unreachable, none tested |
| 3. Named baseline, dated comment | ✓ `:49-50` |
| 4. `--self-test` + mutate each discriminator | ~ **L2** — 3 of 4 |
| 5. Declared scope | ✓ `:23-27`, unusually clear |
| 6. Never mutate repo-tracked files | ✓ read-only; `self_test` patches `globals()` in-process only |

`python3 scripts/check-ratchet-contract.py` → exit 0, discovers the new script (9 ratchets, up from 8),
does not flag it. It statically enforces rules 1 and 4 only, and says so; both of my findings there are
in the part it declares it does not check.

---

## What I ran

```
python3 scripts/check-premises.py --self-test      exit 0   8/8 cases, 3/3 mutations
python3 scripts/check-premises.py                  exit 0   0 violations, COVERAGE 0/78
python3 scripts/check-premises.py --json           exit 0   specs_scanned 78, with_premise_section 0
python3 scripts/check-ratchet-contract.py          exit 0   9 ratchets, 4 violations, at baseline
python3 scripts/check-docs.py                      exit 0   budgets ok, 44 links, 20 advisory
```

Plus: `audit()` against all 8 versions of the #36 spec; 5 hand-built bypass specs; the one-line-patch
demonstration through the real globs; a zero-subject `collect()`; manual mutation of `ASSUMPTION_RE`;
`git ls-tree` counts for reviews/specs/memories; and a full enumeration of all 34 Blocking+High
findings across the 15 review files, reconciled against each Claude review's own headline verdict line
and classified by stated root cause.

**Tree left clean.** Two files were copied into `docs/superpowers/specs/` to exercise the real globs
and deleted immediately; `git status --porcelain` after cleanup showed only the other reviewer's
untracked output file. No tracked file was modified except this review.

## Checked and found SOUND (recorded so it is not re-litigated)

- **The `1216` figure** in `review-method.md`'s new section is corroborated: `spec-v2.md:88,91` records
  `ACCEPTED | 1216 | 6 segments × 200` and states the bound explicitly. (The round-1 reviewer's own
  probe said "at least 1063" from a 4×200 run; 1216 is the later, larger measurement. Not a defect.)
- **The core epistemic point of the `review-method.md` addition** — *"could this experiment have
  returned the other answer?"* — is correct and well-argued, and the 267-vs-255 case genuinely
  illustrates it: a fixed prefix with one varying segment cannot distinguish per-segment from
  whole-path. Only the "survived two rounds" claim about it is wrong (H2).
- **P4 and P5 are real premise defects** (their *cost attributions* are what H2 disputes, not their
  existence). P4 is corroborated by commit `4054928` (`assertCloudSummaryMdKey`'s docstring said the
  requirement was *"a SINGLE path component"*, and the allowlist existed because *"slugify never emits
  anything outside the allowed class"*) and by two findings, `r2-claude:27` and `r4-claude:66`. P5 is
  round 7's headline finding, `r7-claude:113` and `r7-codex:3`.
- **Ratchet rules 3, 5 and 6** are satisfied, and rule 5's scope declaration (`:23-27`) is better than
  most in the repo.
- **The three declared mutations are independent discriminators** (3 / 1 / 3 kills), and the eight
  self-test cases are balanced 4 expect-violation / 4 expect-clean.
- **The CI wiring cannot mask.** Two separate steps, both must pass; `check-ratchet-contract.py`
  discovers the new script via its docstring even though neither step name contains "ratchet".
- **`portable-practices.md` entry 11 clears filter 2** (project-independent): the lesson — name the
  phase in which a rule's defect is *committed* and check the rule is reachable from there — holds in a
  repo with no Supabase. Filter 1 (measured) is met in form; H2/M1 are about the accuracy of two of
  those measurements, not their absence.

## What would have found each class of defect

- **Ratchet porosity** — writing candidate specs and *running* the script, rather than reading the
  regexes. Four of my six bypasses were not visible to me from reading `PREMISE_HEADING_RE`; the
  section-scoping of rule 2 (case B) and the 174-byte body of the real §2 only appeared on execution.
- **Wrong-subject coverage** — extracting the artifact the tool was built for from the branch it
  actually lives on, instead of testing against the corpus in front of me.
- **Thesis error** — reading the seven rounds and the four `docs(#36)` commit subjects, then checking
  whether a *different* armed rule had already fired. It had.
- **Stale measurements** — re-running the counts the prose asserts (`git ls-tree`, `ls | wc -l`),
  which is the file's own stated method.
