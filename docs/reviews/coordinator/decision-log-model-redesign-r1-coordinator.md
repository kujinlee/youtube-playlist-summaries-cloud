# Round 1 — `decision-log-model-redesign` — coordinator

```yaml
round: 1
fixes_nontrivial: true
subject: decision-log-model-redesign
halves:
  codex: ran
  claude: ran
findings:
  - {id: XB1, severity: Blocking, aim: deliverable, fix_induced: true,  component: log-schema,          disposition: fixed}
  - {id: CB1, severity: Blocking, aim: deliverable, fix_induced: true,  component: log-schema,          disposition: fixed}
  - {id: CB2, severity: Blocking, aim: deliverable, fix_induced: false, component: ranker-caller,       disposition: fixed}
  - {id: CB3, severity: Blocking, aim: deliverable, fix_induced: true,  component: starvation-ratchet,  disposition: fixed}
  - {id: XH2, severity: High,     aim: deliverable, fix_induced: true,  component: starvation-ratchet,  disposition: fixed}
  - {id: XH3, severity: High,     aim: deliverable, fix_induced: true,  component: starvation-ratchet,  disposition: fixed}
  - {id: XH4, severity: High,     aim: deliverable, fix_induced: true,  component: log-schema,          disposition: fixed}
  - {id: XH5, severity: High,     aim: deliverable, fix_induced: true,  component: log-schema,          disposition: fixed}
  - {id: CH1, severity: High,     aim: instrument,  fix_induced: false, component: ranker-caller,       disposition: fixed}
  - {id: CH2, severity: High,     aim: deliverable, fix_induced: true,  component: log-schema,          disposition: fixed}
  - {id: CH3, severity: High,     aim: deliverable, fix_induced: true,  component: starvation-ratchet,  disposition: fixed}
  - {id: CH4, severity: High,     aim: deliverable, fix_induced: true,  component: log-schema,          disposition: fixed}
  - {id: CH5, severity: High,     aim: deliverable, fix_induced: true,  component: log-schema,          disposition: fixed}
  - {id: CH6, severity: High,     aim: deliverable, fix_induced: true,  component: starvation-ratchet,  disposition: fixed}
  - {id: XM6, severity: Medium,   aim: deliverable, fix_induced: false, component: corpus-cannot-run,   disposition: fixed}
  - {id: XM7, severity: Medium,   aim: deliverable, fix_induced: false, component: log-schema,          disposition: fixed}
  - {id: XM8, severity: Medium,   aim: deliverable, fix_induced: true,  component: ranker-caller,       disposition: fixed}
  - {id: CM1, severity: Medium,   aim: deliverable, fix_induced: false, component: log-schema,          disposition: fixed}
  - {id: CM2, severity: Medium,   aim: deliverable, fix_induced: true,  component: log-schema,          disposition: fixed}
  - {id: CM3, severity: Medium,   aim: instrument,  fix_induced: true,  component: log-schema,          disposition: fixed}
  - {id: CM4, severity: Medium,   aim: deliverable, fix_induced: true,  component: log-schema,          disposition: fixed}
  - {id: CM5, severity: Medium,   aim: deliverable, fix_induced: false, component: log-schema,          disposition: fixed}
  - {id: CM6, severity: Medium,   aim: instrument,  fix_induced: true,  component: ranker-caller,       disposition: fixed}
  - {id: CM7, severity: Medium,   aim: deliverable, fix_induced: true,  component: log-schema,          disposition: fixed}
  - {id: CL1, severity: Low,      aim: deliverable, fix_induced: true,  component: log-schema,          disposition: filed}
```

**Subject:** `docs/superpowers/plans/2026-10-20-decision-log-model-redesign.md` — the **design review**
the thrashing escalation owes (`review-method.md:178`), not another defect hunt on the code.
Halves: [`codex/`](../codex/decision-log-model-redesign-r1-codex.md) (`gpt-6.1-sol`, `gate_ran=true`),
[`claude/`](../claude/decision-log-model-redesign-r1-claude.md). Both **NOT CONVERGED**.
Round 1, so both ran **concurrently** per the topology; the Claude half records that it did not read
the Codex half, which was already on disk.

## ⭐ The two halves agreed on four defects, independently

