# Round 3 (the CAP) — `spec-586-redesign` (PR #552, backlog #586) — coordinator — Claude NOT CONVERGED; STOPPED AT THE CAP, folded by REFUSALS

```yaml
round: 3
fixes_nontrivial: true
subject: spec-586-redesign
halves:
  codex: gap
  claude: ran
findings:
  - {id: R3-C1, severity: High, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: R3-C2, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: R3-C3, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: R3-C4, severity: Medium, aim: deliverable, fix_induced: true, component: observed-reach-spec, disposition: fixed}
  - {id: R3-C5, severity: Medium, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: R3-C6, severity: Medium, aim: deliverable, fix_induced: true, component: observed-reach-spec, disposition: fixed}
  - {id: R3-C7, severity: Low, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: R3-C8, severity: Low, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: R3-C9, severity: Low, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
  - {id: R3-C10, severity: Low, aim: deliverable, fix_induced: false, component: observed-reach-spec, disposition: fixed}
```

REVIEW GAP: codex — alternation

Subject: `docs/superpowers/specs/2026-11-09-observed-reach-selection-design.md` at `31e94dd8` (the round-2 fold).

- Claude half: `docs/reviews/claude/spec-586-redesign-r3-claude.md` (F1-F10, recorded here as R3-C1..R3-C10),
  1 High, 5 Medium, 4 Low, plus 12 places an implementer must guess. NOT CONVERGED. Committed on its own with
  its verdict; the fold is the commit after it.

