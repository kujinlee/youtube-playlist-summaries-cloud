# Round 10 — Claude half, `shard-mutation-sweep` (PR #366) at `d991afd5`

**Mandate: REFUTE.** This is the final confirmation round, so the question answered here is not
*can I find something* — nine rounds have found plenty — but **is anything left that would make
merging wrong.**

**Answer: no finding in the deliverable, at any severity.** Five findings, every one INSTRUMENT.
One of them says a backlog row filed yesterday is false about its own subject, which is the thing
the mandate asked for most directly. And there is **one procedural blocker that is not a finding**:
`check-merge-ready.py` is at **rc=2** right now, because CI on `d991afd5` has not finished.

---

## Verification

### The merge gate, relayed verbatim

```
pull request           : #366
base                   : origin/master
pull-request-only steps: 2 derived from ci.yml — dashboard entry ratchet, check-review-recorded (PR only)

  ok  dashboard entry    rc=0  ok — an entry block was added
  ok  review recorded    rc=0  ok — review recorded in this range: docs/reviews/claude/shard-mutation-sweep-r1-claude.m
  ok  review rounds      rc=0  ⚠ verdict corpus: 224 read — 32 meaningfully checked below, 192 PRE-CUTOVER (schema < 3:
  NO  mergeability       rc=1  mergeStateStatus is BLOCKED
  ??  CI                 rc=2  still running

CANNOT RUN — CI could not reach what they measure. Treat this as NOT RUN.
  ⚠ A local gate sweep cannot answer the pull-request-only checks above. That is why this script exists and why 'all my gates are green' is a different claim.
```

`RC=2`. Per `CLAUDE.md` — *"'Cannot run' is a FAILURE, never a pass"* — **this does not currently
clear the merge**, and the reason is benign: CI is genuinely still running.

- `gh pr checks 366`: eight `mutation-sweep (1..8)` **pending**, `schema-gates` **pending**,
  `verify` **pending**, `prod-drift` skipping — workflow runs **37541090988** / **37541090916**.
- `gh pr view 366`: `mergeStateStatus: BLOCKED`, `mergeable: MERGEABLE`, `headRefOid d991afd5`.

⚠ **The green run the brief cites is one commit behind HEAD.** On `897d0938` the check-run API
returns twelve runs — `mutation-sweep (1..8)` success, **`mutation-sweep-complete` success**,
`schema-gates` success, `verify` success, `prod-drift` skipped. That is the "11 passing, 0 failing"
figure, and it is accurate (11 non-skipped). But `d991afd5` added two docs-only commits after it, so
**the measurement the merge needs is the pending one**, not the cited one.

⚠ **Two commits landed after round 9's Codex half, and both are docs-only** — verified, because the
brief's claim that the final tree was reviewed depends on it. `shard-mutation-sweep-r9-codex.verdict.json`
records `head: 8756c623`, `gate_ran: true`, `model: gpt-5.5`, `refused: false`.
`git diff --name-only 8756c623..HEAD` returns exactly `docs/backlog.md`,
`docs/dashboard-entries.md`, and three round-9 review artifacts — **nothing outside `docs/`**. The
deliverable that merges is the deliverable round 9 reviewed.

### Can the PR-only derivation be incomplete at `d991afd5`?

**No.** Checked as a class, not an instance:

- `ci.yml` carries exactly two `if: github.event_name == 'pull_request'` steps, and both are named
  in the output above.
- `schema-gates.yml` has no pull-request-only step or job. Its two `if:` gates are
  `!= 'schedule'` (PR *and* push) and `== 'schedule' || == 'workflow_dispatch'` (`prod-drift`).
- `check-merge-ready.py` does not parse `ci.yml` alone — `workflow_files()` enumerates
  `.yml`/`.yaml` across `.github/workflows/`, and `ACCOUNTED_MENTIONS` (`:247-266`) accounts for
  **every** non-comment line in both files mentioning `pull_request` **or** `github.event_name`,
  with a count and a written reason each. An unaccounted mention is rc=2. It did not fire.

