# velocity-backfill r1 — Claude half

**Subjects as assigned, at HEAD `5996a6d8`:**
`docs/superpowers/specs/2026-09-25-development-velocity-design.md` ·
`docs/superpowers/plans/2026-09-25-development-velocity.md`

⚠ **THE SUBJECT MOVED UNDER ME AND THAT IS STATED RATHER THAN HIDDEN.** At 20:54 local, mid-review,
both files were renamed to `…-RECONSTRUCTED-design.md` / `…-RECONSTRUCTED-plan.md` and edited; the
coordinator committed `8e8bbe2e`, folding the Codex half's High plus five Mediums, **before this
half landed**. Every finding below was found against `5996a6d8` and then **re-checked against the
post-fold tree**; each says which. Findings the fold already closed are not re-filed — they are
listed under *Already closed by the r1 fold* so the lead does not double-count them.

---

## Blocking

### B1
- **severity:** Blocking
- **component:** reconstructed-checkbox-grammar
- **aim:** deliverable
- **fix_induced:** false

**The plan's mitigation is a label, and there is a reader of this plan that structurally cannot
receive a label. That reader consumes exactly the thing #119 named: machine-readable claims.**

`scripts/check-plan-progress.py` is the Stop guard. `count_steps` (`:139`) reads `- [x]` / `- [ ]`
at line start and returns a pair of integers — there is no channel through which any caveat reaches
it. Run against the post-fold plan:

```
$ cd scripts && python3 -c "…exec check-plan-progress.py…; print(m.count_steps(t)); print(m.next_pending_task(t))"
count_steps -> (12, 25)
next_pending_task -> (before the first task heading)
```

**All twelve ticked steps are reconstructions.** Not one of them was executed under this plan. The
guard's output for this plan is therefore `12/25 steps ticked` — a machine-readable progress claim,
reconstructed rather than recorded, which is backlog #119's formulation verbatim
(`docs/backlog.md:147`).

⛔ **The r1 fold does not reach this, and cannot.** Its repair was to add a prose banner to each
reconstructed task (`> ⛔ Every [x] in this task means "this shipped"…`). `count_steps` does not read
prose. The label now travels to three more *human* surfaces and to zero machine surfaces — the fold
strengthened the channel that was already working.

⚠ **The honest bound, stated because it changes the severity argument and not stating it would be
the defect this repo files against itself:** the guard reads only the plan named in
`.claude/executing-plan`, so the 12/25 figure is produced only if someone arms this plan with
`begin-plan.py`. **It is Blocking anyway**, because the documents' entire Phase 1 case is the
sentence *"the label is the whole mitigation"* (plan `:30`), and that sentence is **false as
written** — there is a reader for which the mitigation does not exist. #119 did not turn on who
read the manufactured claim either; it turned on the claim being manufactured.

**The fix is cheap and does not cost the index.** Reconstructed items do not need checkbox grammar
at all — they are not steps anyone will execute. Render Tasks 1–3 as plain `-` bullets under a
heading that says *Already shipped — index over PR #345*, and `count_steps` returns `(0, 13)`: every
ticked box in the file then genuinely means *planned here, then done here*. Keeping `- [x]` buys
nothing a bullet does not, and it is the only part of these documents that a machine will read as
testimony.

---

## High

### H0
- **severity:** High
- **component:** goals-page-work-state
- **aim:** deliverable
- **fix_induced:** false

**The backfill exists to make #177 visible on the goals page. What the goals page now says about
#177 is `no pull requests` — and four of its five strands shipped in PR #345.**

Regenerated against the post-fold tree (`8e8bbe2e`):

```
$ python3 scripts/gen-goals-page.py --out <scratch>/goals2.html
wrote … (13 goals, 55 docs, 1 with a spine)

review-decides-itself … Work 4 thread(s) · 2 PR(s) · derived from git at 8e8bbe2e
  2026-09-25-development-velocity-RECONSTRUCTED   no pull requests
      spec 2026-09-25-development-velocity-RECONSTRUCTED-design.md
      plan 2026-09-25-development-velocity-RECONSTRUCTED-plan.md
  2026-09-25-decision-card-soundness   1 PR(s) … docs only #347
```