**Round 3 is the CAP for this redesign** (`docs/review-method.md` §0 Q4c). Its findings are folded, as rounds up to
the cap are. Every fix prefers a REFUSAL to a model, which is round 2's lesson: where a round-1 rule modelled
something no suite reaches today (staging provenance, the real checkout's `.git`, the link table), it is
replaced by an INCOMPLETE trace. Each refusal fails closed: doubt costs selection savings, never a lost read.
Each fix is a mechanism inside the owner's §7 decisions; none changes one.

**Method.** The reviewer's MEASURED figures were re-checked by hand at this head before they were cited in the
spec: `grep -l GITHUB_WORKSPACE scripts/*.py` gives 0; `git ls-files -s` mode `120000` gives 21 paths, all
under `.claude/skills`; `HARNESS_TREE` (`scripts/check-plan-code.py`) is `scripts`, `supabase`, `docs`,
`node_modules/typescript`, `.claude/hooks`, `.github/workflows`, `.agents/skills`, `.githooks`, so no tracked
link is staged; `grep -l DEVNULL scripts/*.py` gives 17; `seed_trees`' docstring states the within-tree mutant
exposure; the comment above `SEED_MAX` says "about 1 in 120"; `stage_tree` COPIES `node_modules/typescript`
(it is not under the workspace). The strace behaviours (the ` (deleted)` suffix, log interleaving, the `-yy`
label on every descriptor) were NOT checked here (no `strace` on this Darwin host). The fold does not depend on
them being exact, because each one is met by a refusal.

## Dispositions

| Finding | Severity | Caused by r2 fold? | Disposition | Spec section changed |
|---|---|---|---|---|
| **R3-C1** a probed DIRECTORY appears or vanishes through a descendant's `A`/`D`; 3(a) compares exact paths only | High | **n**: 3(a) reads the same as before r1; the PROBE twin of r2's listing fix (R2-X1) | FIXED by WIDENING the pick: an `A`/`D` path P also picks when ANY ancestor of P is in `reads` or `probed`, mirroring 3(b). Cost: about nil (INFERRED: `scripts` is already listed) | §2 Use 3(a); §5 note; §8.3 (both directions, with an adjacent negative) |
| **R3-C2** a hash-order read under a PR's random seed is in neither fixed seed's set | Medium | **n**: round 1's union rule | FIXED by REFUSAL: differing seed sets are INCOMPLETE (`seed-dependent reads`), not unioned. Agreeing seeds that still miss a third order are stated as §4's new bound 5 | §2 Record; record list; §3 row 1; §4.5; §8.4; §8.5 |
| **R3-C3** another target's MUTANT writes in the shared tree are unrecorded, yet §4.3 claimed cross-run flows were out of the bound | Medium | **n**: round 1's claim | FIXED by RESTATING: a flow through another target's mutant run is IN §4.3's bound (same family as §4.1), citing `seed_trees`; no mechanism added | §2 cross-run; §4.3 |
| **R3-C4** under `-yy` every descriptor call "names a path", so `close`, `read`, `mmap` read literally as writes; saving 0 | Medium | **y**: R2-X6's sentence | FIXED by ENUMERATION: the table classifies by syscall NAME; the read-only path calls, descriptor calls and process calls are listed by name, and the write class too | §2 "How each call counts"; §8.4 |
| **R3-C5** `subprocess.DEVNULL` opens `/dev/null` `O_RDWR`, so most spawner pairs refuse each other | Medium | **partly**: whole-trace scope and `O_RDWR` = write are round 1's; round 2 made the scope explicit | FIXED by a NAMED EXEMPTION from the cross-run comparison: `/dev/null`, `/dev/zero`, `/dev/full`, `/dev/random`, `/dev/urandom`, `/dev/tty`, `/dev/pts/*`, `/proc/**`, `/sys/**`. `/dev/shm` is NOT exempt | §2 cross-run; §8.4 |
| **R3-C6** a seed-dependent miss that does not reproduce under the replay seeds is INCONCLUSIVE, so Q4's gate cannot fail on it | Medium | **y**: R2-X7's disposition | FIXED: a difference that reproduces under ANY replay seed latches as a MISS; one that never reproduces is an `unreproduced difference`, INCONCLUSIVE, kept out of the 20 and LISTED in the ledger. The remaining bound (a miss only another hash order or shard-order leftovers produce never latches) is stated in §2 and §4.5 | §2 *A MISS*; §4.5; §8.6 |
| **R3-C7** staging provenance and the link-listing refusal map nothing today (0 staged tracked links) and leave the map's key open | Low | **n** (r1; r2 added the listing refusal on top) | REPLACED by ONE REFUSAL, keyed by prefix: a read, probe or listing at or under a staged path that is a symlink in R's tree is INCOMPLETE (`through a repo link`). Cost today 0 (MEASURED) | §2 normalisation; record; §3 row 1; §8.4 |
| **R3-C8** no suite reaches the real checkout; the working-tree mapping and `git_membership` serve none | Low | **n** | REPLACED by REFUSAL: any path at or under `$GITHUB_WORKSPACE`, `.git` included, is INCOMPLETE (`real checkout`). Rule 3(d) and `git_membership` removed. The fixture-`.git` drop is kept. Cost today 0 (MEASURED) | §2 `.git`; record; Use 3; §5; §8.3; §8.4 |
| **R3-C9** "a pre-existing link cannot point into the copy" is false for a link to an ANCESTOR of the copy | Low | **n** (r1) | REPLACED the link table by REFUSAL: a path through a link created during the trace is INCOMPLETE; a path lexically outside the copy whose parse-time `realpath` lands at or under the copy is INCOMPLETE | §2 normalisation; §3 row 1; §8.4 |
| **R3-C10** a dependency change over R..BASE is not seen | Low | **n** | FIXED: the dependency manifests' blob ids (`package.json`, `package-lock.json`) join the validity key; `sweep-select` compares them with BASE's | §2 Store and Resolve; §3 validity row; §8.3 |

**Kept, with the reviewer's reasons.** The shared-cwd (`CLONE_FS`) model stays: a per-task copy-on-fork cwd is
needed for ANY relative path in a child, and a refusal is about as long. `Δ = R..BASE ∪ BASE..HEAD` stays: the
refusal "R ≠ BASE → today's rule" is simpler, but it gives up every lag-1+ run (31 of 113 PR runs, INFERRED in §5).

## The twelve buildability guesses, answered in the spec

| # | Guess | Answer (spec text) |
|---|---|---|
| 1 | which descriptor calls are read-only | enumerated by name (R3-C4) |
| 2 | `probed`'s record definition vs the recorder bullet | the bullet IS the definition; the record cites it |
| 3 | "under the staged roots": roots included? | "AT OR UNDER", the roots included |
| 4 | the provenance map's key | the map is gone; the repo-link refusal is by PREFIX (R3-C7) |
| 5 | detecting a pre-existing link on a failed or path-only call | parse-time `realpath` of the longest existing prefix (R3-C9) |
| 6 | `T`, `U` and other statuses | any status other than `A`/`M`/`D` is unparseable: FULL |
| 7 | the mount family | `mount`, `umount2`, `open_tree`, `move_mount`, `fsopen`, `fsmount`, `fspick`, `mount_setattr`: INCOMPLETE on sight |
| 8 | ` (deleted)` labels, escaping, label timing | a deleted label under the copy and a `rename*` in the copy are INCOMPLETE; C escapes decoded, an undecodable path INCOMPLETE |
| 9 | interleaved `-f -o` lines | two passes; a child starts with the parent's cwd at the clone's entry; a `chdir` in that window is a `cwd race`, an uncreated pid `unknown pid`, both INCOMPLETE |
| 10 | which strace version is "pinned" and how `sweep-select` learns it | `STRACE_VERSION`, a constant in the recorder module; a differing runner records every target INCOMPLETE; `sweep-select` imports it |
| 11 | §8.3's stale-set case tests a removed rule | replaced: a modified read or probed path over R..BASE PICKS by 3(a) |
| 12 | where the comparator's re-run runs | inside `shadow-compare`, on fresh staged trees of each side, via a new `--only <target> --mutant <id> --seeds <s>`, in isolation |

## Thrashing?

**No.** The arming condition (`docs/review-method.md` → *The arming condition — full account*) fires on two
CONSECUTIVE rounds whose findings came from the previous round's fix, in one component. Round 2's seven were all
fix-induced. Round 3's High (R3-C1) is NOT: rule 3(a) has read the same way since before round 1, and R3-C1 is a
sibling of R2-X1's fix (listings), not a consequence of it. Two findings ARE caused by the r2 fold, R3-C4 and
R3-C6 (R3-C5 partly). All are MEDIUM, and none loses a read: R3-C4 fails closed to a zero saving, and R3-C6
misjudges a comparison's count, not a selection. Round 2's simplifications held: the reviewer found no
construction against its widened refusals (`..`, listings through links, listed-ancestor cross-run, the
unfiltered table, write-by-default) that lets a lost read through as `complete`. **Not a prose floor either:**
R3-C1 is a constructed counterexample on the exact shape of `check-goal-status.py` and `check-anchors.py`.

## NEEDS THE OWNER

None. Every fix is a mechanism inside §7: Q1 B is kept and its probes widened (R3-C1), Q3's today's-rule fallback
is what every new refusal uses, Q4's 20 complete PRs are unchanged (R3-C6 tightens what counts as clean), Q5's
bound is restated more honestly (R3-C3, the new bound 5), and PR sweeps stay unseeded (the 2026-11-06 call in
`ci.yml` is untouched).

## Verdict

**Claude: NOT CONVERGED. STOPPED AT THE CAP.** Ten findings and twelve guesses, all folded in the spec.

**Next: ONE scoped verification round, round 4, Codex**, over THIS fold only (`git diff <r3 fold>^ <r3 fold> --
<spec>`), with `REVIEW GAP: claude — alternation`. Per §0 Q4c its non-BLOCKER findings are FILED to the
backlog, not folded; only a BLOCKER is folded. Its brief should ask it to refute the new refusals (seed-dependent
sets, the repo-link prefix, the real checkout, the runtime and pre-existing link rules, deleted labels and
renames in the copy, unknown pid and cwd race), the read-only name list, the device exemption, the any-ancestor
3(a), the lockfile key, and the latch rule, and to REPORT only, never touching GitHub.
