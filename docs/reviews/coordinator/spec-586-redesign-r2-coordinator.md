# Round 2 — `spec-586-redesign` (PR #552, backlog #586) — coordinator — Codex NOT CONVERGED; folded by SIMPLIFYING

```yaml
round: 2
fixes_nontrivial: true
subject: spec-586-redesign
halves:
  codex: ran
  claude: gap
findings:
  - {id: R2-X1, severity: High, aim: deliverable, fix_induced: true, component: observed-reach-spec, disposition: fixed}
  - {id: R2-X2, severity: High, aim: deliverable, fix_induced: true, component: observed-reach-spec, disposition: fixed}
  - {id: R2-X3, severity: High, aim: deliverable, fix_induced: true, component: observed-reach-spec, disposition: fixed}
  - {id: R2-X4, severity: High, aim: deliverable, fix_induced: true, component: observed-reach-spec, disposition: fixed}
  - {id: R2-X5, severity: High, aim: deliverable, fix_induced: true, component: observed-reach-spec, disposition: fixed}
  - {id: R2-X6, severity: High, aim: deliverable, fix_induced: true, component: observed-reach-spec, disposition: fixed}
  - {id: R2-X7, severity: Medium, aim: deliverable, fix_induced: true, component: observed-reach-spec, disposition: fixed}
```

REVIEW GAP: claude — alternation

Subject: `docs/superpowers/specs/2026-11-09-observed-reach-selection-design.md` at `4686aafc` (the round-1 fold).

- Codex half: `docs/reviews/codex/spec-586-redesign-r2-codex.md` (F1-F7, recorded here as R2-X1..R2-X7), 6 High,
  1 Medium, NOT CONVERGED. Committed on its own with its verdict as `3c13b816`; the fold is the commit after it.

**Every finding sits in a rule round 1's fold ADDED** (the table's last column). So this fold does not add
another layer of path modelling. For each finding it takes the fix that REMOVES modelling and widens either the
refusal (the trace is INCOMPLETE and the target takes today's rule) or the pick. Both keep the spec's
fail-closed property: doubt costs selection savings, never a lost read. Each fix is a mechanism inside the
owner's §7 decisions; none changes one.

**Method.** R2-X7 was checked by hand at this head: `.github/workflows/ci.yml` sets `SEEDS` only when
`EVENT=schedule`, and `mutation_env(d, seed=None)` in `scripts/check-plan-code.py` leaves `PYTHONHASHSEED`
inherited. R2-X1, R2-X3, R2-X4, R2-X5 and R2-X6 were checked against the spec's own round-1 text: each
counterexample walks through the rule as written. R2-X2's strace class membership (`unshare` class 0, `setns`
`TD`) was NOT checked here (no `strace` on this Darwin host); the fold does not depend on it, because it removes
the filter entirely.

## Dispositions