`thread_prs` derives PRs from `git log` over the thread's **own documents**. These documents were
committed direct to the branch (`c2140f4b`, `5996a6d8`, `8e8bbe2e`), none with a `(#N)` subject
tail, so the thread resolves to zero PRs. Meanwhile the *`decision-card-soundness`* thread beside it
— which has shipped nothing — renders `1 PR(s)`.

⛔ **So on the one surface these files were built for, #177 now reads: design present, plan present,
nothing shipped. The truth is the inverse** — mostly shipped, never designed. `RECONSTRUCTED` in the
filename says the *documents* are reconstructed; it says nothing about the work, and a reader
scanning the Work column does not get a correction, they get a false state in the page's own
vocabulary.

**This is the Codex High's other half, and the fold stopped at the first half.** Codex asked *does
the caveat appear?* and fixed that. Nobody asked *what else does this card now assert?*

**A verified fix path exists inside these documents.** `gen-goals-page.MILESTONE` is
`^#{2,4}\s+(M\d+)\s*[—-]?\s*(.*)$` and its state markers are `⛔ ◀ ✅`. The goal's Milestones slot
currently renders *"No milestone plan — this goal has no spine to read state from."* A spine of
`## M1 — strands ⑵⑶⑷, shipped in PR #345 ✅` / `## M2 — Q0 …` in the plan would put the shipped
state, and PR #345, on the card in the page's own rendered vocabulary — and would fill the empty
slot the page already flags as a finding.

### H1
- **severity:** High
- **component:** disjointness-claim
- **aim:** deliverable
- **fix_induced:** false

**The spec's own falsifier is already firing at commit time, and the r1 fold made the case for it
stronger rather than weaker.**

The spec states the falsifier itself: *"`development-velocity.md` and this spec both describe the
same mechanism → the disjoint-jobs split failed and there are now two owners."* Its concern table
declares the split as *"this spec owns the design, `development-velocity.md` owns measurements and
history"*, and *Prior art* asserts of that file *"It keeps that job; this document does not duplicate
it."*

⛔ **`development-velocity.md` §2 and §3 are not measurements and not history. They are the design.**

| The spec says | `development-velocity.md` already has it |
|---|---|
| §2's kind-of-wrongness table — seam / logic-in-seam / surface / guard / prose | `:83-89`, a five-row table with the same five distinctions and the same instrument per row |
| §2's HYBRID split — judgement at entry, mechanical for escalation, neither sufficient alone | `:62-76`, the blockquote *"FORM DECIDED 2026-09-24 by the user — HYBRID"*, with both halves and both warnings |
| §3's four SEAM-not-LOGIC signals | `:101-118`, the same four, numbered, with their worked instances |
| calibration before shipping the mechanical half | `:80-82` *"Calibrate the mechanical half against a corpus of past rounds before shipping it"* |

That is the whole of §2 and §3 of the spec. **The duplication is not at the margin; it is the
spec's design sections in their entirety.**

⚠ **And the r1 fold sharpened the contradiction.** It converted the *Measured costs* table to
pointers on the reasoning that `development-velocity.md` owns the measurements. After that edit,
`development-velocity.md` owns the measurements **and** the design, and the spec holds a second copy
of the design — the precise two-owner state its falsifier names. The spec also forecloses the
obvious remedy: *"It does not move or rewrite `development-velocity.md`."*

**What this needs is a decision, not a caveat.** Either §2/§3 of the spec become pointers the way
*Measured costs* just did, or `development-velocity.md` §2/§3 are cut down to the measurement that
motivates each and the design moves here. One of the two must lose the copy. `one-rule-one-place`
and `a-second-implementation-of-one-rule-drifts` (17 recorded instances) both say the copy drifts;
the shape-invariant Medium the fold just closed is that drift, already happened, in three days.

### H2
- **severity:** High
- **component:** omitted-design-constraint
- **aim:** deliverable
- **fix_induced:** false

**The record names two constraints the designer must not skip. The spec covers one and drops the
other — and the dropped one is the one the record calls *the thing the design session must answer
first*.**

`docs/development-velocity.md:78-80`, inside the blockquote that decides Q0's form:

> *"§0's own banner is 'read this, do not recall it', and its Q1 is explicitly keyed on the changed
> path set **rather than judgement**. A judgement question sitting at the top of that card is in
> tension with the card's own claim. **Q0 has to say out loud that it is the exception, and why — or
> it weakens everything under it.**"*

