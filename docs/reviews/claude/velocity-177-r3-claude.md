# Claude adversarial review — velocity-177 r3

Subject: the r2 fold, `git diff e44be4b0..HEAD` (commit `b49e0c7a`), against the whole branch
`git diff origin/master...HEAD`. Docs-only. PR #345, backlog #177.

## Verdict

**NOT CONVERGED — 1 High, 1 Medium, 1 Low. CONTINUE.**

The four numbers survive a third, independent method (and it is a strictly stronger method than
r2's — see *What I checked*). The counts are not the problem any more. **The problem is that the
wrong `34` still stands in two places inside rule 1b, one of which is the exact line r2's own half
named, and which the r2 coordinator doc records as `disposition: fixed`.**

These are **not prose preferences.** H1 is a contradiction between two sentences six lines apart,
checkable by reading. L1 is a heading count. Only M1 is judgement-shaped, and I flag that it is.

**STOP is not available yet** — but it should be reachable in one more round, because the fix that
closes H1 is a shape change that leaves no number in the rule prose to go stale.

## Thrashing assessment

### ⛔ IT FIRES. This is link two in `number-populations`, and the coordinator should not litigate it.

r2's M1 was `fix_induced: true`, component `number-populations`
(`docs/reviews/coordinator/velocity-177-r2-coordinator.md:11`). Link two:

| Finding | New text from the fix? | Fix-induced? |
|---|---|---|
| **M1** — the ⛔ paragraph at `:483-487` overclaims | **100% new.** `git blame` attributes `:483-487` entirely to `b49e0c7a` | **Unambiguously yes** |
| **H1 site B** — `:487-488` exemplar | the *line* is attributed to `b49e0c7a`; the *token* `34` predates it | **Yes on effect:** before the fix the sentence was consistent with the section (all `34`); the fix made it a **contradiction** with text it added six lines above |
| H1 site A — `:476` | untouched by the fix | **No** — this is an *unrepaired* half of r2's own finding, not a new one |

⚠ **Stated honestly, because the call is load-bearing:** link two rests on M1 (clean) and H1-B
(strong but contestable). If the coordinator rejects M1 *and* reads H1-B as "the token predates the
fix", the fix-induced link is not there. **That does not save the round**, because the repo's own
primary test answers independently:

> `docs/review-method.md:200` — **Can a redesign remove it?**

**Yes, and the redesign is already written down twenty lines below the defect.**
`docs/process-checklists.md:517-521`, rule 3's ⚠ note, made exactly this call for exactly this
reason: *"The survivor COUNT is deliberately not quoted here… the number belongs to the measurement
that produced it, where it can be checked. Quoting it here would break rule 1 inside the section
that argues for rule 1."* Rule 1b does the opposite — it quotes four counts and a generalisation in
its prose, and that prose has now produced a finding in **three consecutive rounds** (r1 H2/M4,
r2 M1, r3 H1). Per `review-method.md:195`, findings the fixes keep producing that a different shape
would dissolve are **mechanism** defects, and the action is **REDESIGN**.

⚠ **Thrashing or prose floor? — THRASHING, and here is the per-finding evidence the rule demands**
(`dev-process.md`, *THE ARMING CONDITION IS THRASHING, NOT A COUNT*). The prose-floor signature is
findings shifting to wording while the substance improves. That is not what these are: H1 is a
factual contradiction, L1 is a countable mismatch against five `###` headings. Nothing here is a
rewording request.

⚠ **Proportionality, offered as information and not as an argument against the firing.** The owed
redesign is confined to one ~20-line section (`:468-489`) and its shape is already in the same file
at `:517-521`. Convening a full Phase 6 architecture review over it would measure a subject three
lines wide. Routing that is the coordinator's call; the trigger having fired is not.

## Findings

### H1 (High) — the wrong `34` still stands twice in rule 1b, and one site was named by r2 and recorded as fixed

**Site A — `docs/process-checklists.md:476`**, row 1 of rule 1b's evidence table:

    | *"28 gates named"* | distinct `scripts/check-*.py` in one workflow | the regex excluded `.sh`; "gates" names steps (54), scripts (34) or workflows — not this |

The cell offers `scripts (34)` as the correct population count. It is wrong: **33** scripts are
invoked. Three lines below it, `:479` — the row the fix *added* — says so in its own words:
*"`grep` over the file's **text** — 33 are invoked"*. The table now contradicts itself.

⛔ **This is the line r2's reviewer pointed at by number.** `docs/reviews/codex/velocity-177-r2-codex.md:6`:
*"Same bad `34` also appears in rule 1b's table at [docs/process-checklists.md:476]."* I confirmed
the cite resolves: `git show e44be4b0:docs/process-checklists.md | sed -n '476p'` is that row,
verbatim. The fix repaired the other site r2 named (old `:530`, now `:538`) and added a row
narrating the error — **and left the line the reviewer indexed untouched.** The r2 coordinator doc
records `disposition: fixed` (`velocity-177-r2-coordinator.md:11`). Half of it is not fixed, which
makes that disposition itself an unverified claim — the class this whole branch is about.

**Site B — `docs/process-checklists.md:487-488`**, the *prescriptive* clause, i.e. the sentence
telling the reader what a correct sentence looks like:

    sounds identical to the one you meant and is not. Write *"34 distinct scripts
    invoked by `ci.yml`"*, never *"34 gates"*.

Read in flow, the paragraph establishes that `grep` gives a near-identical-sounding wrong answer and
then instructs the reader to **write the wrong answer**. The phrase *"34 distinct scripts invoked by
`ci.yml`"* is, word for word, the string `:479` files as the r2 Medium and `:538` corrects to 33.
`git blame -L 487,487` attributes the line to `b49e0c7a` — the fix commit reflowed this sentence and
re-set the number unchanged, six lines under its own correction.

⚠ Secondary: *"never `34 gates`"* names a sentence nobody wrote. The original defect was
*"28 gates named"* (`:476`), not *"34 gates"*.

**This defeats the branch's stated goal** (mandate 6): a reader who follows rule 1b as written
produces the defect rule 1b exists to stop.

**Siblings — searched, HOW, and what turned up.** `grep -rn` over `docs/ .github/ scripts/` for
`34 distinct`, `34 gates`, `scripts (34)`, `(34)`, `**34**`, then a bare `grep -n "34"` over
`docs/process-checklists.md`. Five hits in the deliverable, all in this section: `:476` (defect),
`:479` (legitimate — files 34 as the error), `:487` (defect), `:488` (the `34 gates` residue),
`:543` (legitimate — *"The first version said **34**"*). **Zero** hits outside
`docs/process-checklists.md` in `docs/`, `.github/` or `scripts/`, excluding `docs/reviews/`.
`docs/development-velocity.md` carries no count. So the class is two members, both above.

**Fix that also closes the class:** apply rule 3's own policy (`:517-521`) to rule 1b — take the
counts out of the rule prose and let the measurement at `:538-539` own them. `:476` becomes
*"'gates' names steps, scripts or workflows — not this"*; `:487-488` becomes a form template with no
digit, e.g. *"Write 'N distinct scripts invoked by `ci.yml`', never 'N gates'."* Nothing in the
section then has a number that can go stale, which is what ends the stream.

---

### M1 (Medium, fix-induced) — the new ⛔ paragraph's generalisation is supported by two of its four rows, and one row is a counter-example

`docs/process-checklists.md:483-487`, entirely new text from `b49e0c7a`:

> A rule that catches its own author while he is writing it down is not a rule about carelessness —
> **the slip is in how measuring works**, because `grep` answers a question that sounds identical to
> the one you meant and is not.

Mandate 2 asked whether this is a nice sentence doing work the evidence does not. **It partly is.**
Scoring the four rows it rests on:

| Row | Is it "a command answering a near-identical question"? |
|---|---|
| `:476` *"28 gates named"* | **Yes** — a regex that excluded `.sh` |
| `:477` *"the draft PR caught #176 r2's Blocking"* | **No.** This is a causal attribution about what caused a finding. No command was run and no population was miscounted; the source *disclaims* the cause. Nothing about measuring produced it |
| `:478` *"derive from `ci.yml`"* | **Partly** — a file-scope error. The author chose the wrong input, not a command that answers a near-identical question |
| `:479` *"34 distinct scripts invoked"* | **Yes** — text match vs invocation |

Two of four support it cleanly; `:477` sits inside the evidence table as a counter-example to the
sentence the table is cited for. Per rule 3 in this same document (`:502`, *a class claim requires a
class SWEEP*), a claim over "the four rows" needs the four rows. The honest version is narrower and
loses nothing: *the two rows that came from a command show `grep` answering a near-identical
question; `:477` shows the same failure without any measurement at all, which is why rule 1b is
about the label, not about the tool.*

⚠ **I am flagging this as the softest of the three.** It is a judgement about whether a
generalisation is earned, and a reasonable reader could call it rhetoric rather than a claim. I file
it because the document's own rule 3 is the standard being applied, not my taste — and because it is
the only **unambiguously** fix-induced finding, so the thrashing call rests on it.

**Siblings — searched.** Re-read every ⛔/⚠ generalisation added on this branch
(`git diff origin/master...HEAD -- docs/process-checklists.md docs/development-velocity.md`,
grepping added lines for `⛔`/`⚠`/`**`). The other bolded generalisations in the section
(`:449-451`, `:517-521`, `:531-535`) each either cite a specific artifact or explicitly narrow
themselves. No second instance.

---

### L1 (Low) — "four rules" names a population of five

- `docs/process-checklists.md:452`: *"All four rules below cost nothing to follow."* Five `###`
  headings follow: `:454` (1), `:468` (1b), `:491` (2), `:502` (3), `:525` (4). `1b` was added in
  the r1 fold; the count above it was not.
- `docs/development-velocity.md:192-195` outlines the adopted rules as four — *"provenance of
  numbers, fixing a sentence in place, a class claim requiring a class sweep, and deriving gate
  lists"* — and **omits 1b entirely**. Rule 1's own ⚠ (`:459-463`) insists 1b is a different rule
  from rule 1 (*provenance* vs *population*), so folding it in is not available as a defence there.
- `docs/process-checklists.md:489`: *"all three answered **yes**"* now sits under a four-row table.
  Defensible (it refers to r1's three, and `:470` says so), but it reads as a count of the table.

⚠ **The reading that makes `:452` correct** is that `1b` is a sub-rule of `1`. I am not asserting it
is wrong so much as that two documents now disagree about whether 1b is a rule, which a reader hits
immediately. Cheapest fix: drop the count at `:452` ("The rules below cost nothing to follow") and
add population to the velocity outline.

**Siblings — searched.** `grep -n "^### [0-9]" docs/process-checklists.md` for every numbered rule
block in the file, then grepped the file and `development-velocity.md` for `four rules`, `five
rules`, `all three`, `all four`. Hits: the three above. No others.

## What I checked and found clean

**The four numbers — re-derived by a third method, and it is stronger than r2's.**
r1 grepped the file text; r2 used a YAML library then regexed the raw `run:` text. My method 3 is a
hand-rolled indentation-aware block-scalar extractor with **no YAML library**, which then **strips
shell `#` comments inside each `run:` block** (quote-aware) before extracting paths — a step neither
prior method had. Result on the real files:

    ci.yml            run: blocks 54 · whole-file text 34 · in run: blocks 33 · INVOKED 33 · check-* invoked 28
    schema-gates.yml  run: blocks 10 ·                  4 ·                4 · INVOKED  4 · check-*         3
    text-only, never in a run: block: ['scripts/check-schema-gates.sh']

**All four adopted numbers (33 / 28 / 54 / 4) confirmed.** `:538-539` is correct as written.

⚠ **The counter was mutation-tested, because a counter that cannot be wrong proves nothing.** Three
mutations on temp copies of `ci.yml`, each killed by the case it names:

| Mutation | Expected | Observed |
|---|---|---|
| A — add a real `run:` invocation | steps 54→55, invoked 33→34 | 55 / 34 ✅ |
| B — add the path in a YAML comment only | text 34→35, invoked **unchanged** | 35 / 33 ✅ |
| C — add the path in a **shell comment inside a `run:` block** | r2's raw method 33→**34**; mine **unchanged** | raw 34, invoked **33** ✅ |

Mutation C is the point: `33` survives a method that would have caught a class r2's method could
not. On the real file the two agree only because `ci.yml` happens to have no such mention.

**Command-position audit.** Classified all 53 `scripts/*.py|sh` occurrences in `ci.yml` by what
precedes them. Four are in comments (`:66`, `:126`, `:267`, `:453`); three of those scripts are
invoked elsewhere, so only `scripts/check-schema-gates.sh` is comment-only. Every one of the 33 is
in a command position behind `python3`/`bash`. Spot-checked the four non-`check-*` members, which
are the easiest to get wrong: `:165` `brief-compose.py --self-test`, `:303` `begin-plan.py
--self-test`, `:391` `page_markup.py --self-test`, `:400` `page_chrome.py --self-test` — all real
invocations. So **"invokes"** is the right verb for the 33, not merely "mentions".

**`:543-546`, the comment-only claim — verified.** `scripts/check-schema-gates.sh` at `ci.yml:267`
is inside `# Their only automated caller was scripts/check-schema-gates.sh`. `ci.yml:286` reads
`# catalog-reading run stays in check-schema-gates.sh` — note it carries **no `scripts/` prefix**,
so it is outside the `scripts/*.py|sh` population being counted. Both are comments, so the sentence
is true; flagging only that the second cite is a bare filename, in a paragraph about populations.
Not filed.

**`:530`, the `check-merge-ready.py:52-55` cite — exact.** The comment occupies lines 52-55 and its
quoted words match verbatim.

**Rule 4's recommendation does not contradict its own ⛔.** `check-merge-ready.py:56` pins
`WORKFLOW = ci.yml`, which looked like the single-file defect the ⛔ above warns about. It is not:
`:440` and `:452` iterate `workflow_files(WORKFLOW_DIR)` over **every** workflow, and `:250-265`
account for every `pull_request` mention in `schema-gates.yml` by hand with reasons. `:56`'s scope
is only "the steps this script can itself invoke", as its inline comment states. The claim *"it
derives its own, and it reaches the pull-request-only gates a local run cannot"* holds.

**`scripts/check-docs.py`: green** — *"Documentation integrity OK"*, 143 ADR refs, 79 living-doc
links, with the standing 21-document ADR advisory (pre-existing, not this branch).

**Followability (mandate 6): yes, subject to H1.** I read `:425-546` straight through as a reader
with no access to `development-velocity.md`. Every rule states its trigger, its action and a worked
example without leaving the file; rule 4 hands off to a runnable command. The split achieves its
goal. The one place a reader is actively misled is `:487-488`, which is H1 site B.

**Whole-branch coherence.** `git diff origin/master...HEAD` touches 12 files; the four
non-review deliverables are `process-checklists.md` (+153), `development-velocity.md` (+161),
`roadmap-to-launch.md` (±36), `backlog.md` (1 line), plus dashboard entries. The §6/§7 banners in
`development-velocity.md:190-196` and `:219-230` are pointers, not copies — I checked for a third
copy of the rule text by grepping `docs/` for `No number unless`, `class SWEEP`, `Fix the sentence
IN PLACE` and `Derive gate lists`: each appears once outside `docs/reviews/`. r1 M3 stays fixed.

**Not checked / CANNOT RUN — stated rather than implied.** I did not re-run the unit suite,
`tsc`, the schema gates or `check-plan-code.py --mutate .`; the change is documentation only and
r2's half recorded CI `verify` green on this tree. I did not re-derive the historical figures
quoted at `:446-448` (`1858 → 1869`, `183/184 verdicts`) — they are quotations of prior findings, and
re-deriving them needs the trees they were measured on. **Treat those two as NOT VERIFIED by r3.**