Agreement between halves is the strongest signal this process produces, and it is rarer than
disagreement. All four were reached by construction, not by reading:

| defect | Codex | Claude |
|---|---|---|
| The row model + append-only + "existing rows not rewritten" returns **rc=2 for ever** | XB1 | CB1 |
| `total_findings` is **not** noise-safe at equal recurrence | XM8 | CB2 |
| The readability figure uses the corpus this slice itself corrected — **57 → 82 subjects, 18% → 13.4%** | XM6 | CB3(b) |
| My §2.5 claim that a miss is inexpressible today is **false** | XM7 | CM5 |

## ⛔ The two claims of mine they refuted, both verified by hand before acceptance

1. **"Today no log can make t5 FAIL."** FALSE. Two rows on distinct units with `ranker_hit: false`
   both return `validate_row → None`, and the real `main()` returns **rc=1, `FAIL trigger 5 RANKER
   MISS`**. Re-run independently here, not accepted on testimony. ⚠ **My own probe had printed
   `ranker_hit=False -> None` on screen and I wrote the opposite sentence next to it.** #325's real
   shape is narrower: an *abstention* is inexpressible (`None` and `"abstained"` both refused), so it
   must be encoded as absence (invisible) or as `false` (scored as a miss) — which is what the code
   comment already said and what the design should have said.
2. **"10 of 57 subjects (18%)."** The population is the one `baseline.json` preserves under
   `corpus_ORIGINAL_WRONG`. Today: **82** subjects with ≥2 rounds, **11 readable (13.4%)**, and over
   the rule's actual domain — `(subject, round)` pairs — **46 of 395 = 11.6%**. The error direction
   favoured my conclusion, so the conclusion survives; the sentence that justified the design did not.

## The structural finding, which neither the backlog nor I had

**#323 does not belong in the unification.** The Claude half could not construct a reading in which
`(unit, bet)` recorded as `(subject, prediction)` produces it: `review_scope` ranks components over
**round documents**, never touches the decision log, and has no `unit`, no `bet` and no row — §3's own
table says it *"reads the corpus, not the log"*. Folding it in is what let §2.3 be written without the
constraint the rest of the document observes, and §2.3 is where two of the three Claude Blockings land.

**The unification holds for #321, #324, #325 — three of four, measured, not claimed.**

## ⭐ #321 blocked this round too, which is its second independent occurrence

#321 was filed because the ladder refuses two of the four routes the slice actually took. **Feeding
*this* round's route decisions hits the same wall**: `log-schema` was given REDESIGN at r1 without an
ACCRETE, so no row for it is admissible, and the component carrying 10 of this round's 25 findings is
the one the log cannot discuss. The finding has moved from *found by use* to **blocks use twice**, and
the second occurrence is on the round convened to fix the first.

## Mutation coverage — the gap the Claude half flagged is now closed

That half recorded *"treat the mutation coverage of every new branch as NOT MEASURED by this half"*
because a sweep was in flight. It has since been measured, by the harness rather than a probe, over a
pruned `HARNESS_TREE` copy with the two subjects' manifests:
**62 mutations, 62 killed, 62 attributed to the case each names, 0 survivors** (`43` +`19`, matching
`EXPECTED_MUTATIONS` in both directions), 57 seconds.
⚠ The **full** 1,625-mutation sweep remains CI's, by design, and CI fires at the PR — which this work
has not earned. A local full run was started and abandoned at 413/1,625; the prior session had already
closed that question by delegation and I reopened it.

## Q4 — another round is owed

`fixes_nontrivial: true`, four Blocking, ten High. The fixes are a redesign of the redesign, and
unreviewed code cannot converge. **Round 2 is owed and ALTERNATES — Codex alone**, per the topology
(a concurrent pair never reviews the fixes, which is where both of 2026-09-13's surviving defects were).

⛔ **Thrashing watch, stated now rather than discovered later:** 19 of these 25 findings are (DERIVED by `rounds_for` + the header parser; this said 18 when I counted prose)
`fix_induced: true`, and `log-schema` carries 12 of them. If round 2 returns fix-induced findings in
`log-schema` again, the arming condition fires on a component **inside a document written because it
already fired** — which is the shape that would say this mechanism should be DEFERRED rather than
redesigned again.
