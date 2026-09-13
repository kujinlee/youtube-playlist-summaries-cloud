# Adversarial review — `schema-index-bound-stale`, round 1 (Codex)

**REVIEW GAP:** claude — not invoked. This session's harness instruction forbids dispatching review
subagents unless the user asks, and the user's approval covered the triage and fix shape, not a
review fleet. The change is a 44-line assertion inversion whose subject is itself a test harness,
and it is verified by the full fifteen-gate schema suite plus an independent Codex run that
re-executed the harness on the clone path. Re-attempt the Claude half before merge if wanted.

**Dispatched with** `scripts/codex-review.py --prompt-file … --out …/r1.md`; model `gpt-5.5`;
`gate_ran=true`, 3187 chars. ⚠ The verdict JSON beside this file was renamed from its run stem
`r1.verdict.json` to match this document's basename — its `review` field was updated in the same
edit and nothing else in it was touched. The `--out` path was a generic `r1.md`, which is the
allocator-less evidence-path hazard this repo has paid for twice; naming it after the subject at
dispatch time is the fix next time.

**Verdict: no Blocking / High / Medium. One Low, ACCEPTED and corrected** — see below.

---

<!-- codex-review: model=gpt-5.5 -->

**Findings**

Low — `docs/dashboard-entries.md:8013` overstates the harness count. The diff arithmetic is directionally right: the old INDEX bound was one runtime report removed at `scripts/mutate-live-schema-check.sh:347-349` on `master`, and the new `probe_kind "INDEX"` adds two runtime reports through `probe_kind` at `scripts/mutate-live-schema-check.sh:303` and `scripts/mutate-live-schema-check.sh:308`. So the branch should net `+1` assertion line. But I measured the actual branch harness as `pass=56 fail=0 total=56`, not `73/0`. A literal report-call/runtime expansion also supports `55 -> 56`, not `72 -> 73`: `probe_kind` is called 3 times on `master` and 4 times now at `scripts/mutate-live-schema-check.sh:315-348`. No functional failure, but the recorded evidence line is false as written.

**No Blocking / High / Medium Findings**

The diagnosis looks right. The live-DB measurement is not load-bearing by itself, but the branch now proves the same thing on the clone path: mutation 3 runs on `${PREFIX}_raw` from `fresh` at `scripts/mutate-live-schema-check.sh:253`, controls the unmutated clone at `:255-256`, creates the index at `:347-349`, matches the drift output at `:301-303`, and requires undo-green at `:304-308`. I ran `./scripts/mutate-live-schema-check.sh`; the clone INDEX probe passed and the harness finished green.

Dropping `landed` is sound for the failure modes named. Because the INDEX assertion is expected-red, a failed/suppressed `create index`, an index-name collision, or `workspace_videos` no longer being owned leaves no drift sentence and marks the probe failed at `scripts/mutate-live-schema-check.sh:301-303`. A leftover/other drift object cannot make the whole suite falsely green: the block first asserts no drift sentence on the clean clone at `:311-313`, and each prior POLICY/CONSTRAINT/TRIGGER probe requires undo-green at `:304-308` before the INDEX probe runs.

The removed later cleanup `drop index if exists m4_mut_idx;` also looks safe. If the INDEX undo does not happen, the immediate undo-green assertion at `scripts/mutate-live-schema-check.sh:307-308` goes red before the later removed-column assertion at `:399-404`. A leftover index could make that later expected-fail line pass for an extra reason, but only after the suite is already red, so it is not a false-green path.

Docs are mostly clean. `docs/backlog.md:93` now states the closed index hole as history plus the new probe. I found the old-world statement still present in the dated review record at `docs/reviews/backlog-65-live-schema-drift-self-review.md:69-74`, as claimed. Other hits I checked are historical/comments or mutation names, not current present-tense assertions.

**Verification Run**

Ran:
`./scripts/mutate-live-schema-check.sh` — PASS, every mutation caught.  
`./scripts/mutate-live-schema-check.sh | awk ...` — `pass=56 fail=0 total=56`.  
`M4_PHASE=post bash scripts/check-schema-gates.sh` — PASS, all 15 schema gates green.  
`python3 scripts/check-live-schema.py --self-test` — PASS, `119/119`.  
`python3 scripts/check-catalog-coverage.py --self-test` — PASS, `18/18`.  
`python3 scripts/check-backlog-closure.py docs/backlog.md` — PASS.

---

## Coordinator response to the Low — ACCEPTED, and re-measured rather than taken on trust

Codex is right and the defect is mine. The line in `docs/dashboard-entries.md` labelled
`harness   71 ✓ / 1 ✗  ->  73 ✓ / 0 ✗` reports **suite-wide** counts under a **harness** label. I had
counted `✓`/`✗` in the whole `check-schema-gates.sh` log, which includes ticks emitted by the other
fourteen gates, and inherited the `71/1` figure from a session handoff that counted the same way.

Both populations, each measured by running the thing rather than reasoning about the diff:

| population | master (`a1a5e1bf`) | branch (`1b4ee329`) |
|---|---|---|
| `mutate-live-schema-check.sh` alone | **54 ✓ / 1 ✗** | **56 ✓ / 0 ✗** |
| `M4_PHASE=post check-schema-gates.sh` | 71 ✓ / 1 ✗ | 73 ✓ / 0 ✗ |

Both move by `+1` net, which is the arithmetic the diff predicts: one `report` call removed, one
`probe_kind` (two `report` calls) added. Codex's independently measured `56` matches.

The store is append-only, so the correction is a **new entry**, not a rewrite of the old one —
the ids are positional and editing history silently rebinds them.

⭐ The general shape, which this repo has a memory file for: *a measurement is only as good as its
corpus*. The number was never wrong; the **set it was taken over** was, and the label is where that
became a false claim.
