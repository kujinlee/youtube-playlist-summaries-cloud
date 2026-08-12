# Adversarial review — `docs/understanding-gate-spec.md` (v2)

**Date:** 2026-08-12
**Reviewed file:** `docs/understanding-gate-spec.md` — 475 lines, md5 `70e1f50814afdd63cbb4e5d442fd2150`, untracked (`git status` = `??`), repo at `727135a`
**Spec version:** v2 (DRAFT, Phase 1 review gate)
**Reviewer:** Claude (Claude half of the dual adversarial review, round 1)

> ⚠ **The file changed under me mid-review.** My first read returned 451 lines; a re-read minutes later
> returned 475, with a new `PENDING` record form and a new *"Stated limit — this gate cannot verify a
> mind"* paragraph (lines 268–318) that were not in the first version. **Every anchor below is against
> the 475-line / `70e1f50…` version.** If the file has moved again, re-check the anchors before acting
> on any finding.

---

## B1 — Blocking

**Claim:** The record is written by *editing the PR body at merge time*, and a `pull_request` workflow
does not fire on a body edit — so the required status check can never observe the transition that
satisfies it. The sequence the spec requires is unsatisfiable.

**Failure scenario.** Agent opens PR #99 at head `a1b2c3d` with
`Understanding check: PENDING against a1b2c3d — …` (spec:281). CI runs on `opened`;
`check-understanding-record.py` sees `PENDING`, exits 1 (spec:299), the required check goes red — as
designed. Days later the human returns, takes the quiz, and edits the PR body to
`Understanding check: 4/5 against a1b2c3d …` (spec:288). **No workflow run is triggered.** GitHub
Actions' `pull_request` event defaults to the activity types `opened`, `synchronize`, `reopened`;
`edited` is not among them, and `.github/workflows/ci.yml:14-18` declares no `types:` filter:

```yaml
on:
  pull_request:
    branches: [master]
```

The last recorded conclusion for the check remains the red `PENDING` run. The merge stays blocked. The
only way to force a re-run is to `synchronize` the PR — push a commit — which moves the head, which
makes the freshly-written `4/5 against a1b2c3d` name a SHA that is *not* the PR's current head, which
is itself a stated failure condition (spec:299, U3 at spec:403). **Pushing to unblock the gate
invalidates the record you pushed to validate.**

This is the project's own signature shape: *unsatisfiable-ordering-is-the-tell* — the requirement is
"X must be true when Y observes it", and no interleaving exists in which Y observes X.

**Anchor:** spec:270–306 (the durable record, "It binds to the MERGE, not to opening the PR"),
spec:403 (U3), `.github/workflows/ci.yml:14-18`.

**Premise tag.** The GitHub-side half — that `pull_request` defaults exclude `edited` — is an external
premise about GitHub Actions, not repo code. It is standard documented behaviour and I am confident in
it, but it is the one load-bearing claim here I could not verify by reading this repo. The repo-side
half (no `types:` filter, `gh` never invoked in CI) is verified. **If that premise is wrong, B1
collapses to H5 and nothing else changes.**

---

## B2 — Blocking

**Claim:** The answer key ships inside the artifact being graded. Combined with self-reported scoring
and no stated first-click lock, 5/5 is reachable by clicking — with no dishonesty and no understanding.

**Failure scenario.** The renderer refuses any quiz where "any question lacks a **per-option
explanation**" (spec:222), and the page gives "`Q1 ( ) ( ) ( ) ( )` ← **feedback after click**"
(spec:345), in a "single self-contained HTML file. Inline CSS and JS" (spec:251). So every option's
correctness and rationale is in the file the taker holds, revealed on click. Nothing in the spec says
the first click locks the answer, that the score is computed from first attempts, or that the key is
obscured. A tired human clicks A, is told it is wrong and why, clicks B, is told it is right — five
times — and then types `5/5 against a1b2c3d` into the PR body, which is the *only* thing the script
reads.