### Independently re-derived, not taken from the brief

| Claim | My measurement | Verdict |
|---|---|---|
| `--self-test` 178/178 | `178/178 passed`, rc=0 | ✅ |
| declared sum 1211 | 1211 entries across **57** manifest files | ✅ |
| 1,219 anchors, 0 unresolved, 0 duplicate tuples | 1,219 anchor edits; **0** unresolved, **0** ambiguous; 0 duplicate anchor-tuples | ✅ (see §R5) |
| required contexts | API: `["verify","schema-gates"]` | ✅ |
| `ci.yml` has no `paths:` filter | no `paths:`/`paths-ignore:` anywhere | ✅ |

---

## Findings

### 1. MEDIUM — INSTRUMENT. Backlog #235 is false about its own subject: **anchor resolution also left the required context**, and it is the more frequent defect of the two

`docs/backlog.md:256` (#235) states:

> Every other whole-manifest invariant (counts against `EXPECTED_MUTATIONS` in both directions, the
> duplicate name and anchor refusals) also runs in `verify` via `--self-test`; this one does not.
> […] *The home-escape scan is the one item on that list with no second home.*

**It is not the one item. It is one of two.** `ci.yml`'s own FAILS IF list includes *"an anchor is
missing or ambiguous"*, and that item has no second home in `verify` either.

Traced, not inferred:

- `--self-test` touches the real manifests in exactly two cases (`check-plan-code.py:4624-4627`):
  `"the manifests ON DISK load with no refusal"` and `"...and the entry count they yield is the
  pinned sum"`. Both go through `load_manifests(_repo)`.
- `load_manifests` (`:1470-1535`) checks target existence, JSON validity, non-emptiness,
  duplicate name, duplicate anchor-**tuple**, and file/manifest-name agreement. **It never reads a
  delivered source file**, so it cannot resolve an anchor.
- Resolution lives in `run_mutations`: `src.count(find) > 1` → *"anchor matches N times"* (`:1952`)
  and `find not in src` → *"anchor NOT FOUND"* (`:1962`).
- `run_mutations` has **one** non-synthetic caller: `mutate_delivered:1866`. Every other call site
  (`:2584`–`:3773`, thirteen of them) runs against temp fixtures named `m.py`/`n.py`/`p.py`.
  `mutate_delivered` is reachable only from `--mutate`.

⭐ **The row's own severity argument does not transfer, and that is what makes this worth filing
rather than noting.** #235 earns its Low with a bound: *"reaching it needs an edit to a manifest or
a mutation target that also survives review."* True of a home-escape. **False of an orphaned
anchor** — an anchor binds by TEXT, so *ordinary refactoring of delivered code near an anchor*
orphans it while the suite stays green. `check-plan-code.py:984` says so in the file itself:

> An anchor binds by TEXT, so improving code breaks it and the suite stays green; `--mutate .`
> refuses an unresolved anchor, **which is the only reason that was caught here rather than merged.**

So the repository's own comment names `--mutate .` as the sole instrument for the class — and this
PR moves it out of the required context. The hazard is recorded as recurring (seven anchors orphaned
in one session, one of them a blocking red CI step).

⚠ **Why this is Medium and not High, stated as a measurement rather than a judgement.** The window
is guarded by the same instrument that guards the home-escape gap, and I verified it rather than
taking the PR body's word: `check-merge-ready.ci_conclusion` (`:386-394`) returns rc=1 on **any**
check whose bucket is not `pass`/`skipping`, and rc=2 on pending or empty. A red shard is therefore
visible to the documented pre-merge step even before the repo setting lands. The PR body's round-1
correction to that effect (lines 138-141) is **correct**.

⚠ **Also not a reason to hold the merge:** the *general* loss of the sweep from the required context
is disclosed loudly and in three places (`ci.yml`'s `mutation-sweep-complete` comment, the PR body's
READ FIRST block, and backlog #217). What is mis-stated is only the *enumeration* of which global
checks lost their second home.

**Two sites carry the false claim**, and both will be read by whoever actions the row:
`docs/backlog.md:256`, and the dashboard tail (*"#235 the home-escape scan is the one global check
riding only on the non-required matrix"*).

**Candidate fix:** amend #235 to name both dimensions, and move the frequency argument onto the
anchor half — its bound is *a refactor*, not *a surviving manifest edit*. A single fix closes both:
give `home_escapes()` **and** the resolution branches a caller reachable from `--self-test` over the
delivered tree.

**FAILS IF:** `--self-test` passes on a tree where a manifest anchor does not occur in its target,
or occurs more than once.

---

### 2. LOW — INSTRUMENT (merge artifact). The PR body's "Review state" says **"Eight rounds"**; nine are filed, and backlog #217 already says nine

`docs/reviews/claude/` holds **9** `shard-mutation-sweep-r*-claude.md`; `docs/reviews/codex/` holds
**9**; `docs/reviews/verdicts/` holds **9** verdicts. The PR body line reads:

> **Eight rounds, both halves each** — ⚠ this line said *"Five"* until round 8 caught it […]

Round 8 set it to eight; round 9 did not bump it. Backlog #217's closure note says *"Nine review
rounds"*, so **the two merge artifacts now disagree with each other** — and after this round both
are low by one or two.

⭐ This is the same defect the line's own footnote records, in its next generation, and it is the
reason #234 exists. **A number written into prose has no owner.** The durable form here is not a
corrected figure but `ls docs/reviews/claude | grep -c shard-mutation`.

**FAILS IF:** the body's round count differs from the number of filed `(claude, codex)` pairs.

---

### 3. LOW — INSTRUMENT (merge artifact). The corrections table's **figures are right and its build attribution is wrong** — a new shape of a defect now in its fourth generation

The table header says *"Actual at `ece8d309`"* and asserts declared sum **1211** and self-test
**178**. Measured at `ece8d309` (10 commits back on this branch):

| | at `ece8d309` | at `d991afd5` |
|---|---|---|
| manifest entries | **1200** | 1211 |
| declared self-test cases | **161** | 178 |

So 1211/178 are HEAD's values presented as `ece8d309`'s. ⭐ **And the paragraph immediately below it
documents 1200/161 as the stale values round 9 replaced** — when 1200/161 were the *correct* values
for the commit the table names.

⚠ **This generation is structurally different from the three before it, which is why it survived.**
Generations one to three were *stale numbers against a correct build*; this one is *correct numbers
against a stale build*, produced by fixing the figure and not the attribution. A reader checking the
table does the obvious thing — re-measure at HEAD, see 1211/178, conclude it is current — and the
attribution is the half nobody re-derives. This is exactly `dev-process.md`'s gate rule:

> **Record which build a manual check was verified against.** A tick says *that* something was
> verified, never *what against* — and the subject moves.

**Candidate fix:** drop the commit reference, or set it to `d991afd5`. The table already carries the
two commands; the figures are what should go, not the build.

**FAILS IF:** a figure in the corrections table differs from the value produced at the commit the
table names.

---

### 4. LOW — INSTRUMENT (merge artifact). The dashboard tail claims the corrections table "now carries the commands … **instead of** the figures". It carries both

Written in the last hour. The dashboard entry says:

> It now carries the commands that produce the figures instead of the figures.

The table still carries `1211`, `178`, and *"1,211 entries across 57 manifest files"* — alongside
the commands, not in place of them. The commands were **added**; the figures were **updated**. Those
are different acts, and the one that leaves a stale-number surface is the one that happened.

Combined with finding 3, the dashboard tail asserts a repair whose own residue is the defect it
claims to have removed.

**FAILS IF:** the dashboard entry asserts the corrections table carries commands instead of figures
while the table contains a bare figure.

---

### 5. LOW — INSTRUMENT (process). **Round 9's committed review document is modified in the working tree, and no review gate can see it**

`git status` at `d991afd5`:

```
 M docs/reviews/claude/shard-mutation-sweep-r9-claude.md
```

`+30/-2`. The edit retroactively marks a round-9 finding **CLOSED DURING THIS ROUND**, rewrites
*"the effect is"* → *"the effect was"*, and appends new analysis of #230's cheaper closer.

It is invisible to every gate, by construction:

- `check-review-recorded.py:1249-1251` builds `git diff --name-only -z --no-renames` and appends
  `--diff-filter=A`. The question it asks is *"did this branch **ADD** a file under `docs/reviews/`?"*
  An **M** to an already-added document is never re-examined.
- `shard-mutation-sweep-r9-codex.verdict.json` still certifies `gate_ran: true` against head
  `8756c623`, unchanged by an edit to its partner half.
- `check-review-rounds.py` asks whether both halves exist, not whether either still says what it
  said when its verdict was written.

⚠ **This instance is benign in content** — the finding it withdraws was genuinely fixed, and the
withdrawal is recorded as an amendment rather than a silent deletion, which is the right form. The
finding is the *property*: `docs/plugins.md` carries the rule **"a refusal never overwrites the
testimony it protects"**, enforced one layer in (a refused run writes `*.refused.verdict.json`,
never over `<id>.verdict.json`) — and it notes the gap itself: *"`check-review-recorded.py` cannot
see it: `--diff-filter=A`, and an overwrite is **M**."* That gap is live one layer out too: the
testimony is mutable after its verdict, and nothing observes the mutation.

**Before merging, this needs a decision rather than a fix.** It is docs-only, so committing it does
*not* re-open `check-review-recorded` and does not breach the freeze. Discarding it drops the record
that round 9's gate near-miss and M1 closed — which backlog #230 and #235 both now rely on. **My
recommendation: commit it.** Leaving a tracked modification uncommitted through a merge is the one
option that loses information silently.

**FAILS IF:** a review document is modified after its round's verdict is recorded and no gate reports it.

---

### Noted, below filing threshold

**`check-merge-ready.py`'s own docstring is wrong about its subject, and was already wrong on
`master`.** Line 16 says *"**52 steps carry a `run:**`, and exactly 2 are gated"* and *"a local
sweep covers 50 of 52"*. Measured: **63** at `d991afd5`, **60** on `origin/master`. Pre-existing —
this PR widened the gap from 8 to 11 but did not create it. The *load-bearing* half of the sentence
(**exactly 2** PR-only) is correct and is derived at runtime, not from this number.

⚠ **It is worth one line because it exposes a gap in #234's own falsifier**, which the mandate asked
me to audit. #234's FAILS IF reads *"a comment in `scripts/` asserts a count of **callers or
readers** that `grep` contradicts."* This is a count of **workflow steps** — same class, outside the
stated falsifier. Widening #234's falsifier to *any count a command contradicts* costs nothing and
catches this.

**`check-merge-ready`'s verbatim output is column-truncated by the script itself** — the `review
recorded` line ends mid-path at `...r1-claude.m`, and `review rounds` ends mid-sentence at
`(schema < 3:`. The repo rule is to relay that verdict **verbatim**; a verbatim relay of a truncated
line relays a partial sentence. Not filed: it is cosmetic and the rows' rc values are intact.

---

## What I tried to refute and could not

This is the product of a clean final round, so it is specific about what was run.

**R1 — `ci.yml`'s licensing claim, which is the whole justification for deleting `--mutate .` from
the required `verify` job.** The claim: *"the whole-manifest checks in that FAILS IF list run in
every shard; only the suite runs are split."* If any global check had silently become per-slice,
merging would weaken `master` and nothing would say so. **Verified in code, and the ordering is
explicit.** `mutate_delivered` (`:1735`) calls `load_manifests(root)` first, then runs the
home-escape scan over every target (`:1798`) **and every replacement** (`:1809`), and only then:

```
# ⛔ EVERYTHING ABOVE THIS LINE IS OVER THE WHOLE MANIFEST, AND MUST STAY THAT WAY.
…
if shard is not None:
    why = shard_refusal(shard[0], shard[1], len(muts))
…
shard_muts = shard_slice(muts, shard[0], shard[1]) if shard is not None else muts
```

`shard_refusal` is passed `len(muts)` — the **full** manifest — and the count/duplicate checks ran
before the slice existed. Only `targets` (`:1831`) narrows to the shard. **Could not refute.**

**R2 — a reachable GitHub state producing a green PR over unmeasured work, excluding the ones
already filed.** Constructed and traced six:

| Attempt | Why it fails safe |
|---|---|
| `concurrency: cancel-in-progress` cancels mid-matrix | `if: always()` runs the aggregator on a cancelled run; `needs.mutation-sweep.result` is `cancelled` ≠ `success` → exit 1 |
| matrix produces zero jobs | `shard: [1..8]` is a literal list, not `fromJSON` of anything |
| matrix job `skipped` | aggregate is `skipped` ≠ `success` → exit 1 (and the job comment says so) |
| `timeout-minutes: 30` kills a shard | a timeout kill is job `failure` → aggregate `failure` → exit 1 |
| re-run one failed shard only (`--job`) | dependents are not re-run, so the aggregator stays red — a false **red**, safe direction |
| re-run the aggregator alone | it reads the *recorded* matrix aggregate, which is still `failure` |

**NOT MEASURED:** `strategy.job-index`/`job-total` semantics under a **partial re-run**. All runs on
this branch are attempt 1 and GitHub documents neither direction. Already recorded in #230, and its
other branch fails loud (a collapsed `job-total` sweeps the whole manifest and is killed by the
timeout, #231). I add nothing to it.

**R3 — `mutation-sweep` does not install `ffmpeg`, which `verify` installs "required by the
slide-crop tests".** Traced both directions rather than assuming. A suite degraded by a missing
`ffmpeg` either (a) reds the control → `CANNOT RUN`, shard red, or (b) stays green and the mutation
survives → shard red. **Both directions are safe**, and all eight shards were green on `897d0938`.
Not a finding.

**R4 — `mutation-sweep-complete` is absent from `gh pr checks` on the current run.** I expected an
aggregator that never reports — the pending-forever shape of #137. **Refuted:** it is absent only
because `needs: mutation-sweep` has not resolved. On `897d0938` the check-run API lists it as
`success`. The brief's "11 passing" is 8 shards + aggregator + `schema-gates` + `verify`, with
`prod-drift` skipped.

**R5 — "0 duplicate tuples", where I measured 2 — and my measurement was the wrong instrument.**
Recorded in full because the near-miss is this repository's most expensive recurring class.
My rule keyed on each individual `(file, find)` pair and found 2 collisions. **The code's rule is
different and mine was wrong about its subject:** `load_manifests:1496` keys on
`tuple(f for f, _ in e.get("edits", []))` — the exact tuple of **all** of an entry's anchors. Both
of my collisions are legitimate under it and under inspection:

- `check-plan-file-tags.py` — two entries share one `find` but carry **different replacements**
  (dropping leading-whitespace tolerance vs dropping the end anchor): two genuinely different
  behaviours at one line.
- `check-python-pin.py` — the second entry carries a **two-element** edit list, so its anchor tuple
  differs in length.

The brief's claim is correct under the rule the code applies. ⚠ And the file already states the
honest bound at `:1510-1519`: exact-tuple equality means *"the message claims more than the test
delivers"*, and a duplicate-**in-substance** entry is caught by nothing — documented, with the
reason a `expect`-based rule cannot be added (it would red six shipping manifests). **Nothing to
file; my measurement is the error.**

**R6 — the PR body's mitigation claim.** *"`ci_conclusion` fails on any non-pass check, so a red
shard is visible pre-merge even before the repo setting lands."* Verified at `:386-394`. **True**,
and it is what keeps finding 1 at Medium.

**R7 — the two commits after round 9's Codex half.** If either touched `scripts/` or
`.github/`, the brief's "final tree was reviewed" would be false and the merge should stop.
`git diff --name-only 8756c623..HEAD` returns five paths, **all** under `docs/`. **Could not
refute.**

**R8 — every number the brief supplied.** 178/178, 1211, 57 files, 1,219 anchors / 0 unresolved /
0 ambiguous, `["verify","schema-gates"]`, no `paths:` filter. All independently re-derived, all
correct. **The only brief claim I could fault is a round count the brief did not make** (finding 2).

---

## Findings table

| # | Severity | Deliverable or instrument | Caused by a previous fold? |
|---|---|---|---|
| 1 | **Medium** | INSTRUMENT (backlog #235 + dashboard tail) | Yes — round 9 filed the row; the gap it describes is real and its enumeration is not |
| 2 | Low | INSTRUMENT (PR body) | Yes — round 8 set "Eight"; round 9's fold did not bump it |
| 3 | Low | INSTRUMENT (PR body) | **Yes, and it is the fold's residue** — round 9 corrected the figures and left the build reference |
| 4 | Low | INSTRUMENT (dashboard tail) | Yes — round 9 wrote the sentence while making the change it overstates |
| 5 | Low | INSTRUMENT (review ledger) | Yes — round 9's own document, amended after its verdict |
| — | noted | INSTRUMENT (`check-merge-ready` docstring; #234's falsifier) | No — already wrong on `origin/master` |

**Deliverable findings: zero, at any severity.** Nothing folds.

⭐ **The pattern across all five is one pattern, and it is worth naming once rather than filing
five times:** every finding this round is in an artifact **round 9 wrote or amended**, and four of
the five are a *correction whose own residue is the defect it corrected*. That is the shape backlog
#234 was filed for, now measured a sixth time, and it is the strongest available argument that the
remaining work on this branch is **not another round** — rounds are no longer finding defects in the
code, they are finding the prose each round adds. **Stop reviewing and merge.**

---

## Verdict

### CONVERGED

**This is the second consecutive clean round.** Round 9 was the first: both halves clean, no
Blocking, no High, no finding in the deliverable. Round 10 is the second — no Blocking, no High,
**no finding in the deliverable at any severity**, and no non-trivial fix required. Judged by AIM
per `review-method.md:112`, the five findings here are all INSTRUMENT: three stale sentences in
merge artifacts, one false enumeration in a backlog row, one mutable-testimony property of the
review ledger. None of them is about the sharding, the matrix, the partition, or the aggregator.

`review-method.md:110`'s stop condition is met.

### Should this merge?

**Yes — once CI finishes green on `d991afd5`, and nothing else must change first.** The deliverable
is sound: I could not refute the partition, the aggregator, the whole-manifest invariants, or any
supplied figure, and I could not construct a reachable GitHub state giving a green PR over
unmeasured work. The three things to do are all bookkeeping and none of them is a gate: re-run
`check-merge-ready.py --pr 366` and require **rc=0** with `mutation-sweep-complete` among the green
checks (it is currently **rc=2 — treat as NOT RUN**, not as a pass); decide finding 5 by committing
the round-9 amendment, which is docs-only and does not re-open `check-review-recorded`; and amend
backlog #235 so the row names anchor resolution alongside the home-escape scan — ⛔ **that amendment
matters more than the merge timing, because the row will be actioned by someone who trusts it, and
as written it will be closed while the more frequent half of the gap stays open.**

⚠ And the owner's one remaining action is unchanged and still correct: add `mutation-sweep-complete`
to `required_status_checks.contexts` for `master` **after** this merges. Round 9 established it is
safe; finding 1 is the measurement of what that setting is now also buying back.
