# Architecture review — 2026-10-20 — `decision-route-escalation`

**Armed mechanically, not convened by judgement.** `check-review-decision.py` printed:

```
ARCHITECTURE_REVIEW — thrashing: 'corpus-cannot-run' carried fix-induced findings in r2 and r3
  rounds=3  tree_reviewed=False
  scope-rank: NO LEAD — 4 components tied at 3 appearance(s)
```

Three rounds, 50 findings, every r2 and r3 finding fix-induced. Read first: `CONTEXT.md`,
`docs/adr/0014-a-guards-main-is-drivable.md`. ⛔ ADR-0014 is **not** re-litigated below; it is the
rule this slice broke by applying it incompletely.

---

## Where the findings actually are — measured, not recalled

| component | r1 | r2 | r3 | total | reads the world? |
|---|---|---|---|---|---|
| `log-schema` | 4 | 2 | **7** | 13 | partly (`read_log`) |
| `starvation-ratchet` | 4 | 2 | **6** | 12 | **yes** (`tree_at`, `_round_docs`) |
| `coverage` | 1 | 3 | 4 | 8 | **yes** (the manifests measure I/O code) |
| `corpus-cannot-run` | 3 | 1 | 2 | 6 | **yes** (`_corpus_now`) |
| `relocation` | 5 | **0** | **0** | 5 | — (SPLIT out at r1) |
| `accounting` | 3 | 0 | 1 | 4 | no |
| `baseline-validation` | 1 | 0 | 0 | 1 | no |
| `ranker-caller` | 1 | 0 | 0 | 1 | no |

**Of the 28 findings in the two FIX rounds, 64% are in components that read the world.** The pure
core — `route_next`, `route_sequence_error`, `derive_routes_tried`, `scope_lead`, `t2`–`t7` —
converged in one round and has produced almost nothing since. The I/O boundary has not converged in
three.

---

## F1 — ADR-0014 WAS APPLIED TO EVERY WORLD-TAKER EXCEPT THE ONE THAT EXECUTES, AND THAT ONE ANCHORS THE FILE

ADR-0014: *"a guard's `main()` takes its world as a defaulted parameter … `__main__` binds the real
repo, a case binds a temporary tree."* The slice applied this to `main()`, `_corpus_now`,
`_round_docs` and `subjects_starved` — each gained an injectable subject and each is now measurable.
**`tree_at` did not.** It computes `REPO` from `__file__` and passes `cwd=REPO` to `git`.

**The consequence is not local.** Measured with the harness's own `stage_tree` /
`run_suite_parts` / `control_is_green`:

```
scripts/check-decision-scheme.py: rc=1 control_is_green=False
scripts/check-review-decision.py: rc=0 control_is_green=True
```

`mutate_delivered` returns `NotMeasured` for **all 1,623 mutations** — the target is in all 8
round-robin shards. ⛔ **And my own attempt to verify r3's findings in a temp copy failed for the
identical reason**, which is the strongest available confirmation: *no mutation claim about this
file is verifiable anywhere but in place.* Mine, r3's, or CI's.

⭐ **THIS IS THE COMPOSITION DEFECT A PER-TASK REVIEW CANNOT SEE.** Each function individually
either follows ADR-0014 or does not, and a reviewer looking at one change sees a defensible local
choice. The SET fails: one member anchoring to its own file location makes every other member's
coverage unmeasurable. r1 introduced the first git-dependent case; r2's half wrote *"the full
mutation sweep was not run"*; r3's fold added a **second** such case. Three rounds walked past it
because each round's subject was a finding, never the shape.

**The repair collapses four of r3's findings** (ZB1, the `epoch`-severance survivor, the vacuous
instant case, and `probe6`'s need to mutate in place): give `tree_at` an injectable repo, as its
three siblings have.

## F2 — THE RANKER'S STATISTIC SATURATES AT THE ROUND COUNT, AND I CALLED ITS FORCED SILENCE "HONEST" TWICE