Backlog #177's status column repeats it: *"Two constraints the designer must not skip — Q0 must
state out loud that it is the EXCEPTION to §0's *keyed on paths, not judgement* stance, and the
mechanical half must be calibrated…"*

The live text it is about, `docs/review-method.md:25`: **"Keyed on the **changed path set**, not on
judgement."** — and `:28-34` explains that the rule owns *no path list of its own* precisely because
three hand-kept lists each mis-scored something dangerous.

Measured against both subjects, post-fold: the spec's §2 states the hybrid split and the two
warnings about neither half being sufficient, and **never says Q0 is the exception to Q1's stance**.
The plan's Task 5 enumerates entry half, escalation half, home, closing Task 3's hole, and a
falsifier — **five bullets, no exception statement**.

⛔ **This is the second omission of this exact class in one document.** The spec was corrected once
already for dropping the shape invariant; the r1 fold corrected it again for dropping the Phase 6
architecture review from the shape invariant's history. Three omissions, all in the same direction:
the reconstruction keeps the conclusions and loses the constraints attached to them. That is the
signature of reconstruction-from-recall, and it is the argument against this document's form that no
label answers.

**Fix:** Task 5 gains a bullet — *Q0 states in §0 that it is the exception to Q1's keyed-on-paths
stance, and why* — and the spec's §2 carries the sentence. One line each; it is currently absent
from both.

### H3
- **severity:** High
- **component:** cracked-ratio-replacement
- **aim:** deliverable
- **fix_induced:** false

**The row that exists to retract a cracked comparison states a second cracked comparison, in the
same sentence. It survived the fold verbatim.**

Spec, *Measured costs*, the `GitHub vs this machine` row (unchanged by `8e8bbe2e`), and repeated in
the plan's Task 5:

> *"**And the denominator moved** — `verify` was **488s** on #342 and is **673–680s** now, ~39%
> slower in three days."*

I re-derived the population by running the Actions API over every successful `ci.yml` run in the
window:

```
36187125066 2026-09-25 master                   verify=666s
36183107591 2026-09-25 decision-card-soundness   verify=686s
36095506698 2026-09-25 master                   verify=584s
36094717914 2026-09-25 velocity-doc-consistency  verify=654s
36093598038 2026-09-25 velocity-doc-consistency  verify=677s
36073928900 2026-09-24 master                   verify=667s
36072747242 2026-09-24 velocity-177             verify=680s
36070971836 2026-09-24 velocity-177             verify=673s
36051552339 2026-09-24 velocity-177             verify=674s
36049305547 2026-09-24 velocity-177             verify=419s
36048654618 2026-09-24 master                   verify=709s
36046955747 2026-09-24 tick-176                 verify=623s
36034379432 2026-09-24 master                   verify=666s
35981888688 2026-09-24 review-identity-176      verify=575s
35948143167 2026-09-24 master                   verify=493s
35947529595 2026-09-24 observer-log-owner       verify=488s   <- the "488s on #342" baseline
35890416059 2026-09-23 master                   verify=622s
35889056587 2026-09-23 refute-not-confirm       verify=643s
```

**Two things this refutes.**

⑴ **The baseline is the minimum of its own day.** 2026-09-24 alone ran 419, 488, 493, 575, 623, 666,
667, 673, 674, 680, 709. The claimed 39% effect is smaller than the within-day spread, so the two
chosen points cannot distinguish a trend from sampling.

⑵ **The variance is in the sweep itself, not in what was added to the tree.** Two runs **six minutes
apart** on 2026-09-24, both `success`, both full sweeps:

```
36048654618  master        19:32:50 -> 19:42:37   sweep = 587s   (verify 709s)
36049305547  velocity-177  19:38:45 -> 19:44:18   sweep = 333s   (verify 419s)
```

A 1.76× spread between a branch and the master it was cut from, minutes apart. Nothing in the
manifest changed between them.

⛔ **This is the standing hazard *fixing a PREMISE rather than covering the BRANCH*, committed
inside the retraction of the previous instance.** The first comparison was cracked because it set
unlike populations against each other; the replacement is cracked because it sets two points against
each other with no population at all. The retraction taught the row's author about *that* comparison
and not about the class.

