# review-decision-procedure — round 5, coordinator adjudication

```yaml
round: 5
fixes_nontrivial: true
subject: review-decision-procedure
halves:
  codex: ran
  claude: "GAP: this session spawns no subagents"
findings:
  - {id: H1, severity: High, aim: deliverable, fix_induced: false, component: round-sequence, disposition: fixed}
```

* Codex: `docs/reviews/codex/review-decision-procedure-r5-codex.md` (`gpt-5.5`) —
  **0 Blocking, 1 High. NOT CONVERGED.**
* **REVIEW GAP: claude** — as rounds 1–4.

## ⭐ THE OVERRIDE WAS TESTED AND UPHELD, BY THE REVIEWER, ON ITS OWN REASONING

r4 recorded an override of the thrashing arming condition, with a falsifier. r5's brief
asked the reviewer to attack the override itself and to name a redesign that would dissolve
the `tests/` / `.claude/` / `.agents/` question. It could not:

> *"A model like 'prose vs executable/operational influence' or 'blast radius by authority'
> still has to decide whether tests, hooks, skills, and agent instructions carry enough
> authority to require full-loop. That is not a carve-out-list failure in the r1–r3 sense;
> it is the contained-set boundary itself. I would uphold the coordinator's override."*

**A recorded falsifier was handed to an independent judge and survived.** That is the whole
point of `:102` refusing a silent override.

## ⛔ SELF-FOUND, AND CORRECTED: THE OVERRIDE WAS BEING ENACTED BY A LABEL

Before r5 landed, the coordinator noticed that `check-review-decision.py` had stopped
reporting `ARCHITECTURE_REVIEW` — **not because it knew of the override, but because r4's
finding had been labelled `component: scope-policy` while r3's was `scope-for`.**
`thrashing_component` intersects components; two names, no overlap, no thrashing.

⚠ **The metric was satisfied by a labelling choice** — the exact defect
`docs/round-header-template.md` warns about: *"a header filled in dishonestly produces
confident wrong answers, and nothing detects that."* It was not dishonest, it was an
adjudication written into a name; the effect is identical and **invisible**, which is worse
than being wrong out loud.

**Corrected:** r4's component is renamed to `scope-for`. The tool now reports
`ARCHITECTURE_REVIEW`, r4's document overrides it in writing with a falsifier, and r5 upheld
the override. A reader sees the disagreement **and** its resolution.

⚠ **Filed, not built:** the header has no `override:` field, so the tool cannot report the
arming and the override together. Adding a schema field mid-branch is how rounds 1–3 went.

## H1 — adjacency was inferred from LIST POSITION

**ACCEPTED AND FIXED.** `rounds_for()` sorted by `round` but never rejected gaps or
duplicates; `converged()` then sliced `rounds[-need:]` and `thrashing_component()` compared
`rounds[-2]`/`rounds[-1]`. Codex confirmed in-process that **`r1 + r3` returns converged for
a full-loop branch**, and that two documents claiming one round count as two consecutive
rounds.

⛔ **A lost round became a false STOP.** Codex names the contradiction exactly: *"this
violates the tool's own 'missing input is failure, never pass' posture."* The tool held that
posture about round documents and about headers, and not about **the sequence they form**.

Not fix-induced — an original sequencing gap the recorded-evidence model exposed.

**Fixed** with a pure `sequence_error()`: rounds must be a gapless `1..N` with no duplicates
and no missing numbers, or `decide()` returns **`CANNOT_RUN`** and `main()` exits 2. Six
cases; one mutation, red via the two cases that name it.

## What Codex cleared, with evidence

`r10` vs `r1` sorts numerically, not lexically. The r4 classifier stand-in is **not**
silently green — under it the full-loop scope cases go red, as designed. Sample card
citations resolve, including `:169`, `:273`, `:345`, `:400` and `:454`. `TREE` exiting 1 was
considered and **not** filed: it is action-required rather than a round owed, and the script
declares `NO-CALLER`, so nothing in CI gates on it.

## Verified on this tree

```
check-review-decision --self-test  55/55   (49 before)
mutations 6 -> 7; EXPECTED_MUTATIONS 635 -> 636
control: adjacency reverted to list position -> 2 cases red, both named
check-plan-code --self-test  128/128
```

**NOT CONVERGED — round 6 owed.** H1's repair is unreviewed code, and the branch is
full-loop, so convergence needs two consecutive rounds with neither a Blocking/High nor a
finding in the deliverable.