This is not the honesty problem the spec acknowledges at spec:308 ("Nothing stops someone typing
`5/5`"). That paragraph concedes deliberate faking. **This is the mechanism silently converting a test
into a tutorial for an honest taker**, and the honest taker's self-report is then indistinguishable
from a real 5/5. Litt's users found the published quiz was passable by picking the longest option;
this version is passable by picking every option.

**Anchor:** spec:222 (refusal condition 4), spec:345 (feedback after click), spec:251 (inline JS),
spec:288 (self-typed score).

---

## B3 — Blocking

**Claim:** The override counter is blind to the cheaper escape route. A false `4/5` costs fewer
keystrokes than `OVERRIDDEN — reason: <why>`, so the valve the script counts is the one nobody will
use — and a running total of `0` will read as evidence the gate is healthy.

**Failure scenario.** Model the steady state the brief asks for: 20 code-touching PRs under time
pressure. Two exits exist from a merge you want now:

| Exit | What you type | What the script records |
|---|---|---|
| Honest override | `Understanding check: OVERRIDDEN against a1b2c3d — reason: <a defensible sentence>` | counted, visible, printed in a running total |
| Skip the quiz | `Understanding check: 4/5 against a1b2c3d (quiz by codex) — explainer …` | **indistinguishable from a real pass** |

The spec deliberately makes the override "not shorter to type than doing the check" (spec:291) — but
it does not, and cannot, make it shorter than *claiming* to have done the check. The design pressure
therefore points at the untracked exit. The override count will sit at zero not because the gate is
working but because nobody has any reason to use the expensive door, and *"a valve nobody counts is a
valve nobody notices is stuck open"* (spec:301) will be satisfied about the wrong valve.

The rationale the spec cites for D4 is *hardcode-only-what-fails-loudly* (spec:198) — sort a check by
what happens when it goes stale. Applied here, the answer is: it goes stale **silently**, and the one
instrument pointed at the failure mode reads green throughout. That is the same class as the
known-red-suite normalisation the brief asks about, one layer worse: a known-red suite is at least
visibly red.

**Anchor:** spec:189–199 (Grading + D4 rationale), spec:291–302 (the two record forms + the counter),
spec:431–433 (D4).

---

## H1 — High

**Claim:** U5 — the only instrument in the whole spec that tests *"can this be passed without
understanding?"* — is unrunnable as specified, and even if it were runnable it fires exactly once,
ever.

**Failure scenario.** The mutation check is: *"Answer the five questions with the explainer closed and
only the PR title in front of you. If you can score ≥ 4/5, the check is not a guard"* (spec:186-187),
and U5 promotes it to a gate on "the quiz for the **first real explainer**" (spec:405).

There is no order in which the same human can perform both takes:

- **Closed-book first, then the real quiz** — the human has now seen all five questions and their
  option sets. The real quiz is contaminated; its 4/5 means nothing.
- **Real quiz first, then closed-book** — the human has read the explainer and seen every per-option
  explanation (B2). They cannot un-know the answers; the closed-book take is contaminated, and will
  score high for the wrong reason, *failing* U5 on a quiz that may be perfectly good.

The spec never states which order applies, and both are broken. A second person could run it, but the
spec's own N3 states the project is "one human plus agents" (spec:55-57).

Scope compounds it: U5 is bound to *the first* explainer (spec:405, spec:420-421). After PR #1, no
instrument in the spec ever again asks whether a quiz is passable without understanding. M3's four
refusal conditions are the standing guard and they check SHAPE only, by their own admission
(spec:224-226). So the answer to the brief's question 2 — *"is the stated mutation check itself
falsifiable and actually runnable?"* — is: it is falsifiable in principle, not runnable by the person
specified, and not standing.

**Anchor:** spec:183–187 (mutation check), spec:405 (U5), spec:55-57 (N3), spec:224-226.

---

## H2 — High

**Claim:** M3's position-balance refusal condition audits the renderer's **own output**. If the
renderer assigns option order, the condition can never fire — a guard that passes in both worlds,
inside the mechanism introduced to fix a guard that passed in both worlds.

**Failure scenario.** Three statements in the spec are mutually inconsistent about who owns option
order:

- spec:71 — M3 is "deterministic renderer **owning option order** and parity";
- spec:346 — "… five, **order shuffled by the renderer**";
- spec:220 — the renderer **refuses to render** when "correct-answer positions across the five
  questions are not balanced (no position used more than twice)".

If the renderer shuffles, the position distribution is its own product: it can always place the
correct answers to satisfy its own rule, so the refusal branch is unreachable and its `--self-test`
case (U1, spec:401) can only be exercised against a synthetic input the real pipeline never produces.
A `--self-test` that is green on a branch no caller reaches is precisely the "mutation harness reports
INVALID = untested" shape recorded in this project's memory.

If instead the renderer *validates* an agent-supplied order and refuses, then spec:71 and spec:346 are
wrong and the fairness guarantee is back in the prompt — the thing M3 exists to move out of the
prompt (spec:156-159).

Secondary, on the threshold itself: "no position used more than twice" over five questions and four
options permits 2+2+1+0 — 80% of correct answers concentrated in two positions, versus 50% expected.
@fm1randa's complaint was *"usually the second option"*; the rule as written still allows the second
option to be correct 40% of the time against a 25% baseline.

**Anchor:** spec:71, spec:203–222, spec:346, spec:401.

---

## H3 — High

**Claim:** M4 arms off the four-round trigger and never mentions the **two-round** REDESIGN trigger
created by the very retrospective M4 cites as its evidence — and it contradicts N4.

**Failure scenario.** `docs/review-method.md:45-46` states:

> **If a component produces findings caused by the PREVIOUS round's fixes in two consecutive rounds,
> it escalates from FIX to REDESIGN, and the next round is a design review — not another defect hunt.**

and `docs/review-method.md:48-49` adds *"Two, not three. The stable-blob-addressing reservation hit it
at round 9 and ran to round 12 anyway."* That rule was added 2026-08-09 — the same date as
`docs/reviews/blob-addressing-retrospective-2026-08-09.md`, which is M4's cited evidence (spec:382-383).

So the concern *"sequence/interleaving defects survive prose review"* already has a mechanism, it fires
at **two** rounds, and M4 arms at **four** — after the existing rule has already mandated a redesign.
The spec's "What already does this?" table (spec:88) names only Phase 6 and answers with a
characterisation, not the `file:line` the section demands (`docs/process-checklists.md:192`:
*"Answered with a `file:line`. 'Nothing does' is a fine answer; a vague answer is the finding."*). The
closest existing mechanism was missed.

Second half, the N4 contradiction. spec:58 says *"**Not a Phase 6 replacement.** Milestone architecture
review stays exactly as it is."* The four-round trigger's only current consumer **is** Phase 6
(`docs/dev-process.md`, Phase table: *"per **milestone** — **or after 4 review rounds without
convergence**, whichever comes first"*). M4 then says: on that trigger, "build the micro-world
**instead of** running a fifth prose round" (spec:378). Under an ordering-shaped finding set, does
Phase 6 run, does the micro-world get built, or both? N4 says Phase 6 is untouched; the arming
condition says the micro-world displaces what that trigger fires. Two mechanisms, one trigger, no
stated precedence — the concern→mechanism table's stated invariant ("Every concern has exactly ONE
mechanism", spec:64-65) is violated by M4 and the table does not show it, because the table only lists
*new* mechanisms.

Note also that `scripts/check-vocabulary-collisions.py` — the instrument this project built for exactly
this failure — reads `pg_catalog` for eight named tables (`scripts/check-vocabulary-collisions.py:44-48`).
It cannot see process vocabulary at all. There is no automated backstop here; the concern→mechanism
table is the only instrument, and it missed this.

**Anchor:** spec:58, spec:72, spec:88, spec:372–384; `docs/review-method.md:45-49`;
`docs/dev-process.md` Phase 6 row; `docs/process-checklists.md:189-197`.

---

## H4 — High

**Claim:** D2's independence property is unverifiable, and the spec asserts the opposite in a sentence
that does not survive reading.

**Failure scenario.** spec:170-171: *"The header block records which agent authored it, so the property
is checkable after the fact rather than assumed."*

The property is *blindness to the explainer*. The header block records a **name** (`Quiz author: <the
reviewer agent…>`, spec:264). A name is not evidence of blindness, and the header block lives in the
explainer, i.e. it is emitted by the party whose independence is in question. Nothing in the spec
produces an artifact from which a later reader could distinguish:

- a quiz author dispatched with only the diff, from
- a quiz author dispatched by a coordinator that had the explainer in its own context and paraphrased
  it into the prompt, from
- the explainer's author writing both and stamping `codex` in the header.

In this project's actual execution model both agents are dispatched from one coordinator session that
holds the explainer — the same structural leak that `docs/plugins.md` records for the Codex gate
("the gate can FAIL OPEN — verify it actually ran"), and there the fix was to read the **output file**,
not to trust a name. No equivalent exists here.

The correct statement is "assumed, not checkable". Because D2 is the *whole* answer to Defect B
(spec:161-165) — the one thing this spec claims to fix that the upstream community did not — an
unverifiable D2 means M2's headline advantage is an honour claim resting on top of B3's honour claim.

**Anchor:** spec:161–171, spec:264, spec:422–427; `docs/plugins.md` — "The gate can FAIL OPEN".

---

## H5 — High

**Claim:** The head-SHA binding and the merge-time write are mutually hostile: any head-moving step
that is *part of merging* invalidates the record that was just written, and the spec does not say what
happens next.

**Failure scenario.** This is the second half of B1 and stands independently of B1's GitHub premise.
The record is valid only while the SHA it names is the PR's current head (spec:299, U3 at spec:403),
and it is written at merge time (spec:284-285). Between writing it and merging, several ordinary
operations move the head: resolving a conflict, rebasing onto master, GitHub's *Update branch* button,
or one last review-fix commit. Each turns a green record red and — per the spec's own logic — requires
a **new** explainer (the SHA is in the filename, spec:237-243), a **new** independently-authored quiz,
and a **new** human sitting. There is no "re-stamp the same score at a new SHA" path, and there
shouldn't be, because that would dissolve the SHA binding that is M5's entire purpose.

The spec's own motivating example makes the cost concrete: PR #67 was "39 commits across 7 review
rounds" (spec:32-33). It cites that PR as evidence *for* the gate without modelling what the gate would
have done to it.

**Anchor:** spec:32-33, spec:237–249, spec:284–299, spec:403.

---

## M1 — Medium

**Claim:** The renderer's **input** format — the JSON content spec — is entirely unspecified, though it
is the interface between the two agents and the subject of three of the four refusal conditions.

**Failure scenario.** spec:205: *"The agent emits a **JSON content spec**; `scripts/render-explainer.py`
renders the HTML."* That is the only description. No schema, no field names, no example, no statement
of how the correct option is flagged, how per-option explanations attach, how the two authors' outputs
(explainer body from one agent, quiz from another) are combined into one document, or which of them
runs the renderer. Refusal conditions 1, 3 and 4 (spec:219-222) are all predicates over this
unspecified structure.

`docs/process-checklists.md:164` requires, for projects that write files, "filename convention (with
example), required frontmatter/header fields, and **an annotated sample file body**". The spec gives
the filename convention (spec:236-243) and the header fields (spec:259-266), and substitutes an ASCII
box of the *rendered page* (spec:326-350) for the annotated sample body. The output body is sketched;
the input contract is absent. This is the "present-but-hollow" case the brief's question 8 asks about.

**Anchor:** spec:205, spec:219–222, spec:230–266; `docs/process-checklists.md:164`.

---

## M2 — Medium

**Claim:** The spec's own gates are invisible to the falsifiability ratchet whose form they adopt, and
U5's `VERIFIED AGAINST:` does not match the mechanised form it invokes.

**Failure scenario.** Two independent mismatches with `scripts/check-gate-falsifiability.py`:

1. **Scope.** `GATE_SCOPES` (`scripts/check-gate-falsifiability.py:55-58`) is
   `{"docs/m1.4-finishup-checklist.md": None, "docs/roadmap-to-launch.md": ["## M1","## M2","## M3"]}`.
   Neither `docs/understanding-gate-spec.md` nor `docs/process-checklists.md` (where the new section
   lands, spec:448) is scanned. Additionally `CHECKBOX_RE`
   (`scripts/check-gate-falsifiability.py:87`) matches `- [ ]` list items; U1–U5 are **table rows**.
   Even if the file were in scope, the parser would not see them.
2. **Form.** `VERIFIED_AGAINST_RE` (`scripts/check-gate-falsifiability.py:86`) is
   `r"VERIFIED\s+AGAINST:\s*v(\d+)"` — it requires a release number. U5 writes
   "**VERIFIED AGAINST:** the PR it was generated for, **by SHA**" (spec:405), and a SHA does not match
   `v\d+`. spec:407 claims U5 "carries a `VERIFIED AGAINST:` by construction, per the same section" —
   it carries the *words*, not the form the section's enforcement recognises. Were the file ever added
   to `GATE_SCOPES`, U5 would be reported as `unversioned_tick`.

Neither is fatal to the design, but both mean the spec's gates get the *appearance* of the project's
enforced convention without any enforcement — which is the exact category of defect the convention was
written to catch.

**Anchor:** spec:395–407; `scripts/check-gate-falsifiability.py:55-58`, `:86`, `:87`.

---

## M3 — Medium

**Claim:** U2 names no instrument and is over-broad to the point where a conforming page fails it.

**Failure scenario.** U2: *"FAILS IF a rendered explainer contains any external asset reference
(`http://`, `https://`, `//`, `src=`, `@import`) outside a code block…"* (spec:402).

- **No instrument.** M3's four refusal conditions (spec:219-222) do not include an external-asset scan.
  The `white-space` half of U2 *is* assigned ("the renderer verifies this per block before writing",
  spec:252-253); the asset half is assigned to nobody. Per the project's own gate rule, the clause
  names an observation but nothing is stated to be able to make it.
- **Over-broad.** The literal token `//` appears in every JavaScript line comment, and the page requires
  inline JS (spec:251) to deliver click feedback (spec:345). `src=` bans an inline
  `<img src="data:image/svg+xml,…">`, which is a *self-contained* asset and exactly what "no external
  network access" should permit. As written, a correct explainer fails U2, and a gate that fails on
  correct output gets switched off — the failure mode `check-gate-falsifiability.py:321-325` calls out
  as the reason ratchets exist.

**Anchor:** spec:402, spec:219–222, spec:251–253, spec:345.

---

## M4 — Medium

**Claim:** The renderer is bound to the ratchet contract, which does not fit it, and one clause of the
binding is contradicted by D3.

**Failure scenario.** spec:213-215: the renderer "takes the `docs/process-checklists.md` ratchet
contract: `--self-test`, **exit 0 at baseline / 1 above**, mutation-verified discriminators, declared
scope, and it **must never write inside the repo**."

- A renderer has no baseline and no debt count. "Exit 0 at baseline / 1 above" (`docs/process-checklists.md:260`)
  is a statement about a ratchet's *count of violations*; for a renderer it is uninterpretable, and
  applying it invites the next reader to invent a baseline that means nothing.
- **"Never write inside the repo" is contradicted by D3.** The actual contract rule
  (`docs/process-checklists.md:276`) is *"**Never mutate repo-tracked files.** Mutate a temp copy"* —
  narrower, and satisfiable. The spec's restatement is stricter, and the renderer's entire job is to
  write `.explainers/…html` at the **repo root** (spec:242, D3 at spec:428). Gitignored is not outside
  the repo. As written the requirement is unsatisfiable by the tool it constrains.
- Note the discovery mechanism: `scripts/check-ratchet-contract.py:58-73` discovers ratchets from CI
  step names containing "ratchet" and from `scripts/check-*.py` docstrings containing "ratchet".
  `render-explainer.py` does not match the glob and will never be discovered;
  `check-understanding-record.py` **does** match the glob, so if its docstring says "ratchet" it is
  discovered and must carry `--self-test` — which the spec never states it has. `BASELINE = 4`
  (`scripts/check-ratchet-contract.py:43`); a discovered ratchet without `--self-test` makes it 5 and
  fails CI.

**Anchor:** spec:213–215, spec:242, spec:428; `docs/process-checklists.md:260`, `:276`;
`scripts/check-ratchet-contract.py:43`, `:58-73`.

---

## M5 — Medium

**Claim:** The CI wiring is under-specified and self-contradictory, and `gh` cannot run in this repo's
CI today — which under U4 means every PR goes red.

**Failure scenario.** spec:304-306 requires the check be *"Wired as a **required PR status check**,
separate from CI correctness… It must not be folded into the existing CI job."* The "Files this
touches" table (spec:451) lists exactly one CI change: `.github/workflows/ci.yml` — "wire
`check-understanding-record.py` (PR events only)". A separate *job* in the same workflow would satisfy
both readings, but the spec never says which, and "separate from CI correctness" plus "the existing CI
workflow file" is at minimum unresolved.

Concretely blocking on the mechanics: `.github/workflows/ci.yml` contains **no `permissions:` block and
no `GH_TOKEN`/`GITHUB_TOKEN` env** (verified by grep — zero matches), and `gh` is invoked nowhere in
it. `gh pr view` without a token fails. Per U4 (spec:404) and spec:317-318, that must exit 1 with
*treat this as NOT RUN* — correct behaviour, and it means the required check is red on every PR from
the moment it merges until someone wires auth. The spec does not mention the token.

**Anchor:** spec:298, spec:304–306, spec:317–318, spec:404, spec:451; `.github/workflows/ci.yml`
(no `permissions:`, no token, no `gh`).

---

## M6 — Medium

**Claim:** The "running total" of overrides has no stated source, and the durable record lives only in
GitHub — invisible to `git log`, which `docs/dev-process.md` names as the ground truth for session
resume.

**Failure scenario.** spec:300-302: *"Overrides are counted, not blocked: the script prints a running
total."* The script "reads the PR body via `gh`" (spec:298) — one PR. A running total requires
enumerating historical PRs (`gh pr list --state all --limit …`, paginated), which is a different query
with different failure modes and its own "cannot run" branch. None of it is specified, and neither U3
nor U4 covers it: a script that prints `overrides: 1` because it only looked at one PR satisfies both
gates.

Separately, the record's medium is a GitHub PR body — editable after merge with no trace in the repo,
absent from `git log`, and unavailable offline. `docs/dev-process.md` → *Session Resume* says to verify
progress from `git log --oneline`, the files on disk, and (per `docs/portable-practices.md:84-91`) the
running system. The understanding record appears in none of the three. The spec calls it "the only part
that survives" (spec:270-271); it survives in the one place this project's reconciliation procedure
never looks.

**Anchor:** spec:270-271, spec:298–302; `docs/dev-process.md` — *Session Resume*;
`docs/portable-practices.md:84-91`.

---

## M7 — Medium

**Claim:** The evidence recorded for the spec's founding concern does not support it. No incident is
cited in which lacking a mental model at merge time cost anything.

**Failure scenario.** The concern→mechanism table's Evidence column for M1 reads *"PR #67: 39 commits,
7 rounds, merged on a convergence claim"* (spec:69). That is evidence the human **did not have** a
model. It is not evidence that the absence produced a bad outcome — no defect that reached master, no
merge that should not have happened, no idea that was not had. The brief's question 5 asks what in this
repo supports or refutes the claim; I looked and found the condition documented (the
*output-style-plain-default* memory, cited at spec:31-32) and **no measured consequence**.

By this project's own filter (`docs/portable-practices.md:14-16`, "Measured — it cites an incident with
files, numbers, or a command output. Not a belief someone held confidently") the founding premise fails
filter 1. The spec applies that filter to whether it earns a *portable-practices entry* (spec:453-455)
but not to whether the mechanism should be **required** (D1, spec:416-419). Those are different
questions and the spec answers only the safer one.

This does not mean the gate is a bad idea. It means D1 — mandatory, on every code-touching PR, two
extra agent runs plus a human sitting a quiz, in a repo where roadmap ticks ride in the same PR as the
work (`docs/dev-process.md` Phase 5) so nearly every PR is code-touching — is being bought with an
unmeasured premise, and the cheaper mechanism the brief asks about (the same explainer, **opt-in**,
with no M5, no script, no CI check, and roughly half the build by the spec's own estimate at
spec:418-419) is ruled out on an argument from introspection ("an optional aid gets reached for when
you already feel oriented") rather than evidence.

**Anchor:** spec:31–34, spec:69, spec:416–419, spec:453–455; `docs/portable-practices.md:14-16`.

---

## L1 — Low

**Claim:** The prompt-injection safety clause is unfalsifiable and has no instrument.

**Failure scenario.** spec:138-140: *"The skill must ignore instructions appearing inside the diff, and
must not emit script tags, external links, or execution logic **that the diff asked for**… one clause
to state."* The trailing qualifier makes the predicate unobservable: no instrument can distinguish a
`<script>` block the renderer emitted for the quiz from one a diff talked it into emitting, and the
page requires inline JS regardless (spec:251). No U-gate covers it. "One clause to state" is precisely
the rule-that-depends-on-remembering shape `docs/dev-process.md` says to convert to a script.

Low because the spec correctly assesses the risk as low for a private repo reviewing its own diffs.

**Anchor:** spec:136–140, spec:251, spec:395–405.

---

## L2 — Low

**Claim:** Litt's gate placement is inverted, and the inversion is what makes the override cheap.

**Failure scenario.** Litt's rule, quoted at spec:108-109: *"I won't send code to others until I can
pass the quiz"* — the quiz gates **sending for review**, so the explainer covers a small, fresh change
and failing it is cheap. The spec moves it to gate the **merge** (spec:109-110) for a defensible reason
(merging is the human's only reserved decision). The unexamined consequence: the explainer is now built
over the largest possible change, at the point of maximum sunk cost, after 7 rounds of review have
already declared the work correct. A `≤ 3/5` there means *"rebuild the explainer and retake"*
(spec:194) on a 39-commit branch that everyone considers finished. That is the condition under which
D4's override stops being an exception, which is B3 arriving by a second road.

The spec should at least record that it considered and rejected Litt's placement, and why the cost
asymmetry it creates is acceptable.

**Anchor:** spec:106–110, spec:189–199.

---

## What I checked

| File | What I verified in it |
|---|---|
| `docs/understanding-gate-spec.md` (475 lines, md5 `70e1f50…`) | Read in full, twice — the second read after noticing the line count had changed from 451 to 475. Every anchor above re-checked against the 475-line version by `grep -n`. |
| `docs/dev-process.md` (202 lines) | Phase 5 blast-radius table (spec's scope table matches it); Phase 6's dual trigger — "per **milestone** — **or after 4 review rounds without convergence**"; the Session Resume three-step; the Conditional AFK rule the spec's PENDING form is built on; the line-budget sentence. |
| `docs/process-checklists.md` (276 lines) | `:45`/`:47` (spec's M2 citations — **verified correct**: line 45 is the Claude review step, 47 the Codex step); `:164` (Output File Format requirement, incl. "annotated sample file body" — **absent from the spec**, M1); `:189-197` ("What already does this?" demands a `file:line` — H3); `:200-233` (Writing a GATE); `:216` (spec's M5 citation — **verified correct**, `VERIFIED AGAINST: vN`); `:235-276` (Writing a RATCHET), specifically `:260` (exit semantics) and `:276` ("Never mutate repo-tracked files", **not** "never write inside the repo" — M4). |
| `docs/review-method.md` | `:38-71` — the two-round REDESIGN stop condition at `:45-46`, "Two, not three" at `:48`, and "Convergence is not enough on its own" at `:70`. This is H3's anchor and the spec never mentions it. |
| `docs/portable-practices.md` (122 lines) | `:12-21` (the two filters — M7); `:46-56` (§2, "cannot run" is a FAILURE); `:58-70` (§3, gates state a failing observation); `:73-80` (§4, the tick/subject rule the spec's M5 leans on — the analogy holds for *subject binding* and does not extend to *content verification*, B3); `:84-91` (§5, reconciliation reads the running system — M6). |
| `docs/plugins.md` | The Codex fallback rule the spec's D2 relies on — **verified**: unavailability is treated as routine and mandates a fresh Claude subagent rather than blocking, so D2's "bind to the property, not the reviewer" is well-founded. Also read "The gate can FAIL OPEN — verify it actually ran", which is the precedent H4 rests on: there, trust was moved from a name to an output **file**. |
| `CONTEXT.md` (97 lines) | Confirmed **artifact** (`:44-49`), **generation** (`:57`) and **reader** are load-bearing product nouns, and that "explainer", "comprehension check", "understanding check" and "micro-world" appear nowhere. **The spec's terminology claim at spec:95-101 is correct and I found no collision.** |
| `scripts/check-gate-falsifiability.py` (356 lines) | `GATE_SCOPES` at `:55-58` (the spec's file is not in scope); `CHECKBOX_RE` at `:87` (table rows are not matched); `VERIFIED_AGAINST_RE` at `:86` (requires `v\d+`, not a SHA); `:28` — "So this catches SHAPE, not TRUTH", which the spec quotes at spec:226 — **verified correct**. → M2. |
| `scripts/check-ratchet-contract.py` (228 lines) | `BASELINE = 4` at `:43`; the two-source discovery at `:58-73` (CI step names + `scripts/check-*.py` docstrings); the six-rule table at `:13-21` showing which rules are enforced. → M4. |
| `scripts/check-docs.py` | `LINE_BUDGETS` at `:190-192`: `dev-process.md` = 220, currently **202** — so the spec's "one pointer row" (spec:449) fits with ~18 lines of headroom. **No finding**; the spec is right about this. `process-checklists.md` has no budget, so routing the new section there is correct. |
| `scripts/check-vocabulary-collisions.py` | Scope is `pg_catalog` over eight named tables (`:44-48`). It **cannot** observe process-level duplicate mechanisms, so it is not a backstop for H3. |
| `.github/workflows/ci.yml` | `on: pull_request: branches: [master]` at `:14-18` with **no `types:` filter** (B1); no `permissions:` block, no `GH_TOKEN`/`GITHUB_TOKEN`, and `gh` invoked nowhere (M5); the five existing ratchet/doc steps at `:59-100`. |
| `.gitignore` | `:30` is `/.screenshots/` — **the spec's citation at spec:247 is correct.** |
| `.claude/skills/zoom-out/SKILL.md` | `:7` — verified. The spec's quote (spec:84) is accurate but truncates the trailing clause "using the project's domain glossary vocabulary". Does not affect the argument; not filed as a finding. |
| `docs/architecture.html`, `scripts/publish-arch-page.sh`, `docs/reviews/blob-addressing-retrospective-2026-08-09.md` | All three exist on disk. Every file path the spec cites resolves. |

### NOT CHECKED — say so loudly

- **The external sources.** I did not open the Litt talk, the thread unroll, the gist, or its 14
  comments. Every quotation attributed to Litt, @Butanium, @fm1randa, @yudhiesh-oc, @ankitg12 and
  @ehsan-ami is **unverified** by me. B2, H1 and L2 argue about the spec's *own* mechanism and do not
  depend on those quotes being accurate; but if the Provenance table is wrong, the spec's framing of
  what upstream measured is wrong with it, and that is untested here.
- **GitHub Actions `pull_request` default activity types.** B1's central mechanism. This is documented
  GitHub behaviour, not something in this repo, and I did not run anything to confirm it. Flagged
  inline; treat B1's severity as conditional on it.
- **`scripts/render-explainer.py` and `scripts/check-understanding-record.py` do not exist.** Nothing
  about their actual behaviour was observed — U1–U4 are judged as *specifications*, not as tools.
- **PR #67's body and history.** I did not run `gh` to inspect the 39 commits / 7 rounds claim; I took
  it from the spec and from the repo's memory index. H5's cost argument rests on it.
- **The `AI Augments Human Understanding in Development.docx` source** referenced at spec:471. Not
  read; the spec's characterisation of it is unverified.

---

## Verdict

**NOT CONVERGED** — three Blocking, five High. What earns it: I traced the record's lifecycle against
`.github/workflows/ci.yml:14-18` and found no interleaving in which the status check observes the
satisfying edit (B1); I traced the answer key from refusal condition 4 (spec:222) to the click-feedback
page (spec:345) into a self-typed score (spec:288) and found the quiz gradeable by exhaustion (B2); and
I read `docs/review-method.md:45-49` and found M4's concern already has an earlier mechanism the
"What already does this?" table missed (H3). Any one of those is enough; the third is the one this
project's own history says matters most.

**Severity counts:** Blocking 3 · High 5 · Medium 7 · Low 2.