**What survives, and I checked it rather than assuming it falls with the rest:** §6's *~81%* sweep
share is robust — measured 379/488 = 78%, 333/419 = 79%, 475/584 = 81%, 551/666 = 83%, 587/709 = 83%.
The share is a within-run ratio, so the runner variance cancels. **Keep §6's share; delete the
39%.** The honest replacement is a sentence with no number in it: *the `verify` job's duration varies
by ~1.7× run to run, so no trend can be read from two samples.*

---

## Medium

### M1
- **severity:** Medium
- **component:** measurement-provenance
- **aim:** deliverable
- **fix_induced:** false

**§6's numbers cite a source that is not in the repository and cannot be reached from a clone.**

The spec's §6 caption: *"(GitHub Actions API, two successful runs. Source: the velocity-ledger page,
§6.)"*

```
$ grep -rn "velocity-ledger" --include=*.py --include=*.md --include=*.sh .
docs/superpowers/specs/…-design.md:73:*(GitHub Actions API, two successful runs. Source: the velocity-ledger page, §6.)*
```

One hit — the citation itself. The page is `~/explainers/2026-09-24-brief-velocity-ledger.html`:
**outside the repository, untracked, on this machine only.** I read it and confirm the spec copies
it faithfully — the crack in H3 is inherited from the ledger, not introduced here — but a reader
who clones this repo has no way to reach the source of §6's table, and **no run ids are given**, so
the table cannot be re-derived either. I identified the two runs only by matching durations:
`36072747242` (680s) and `36070971836` (673s), both on branch `velocity-177`, both 2026-09-24 — so
"two successful runs" means *two runs from the previous day on one feature branch*, presented as
where CI time goes.

**Fix:** name the two run ids inline. That is the whole repair, it costs one line, and it is what
`a-retrospective-number-needs-provenance` asks for — the durable identifier, not the narrative
source. (The spec also cites `check-plan-code.py:501`; the line is correct today — it is the
`subprocess.run([sys.executable, name, "--self-test"], …)` — but the repo's own rule is to cite the
**symbol**, `run_suite_parts`, because a line number is unbound by any edit above it.)

### M2
- **severity:** Medium
- **component:** retracted-figure-still-load-bearing
- **aim:** deliverable
- **fix_induced:** false

**The plan retracts a figure in Task 5 and rests Task 1 on it, and the live document the split hands
it to still asserts it as the whole case.**

Plan Task 1, last bullet: *"⛔ **There is no caught-defect evidence for it** — the case rests
entirely on **the speed measurement**, and §5's *what is lost* stands against it."*

Plan Task 5, last bullet: *"⛔ **Do not justify any of this with the "GitHub is 2× faster" figure.**
… **The corrected ratio is NOT KNOWN.**"*

Task 1's shipped decision is justified by the figure Task 5 forbids citing, with no acknowledgement
that the two bullets are about the same number. And the figure is live and load-bearing where the
spec's own split says measurements belong — `docs/development-velocity.md` §9 Q3:

> *"the measured `verify` job is roughly twice as fast as the local sweep it replaces. **That speed
> measurement is the whole case for the practice**"*

— and `:155`, which states the 8m08s comparison with no caveat at all.

⛔ **The retraction is filed where the claim is not.** By the disjointness split the spec cannot
repair `development-velocity.md`, and it declares it will not (*"It does not move or rewrite"*). So a
reader who follows the pointer to the owning document meets the uncorrected claim, marked *the whole
case*. Correcting a sentence **in place** rather than appending elsewhere is rule 2 of the very
injection rules Task 2 records as shipped.

### M3
- **severity:** Medium
- **component:** backlog-119-quotation
- **aim:** deliverable
- **fix_induced:** false

**The #119 quotation on which both documents' central argument turns is trimmed at the clause that
scopes it.**

Both documents quote: *"writing machine-readable claims into a review record after the fact,
reconstructed rather than recorded, manufactures evidence."*

`docs/backlog.md:147` reads: *"…reconstructed rather than recorded, manufactures evidence **about
review coverage**; the reason is filed here so it is not re-proposed as an obvious cleanup."*