`review_scope` counts a component **once per round** — deliberately, so that recurrence is not
confused with a noisy round. Correct, and it has a consequence nobody wrote down: **after N rounds,
every component present throughout ties at N.** Here, four components tie at 3 and the ranker
abstains.

⛔ **I reported that abstention as the mechanism being appropriately humble. Twice.** It is not
humility; it is structural incapacity on exactly the subjects where ranking is most wanted — the
long, everything-recurs loops. And the discrimination is available in the data I threw away:
findings-per-component runs **13, 12, 8, 6**, which is not a tie at all.

⚠ This is a finding against a rule I adopted **the previous day** and defended twice today, and it
is the second worked example for backlog **#136**: *"counts ran 19 → 14 → 2 → 4 while consequence
ran …"* — the axis this process keeps measuring per-finding and then discarding at decision time.
⛔ Do NOT simply switch the ranker to finding counts: that is the noise-sensitivity the once-per-round
rule exists to prevent, and #136 says severity is one axis doing three jobs. The honest output is a
ranking **plus its saturation state** — "4 tied at the ceiling, N=3" is a different message from
"no component recurred".

## F3 — THE ONE ROUTE DECISION THE LADDER EMITTED WORKED, AND IT IS THE ONLY POSITIVE EVIDENCE HERE

`relocation` went **5 → 0 → 0** after route SPLIT moved it to backlog #320. Two subsequent rounds,
both adversarial, zero findings. That is the only component to go quiet, and the only one whose
route was chosen by the ladder rather than by a patch.

⚠ Bounded: n = 1, and "quiet because it was removed from the branch" is a weaker claim than "quiet
because the decision was right". But it is the single datum on the mechanism's side, and the
components that were patched (`corpus-cannot-run`) or redesigned twice (`starvation-ratchet`) are
precisely the ones still producing findings.

## F4 — THE LOG IS FED AT SUBJECT GRANULARITY WHILE THE MECHANISM REASONS IN UNITS

`t1_not_fed` is satisfied by **one row per subject**. Seven units were decided across this slice;
**two** are logged. The five missing are invisible to the trigger whose entire purpose is detecting
that the mechanism is not being fed — and the two the validator refuses (#321) are exactly two of
the five. ⭐ So the starvation trigger has the same blind spot one level down that its predecessor
had: it asks whether the subject appears, not whether the decisions appear.

## F5 — AN INSTRUMENT THAT EDITS THE REPOSITORY IT MEASURES

`probe6.py` writes mutations into the live file and restores them. r3 flagged it, and its own probe
avoided it. It did not overlap a live reviewer this session (checked: every probe run preceded r3's
dispatch), but the hazard is structural, it is a recorded class in this project, and **it exists
only because F1 makes a copy-based probe impossible.** It disappears with F1's repair.

---

## ⚠ What we decided this milestone that is not written down

The review's mandatory question, and four answers:

1. **That the ladder's prefix rule is a design choice, not a law** — discovered by feeding the
   mechanism its own history, filed as #321, written nowhere in `review-method.md`.
2. **That an abstention is not scoreable** — recorded in a code comment only. r3 says the
   documented omission is insufficient: `ranker_hit: null` and `"abstained"` are both *refused* by
   `validate_row`, so abstention is **inexpressible as data**, and with all four rows omitting the
   key, trigger 5 has no reachable falsifier.
3. **That `derive_outcome` stays unwired until its model is evidenced** — in a docstring. Its model
   has now been wrong twice (counts-as-positions, then no-later-round-means-stopped).
4. **That `probe6.py` is the only valid probe** — in a session sentinel, which does not survive.
   Three weaker probes remain on disk and each reports a greener number than the harness.

---

## Findings that become work

All five go to `docs/backlog.md` and the roadmap in this turn. ⛔ **F1 is the prerequisite for every
other coverage claim in this slice**, including the ones already committed — those commit messages
state mutation figures that the gate asserting them cannot produce.

**Verdict: the mechanism's pure core is sound and converged. Its world-reading boundary is not, and
the reason is structural rather than a sequence of mistakes: one function anchored to its own
location made the whole file unmeasurable, and three review rounds each looked at a finding instead
of at that shape.**