| Finding | Severity | Caused by r1 fold? | Disposition (the SIMPLER fix) | Spec section changed |
|---|---|---|---|---|
| **R2-X1** deleting a directory's last file changes the PARENT's listing; deepest-existing-ancestor misses | High | **y**: rule 3(b)'s deepest-existing-ancestor reading (r1 Claude F8) | FIXED by REMOVING the reading: 3(b) picks when an `A`/`D` path or ANY ancestor at any depth is in `listed`. No model of which directories appear or vanish. This is the reading §5 scored, so 3(b)'s share is no longer an upper bound; the narrowing round 1 promised for `scripts/mutations/`-style additions is GIVEN UP (§5, qualitative) | §2 Use 3(b); §5 scoring note and `scripts/` bullet; §8.3 |
| **R2-X2** the `-e trace=%file,%process,...` filter never shows `unshare`/`setns`, two refusal triggers | High | **y**: trace by strace class (r1 Codex F3, Claude F4) | FIXED by REMOVING the filter: `strace -f -yy -o <log> <argv>` logs every syscall; the parser classifies by name, and a name its table does not hold is INCOMPLETE (`unclassified syscall`). A gap in the table costs a read set, never a lost read; build step 1 fills the table by measurement. Cost: larger logs and more strace overhead (UNMEASURED; it lands only on the recording job) | §2 recorder, INCOMPLETE list, record `trace`, build step 1; §3 row 1; §8.4 |
| **R2-X3** lexical `..` folding before link resolution resolves `outside/link/../flag` to the wrong path | High | **y**: "`..` is folded lexically, then …" (r1 Claude F2's link table) | FIXED by REMOVING the fold: a successful open takes its `-yy` kernel label; a failed or path-only call with a `..` component is INCOMPLETE (`unresolved ..`). No kernel-order resolver is added | §2 normalisation; record `trace`; §3 row 1; §8.4 |
| **R2-X4** listings do not inherit staging provenance (`docs/alias -> real/`) | High | **y**: staging provenance (r1 Codex F5) translated reads/probes only | FIXED by REFUSING, not translating: a target that lists a staged directory at or under a repo directory link is INCOMPLETE (`listed through a link`). A directory that merely holds a link needs nothing: the link is a tracked path, so its `A`/`D` is under that directory | §2 staging provenance; record `trace`; §3 row 1; §8.4 |
| **R2-X5** the cross-run check ignores `listed`, so a created entry in a listed directory launders a flow | High | **y**: the cross-run rule (r1 Claude F5) compared `reads`/`probed` only | FIXED by WIDENING the refusal: a target whose whole-trace `listed` holds any ANCESTOR of a path another target's run wrote is INCOMPLETE. No model of which entry a listing revealed. Renames are covered by R2-X6 (both sides are writes) | §2 cross-run; `listed`/`wrote` scope line; §3 row 1; §4.3; §8.4 |
| **R2-X6** `truncate`, `chmod`, timestamp and other metadata mutations count only as `probed`, not `wrote` | High | **y**: `wrote` extraction (r1 Claude F5) listed its write cases | FIXED by INVERTING the default: a call is a WRITE unless the parser's short, closed READ-ONLY class names it. Every other call naming a path or labelled descriptor writes every path it names, both sides of `rename*` included. Combined with R2-X2, an unlisted call cannot be silently read-only | §2 recorder ("how each call counts"); record `wrote`; §8.4 |
| **R2-X7** PR and push sweeps are unseeded, so "re-run under the seed each side used" cannot replay | Medium | **y**: the flake re-run (r1 Claude F12) | FIXED without changing the sweep: the comparator re-runs a differing mutant 3 times on EACH tree under the SAME fixed seeds; a stable difference under one seed is a miss, anything else (a varying tree, or a difference that does not reproduce) is INCONCLUSIVE, logged with the mutant. PR sweeps stay unseeded, as the coordinator decided on 2026-11-06 (`ci.yml` comment) | §2 *A MISS, precisely*; §8.6 |

**What the simplification costs, stated in §5 without a number.** R2-X1 picks more on additions below a listed
directory (every target that listed `scripts` picks on `scripts/mutations/` additions). R2-X2, R2-X3, R2-X4 and
R2-X5 each send more targets to today's rule. Every one LOWERS the saving; none lowers safety. How much is
UNMEASURED; build step 1 counts refusals by reason, and shadow mode measures the net. No figure was invented.

## Thrashing?

**Not yet, by the arming condition — but this is its early shape, and round 3 decides it.** The condition
(`docs/review-method.md` → *The arming condition — full account*) fires on TWO CONSECUTIVE rounds whose findings
came from the previous round's fix, in one component. Round 1 had none (0 of 20 fix-induced: the first round on
the redesigned text). Round 2 has 7 of 7 fix-induced, each traced to a named round-1 rule: R2-X1 to 3(b)'s
deepest-existing-ancestor reading, R2-X2 to the class filter, R2-X3 to the lexical `..` fold, R2-X4 to staging
provenance's read-only translation, R2-X5 to the cross-run rule, R2-X6 to the `wrote` extraction list, R2-X7 to
the flake re-run. That is ONE fix-induced round. **Not a prose floor either:** every finding is a constructed or
reproduced counterexample in which a read is lost while the trace reads `complete` (or a miss is misjudged), not
an under-specification.

The shape the fold answers is the one *can a redesign remove it?* asks about: six of the seven came from MODELLING
the filesystem more precisely. The fold removes that modelling rather than refining it (route `redesign` in the
decision log). If round 3 still finds a fix-induced High in this component, Phase 6 arms, and round 3 is also the
round cap for this redesign (§0 Q4c): from round 4 findings are FILED unless a BLOCKER.

## NEEDS THE OWNER

None. Every fix is a mechanism inside §7: Q1 B (probes and listings) is kept, Q3 (today's rule where tracing
fails) is the fallback each widened refusal uses, Q4's shadow mode and its 20 complete PRs are unchanged, and the
`strace -f` recorder is kept (only its filter is removed). R2-X7 was fixed without seeding PR sweeps, so the
2026-11-06 call recorded in `ci.yml` is untouched.

## Verdict

**Codex: NOT CONVERGED.** Seven findings, all fix-induced, all fixed by simplification in the spec.

**Next: round 3, ONE half, Claude** (rounds 2+ alternate, `docs/review-method.md` → *Round topology*), on the
fold commit, with `REVIEW GAP: codex — alternation`. Round 3 is the CAP for this redesign (§0 Q4c). Its brief
should ask it to refute the simplified rules: the unfiltered trace and the parser's closed table, the
write-by-default class, the `..` refusal, the listing-through-a-link refusal, the cross-run listed-ancestor
refusal, the any-ancestor 3(b), and the same-seed replay; and to say whether any round-1 rule the fold left in
place (the `CLONE_FS` cwd model, the link table, staging provenance for reads, `git_membership`, `Δ`) would be
simpler as a refusal too.