The dropped clause is the scope qualifier, and the spec's entire distinction is a scope argument —
*#119 concerned a review record; this asserts a design exists.* Quoted whole, #119 supports that
distinction more strongly than the trimmed version does, so **this is not a quote shaped to win the
argument; it is a quote shaped to lose it**, which is the more interesting failure: a reader who
opens the source finds text that does not match, and stops trusting the surrounding reconstruction
at the exact point where trust is what is being asked for. `quote-the-code-dont-characterise-it`.

**On the distinction's merits, having read #119 in full:** it holds for the spec and does **not**
hold for the plan, and the plan says so itself (*"applies to this file more strongly than to its
spec"*) — then changes nothing except adding a label. B1 is what that concession should have
produced.

---

## Low

### L1
- **severity:** Low
- **component:** plan-shape-vs-plan-gates
- **aim:** instrument
- **fix_induced:** false

**Both plan gates return CANNOT RUN on this plan, which CLAUDE.md classifies as a failure.**

```
$ python3 scripts/check-plan-task-order.py docs/superpowers/plans/…-RECONSTRUCTED-plan.md
CANNOT RUN: no Interfaces blocks parsed from …-RECONSTRUCTED-plan.md — the plan's shape changed
or the parser is broken. TREAT THIS AS NOT RUN.

next_pending_task -> (before the first task heading)
```

`check-plan-progress._TASK_RE` (`:103`) is `^### (Task \d+:.*)$`; this plan writes `## Task 1 —
draft-PR pattern`. So the armed guard would report `12/25 steps ticked, next: (before the first task
heading)` — a next-step string naming nothing.

⚠ **Not introduced by this plan alone** — prose-shaped plans are common here, and CI runs
`check-plan-task-order.py` with its default target, so nothing goes red. Filed Low because a plan
that the plan gates cannot read is weaker evidence than one they can, and because B1's fix touches
the same grammar: whoever removes the reconstructed `- [x]`es can promote the task headings to
`### Task N:` in the same edit and get `next_pending_task` answering truthfully for free.

---

## Already closed by the r1 fold — not re-filed

Found independently before reading `8e8bbe2e`; recorded so the lead can see the halves agreed, and
so the count is not inflated.

- **The label reached no rendered surface.** My first measurement, on `5996a6d8`: the goals page
  carried `2026-09-25-development-velocity` with spec and plan links and **zero** occurrences of
  *reconstructed*, *retrospective* or *backfill*. Codex filed it as the High; the rename fixes it.
  ✅ **Verified fixed rather than assumed** — regenerated post-fold: `RECONSTRUCTED occurrences: 5`,
  and the pairing survives (`doc_stem` strips both `-design` and `-plan`, so both files still give
  stem `2026-09-25-development-velocity-RECONSTRUCTED` and the page renders **one** thread, not two).
  H0 is what remains of this once the caveat is present.
- Derived measurements copied from `development-velocity.md` (Codex Medium) — folded to pointers.
  H1 is the same defect one level up, at the design rather than the numbers, and is **not** closed.
- *"no mechanism appears twice"* false while Q0 filled three rows (Codex Medium) — folded.
- Shape-invariant history said four fixes where `process-checklists.md:599-601` says five (Codex
  Medium) — folded. This is H2's class, third instance.
- Task 3's hole routed to Task 4 instead of Task 5 (Codex Medium) — folded.
- Per-task checkbox banners (Codex Medium) — folded **as prose**, which is why B1 stands: the
  machine-readable surface got nothing.

---

## What I checked and found clean

| Claim | How checked | Result |
|---|---|---|
| **1,030 mutations** | summed every `scripts/mutations/*.json` | **53 manifests, 1,030 entries — exact** |
| `check-plan-code.py:501` re-runs `--self-test` in a fresh interpreter | read `:492-505` | correct — `subprocess.run([sys.executable, name, "--self-test"], cwd=d, …)` in `run_suite_parts`. Cite the symbol, not the line (M1) |
| **sweep ≈ 81% of `verify`** | five runs, sweep step ÷ job duration | 78 / 79 / 81 / 83 / 83% — **holds**, and survives H3's variance because it is a within-run ratio |
| **2,892 unit tests** | `docs/roadmap-to-launch.md:2284` | `2892 unit / 278 suites` — agrees |
| `review-method.md` §0 begins at dosage | read `:17-25` | correct — Q1 is *"Full loop, or one round?"*, and there is no Q0 |
| `check-anchors.py:54` / `gen-goals-page.py:61` walk only specs+plans | read both `SUBDIRS` | correct — `("superpowers/specs", "superpowers/plans")` in both; the stated reason the backfill exists is sound |
| The backfill does not break the anchor registry | `python3 scripts/check-anchors.py` | `rc=0` — *13 registered, all claimed; every spec/plan dated >= 2026-08-25 declares one; floor 22 held* |
| Documentation gates | `check-docs.py`; `check-plan-file-tags.py` | `rc=0` *Documentation integrity OK*; *plan-mode tags: 0 across 1,495 documents* |
| `decision-card-soundness` as a labelled positive for **signal 4** | `docs/superpowers/specs/2026-09-25-decision-card-soundness-design.md:48` | supported — *"with three synonyms merged to one name"*. ⚠ **Signal 1** (four non-terminating falsifier designs) I did **not** verify — treat that half as unchecked, not as confirmed |
| ⑸ de-escalation vs *Iterative Re-Review* | `dev-process.md` *notify and continue* | the plan's Task 6 caveat is correct and is the right reading |
| §7's calibration falsifier | read the spec's §3 and the plan's Task 4 | **real, and the pre-accepted negative is genuine** — see the note below |

**On the mandate's question about calibration coming back ambiguous.** The design states two
outcomes (separates / does not separate) and pre-accepts the negative, which is more than most
falsifiers here manage. The third outcome is unstated and is the likely one: the signals separate on
*some* branches. Nothing says what happens then. ⚠ It is **not** a finding on its own — an
unenumerated third branch in a calibration that has not been run is a question, not a defect, and
Task 4's *"state the result as a rule, not a count"* is the right instruction for reaching it. Worth
one sentence in Task 4 naming the partial-separation case and who decides. I raise it here rather
than filing it because the repo's own rule is that a review round is the wrong instrument for a
question a single run answers.

---

## Verdict

**NOT CONVERGED.**

**On the specific question — is the labelling sufficient, or should these documents not exist in
this form?**

**The labelling is not yet sufficient, but the form is defensible and I do not think these documents
should be withdrawn.** The distinction the spec draws from #119 — a review record asserts *a review
happened*, a spec asserts *a design exists* — survives reading #119 in full, and PR #345's decisions
are genuinely dated and recorded elsewhere, so the spec is an index over evidence rather than a
substitute for it. The r1 fold's rename is the right fix and it works: the filename is the only
channel the goals page renders, and it now carries the word.

⛔ **But two things must land before this passes a Phase 1 gate, and one of them is the reason the
verdict is not merely "fold the Mediums".**

**⑴ B1 — the mitigation has to reach the machine-readable surface, because that is the surface #119
was about.** Twelve reconstructed `- [x]` boxes parse to `(12, 25)` and no label reaches the parse.
The documents claim *"the label is the whole mitigation"*; that claim is false while a reader exists
that cannot receive labels. The repair is to stop using checkbox grammar for things nobody will
execute — cheap, and it costs the index nothing.

**⑵ H1 — the disjointness claim is false as written, and the spec's own falsifier says so.**
`development-velocity.md` §2 and §3 are the design, not the measurements, and the spec's §2 and §3
are a second copy of them. The fold's repair of the *numbers* duplication made the *design*
duplication more visible, not less. This needs a decision about which document loses the copy, and
it is the one finding here that a further review round will not settle — it is a scope question for
the human gate.

**And H0 is the finding I would put in front of the user first**, because it is about whether the
backfill achieved its purpose at all: the page these files were written for now renders #177 as
`no pull requests`. The caveat arrived; the work state is still wrong, and wrong in the direction
that flatters the backfill — it makes an un-designed, mostly-shipped strand set look like designed
work that has not started yet. A milestone spine in the plan fixes it in the page's own vocabulary,
and would also fill the empty Milestones slot the page already reports as a finding.

**Round 2 should review the fixes, not re-review the documents** — both of 2026-09-13's surviving
defects were in fixes a concurrent pair never looked at, and this round has already folded six
findings unreviewed.
