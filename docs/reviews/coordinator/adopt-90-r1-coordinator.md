<!-- codex-review: model=gpt-5.5 -->

PROOF OF SUBJECT: `scripts/check-group-claims.py` declares `python3 scripts/check-group-claims.py --self-test  # 24 cases`; frozen `GROUPS` has 6 entries.

**Blocking**
- `scripts/mutations/check-group-claims.json:7` and `scripts/mutations/check-group-claims.json:18` repeat the same edit anchor, so the delivered mutation gate refuses before measuring coverage. Observation: in a complete staged tree from `70b2166` plus the local TypeScript oracle, `python3 scripts/check-plan-code.py --mutate .` exits 1 with `entry 'the falsifier check stops stripping...' repeats the edit anchors of an earlier entry — it measures nothing new`, and CI runs that exact gate at `.github/workflows/ci.yml:378`. This invalidates the shipped claim “8 mutations, all verified to attribute.” I did verify three individual non-duplicate mutations against a green control; they attribute, but the full manifest still does not run.

**High**
- `scripts/gen-backlog-page.py:1398` keeps the index outside `GROUPS`, and `scripts/check-group-claims.py:35` says that is the mechanical barrier. It is not a real guard against the retired bin returning as framed prose. Observation: changing only the index dek to a catch-all framing claim while leaving it outside `GROUPS` still gives `gen-backlog-page.py --self-test` `164/164` and `check-group-claims.py` exit 0. So what stops someone adding the framing sentence next month is review discipline, not this guard.

**Checked, No Finding**
- Completeness invariant is not tautological in the deleted-index direction: suppressing the index made the suite fail the two index cases and `every open item reaches the page exactly once`.
- Retired triggers fire: `Sync` has one open member (#32); `Small visual polish` includes #7 size `S` and open `product / renderer` is exactly #4/#5/#6/#7.
- Retagging status cells were unchanged for the retagged six-column rows I compared; #9/#10/#11 remain in the three-column table with no Bundle cell.
- `SUMMARIES` split preserved 70 summaries byte-identically against `e597a8e7`.
- `check-group-claims.py` CANNOT RUN arms I exercised return nonzero (`2`), not fail-open.

Verification note: the exact frozen archive requested omits `supabase` and `node_modules/typescript`, so `check-plan-code.py --self-test` is red there. With those harness dependencies staged, it passes `128/128`; the mutation gate then fails on the duplicate anchor above.

VERDICT: NOT CONVERGED

---

## Round 1 remediation, recorded by the coordinator

**BOTH findings accepted. Both were right, and the Blocking is the more instructive.**

### Blocking — duplicate edit anchors. ACCEPTED, and my verification was the defect.

Two entries shared the anchor `if not str(falsifier).strip():`, so `--mutate .` refuses the WHOLE
manifest — `NOT MEASURED`, no verdict for the file — and the shipped claim *"8 mutations, all
verified to attribute"* was false.

⛔ **The reason I did not catch it is the point.** I did not run the harness; I wrote a stand-in
that applied each edit and asked whether the named case went red. It answered 8/8. **It did not
implement the duplicate-anchor rule at all**, so its rule was WEAKER than its subject's and it
reported a pass the subject refuses. That is `a-second-implementation-of-one-rule-drifts`, an
error this repo has now recorded EIGHT times, and I wrote *"⚠ A STAND-IN, NOT THE HARNESS"* at the
top of the very script that then misled me. Labelling the hazard is not avoiding it.

**FIXED STRUCTURALLY, NOT BY RENAMING AN ANCHOR.** The two mutations guard two different things —
"the clause is gone" and "the clause stops stripping" — so the clause is now two lines
(`stated = str(falsifier).strip()`, then `if not stated:`) and each mutation anchors its own. ⚠ **I
then made the identical mistake again within the hour** on rule 4's dek comparison, and caught it
only because I had started checking anchor distinctness programmatically instead of by eye. Both
are two-line now, and the reason is written at both sites.

**The real harness is running over all 524 mutations.** The stand-in is not trusted again.

### High — the index barrier was review discipline wearing the word "mechanical". ACCEPTED.

The reviewer's refutation was exact and reproducible: reword the index dek into a catch-all framing
claim, leave it outside `GROUPS`, and everything stays green. Measured again here — it did.

**RULE 4 now exists.** `INDEX_TITLE` and `INDEX_DEK` are constants in the generator; this guard
holds its own copy and refuses when they diverge. ⚠ **It still cannot judge whether prose is a
claim, and the docstring now says so instead of implying otherwise.** What it buys is that
rewording the index is a deliberate act touching two files and failing CI until both agree.

**FALSIFIER, the reviewer's own experiment re-run against the fix:** rewording the dek to
*"Instruments and habits. Cheap individually…"* — the retired bin's actual framing — moved the
guard from **rc=0 to rc=1** with a message naming why it is pinned. Whitespace is normalised, so a
re-wrap is not a false alarm; that has its own case and its own mutation.

Cases 24 → 30, mutations 8 → 11, `EXPECTED_MUTATIONS` 521 → 524.

REVIEW GAP: claude — not invoked. Only the adversarial half ran, as in rounds 1-3 of the previous
branch. ⚠ Note what that cost here: the Blocking was found by the reviewer running the REAL gate,
which is precisely the check a self-review does not perform on itself.
