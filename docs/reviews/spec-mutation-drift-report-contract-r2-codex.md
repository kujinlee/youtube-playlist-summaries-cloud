# Spec review round 2 — Codex half — mutation drift report contract

**Subject:** spec **v2**, SCOPED to v2's own changes. **Date:** 2026-09-03. **Model:** `gpt-5.5`
(`-sol`/`-terra`/`-luna` → HTTP 400, wrapper fell through), `-s danger-full-access`.

> ⚠ **THE WRAPPER'S OVERWRITE WARNING FIRED AGAIN, AND THE MITIGATION FAILED — this is now a
> reproducible defect, not a one-off.** Round 1's warning named the Claude review inside the repo, so
> for round 2 the Claude half was written to the **scratchpad instead**. The wrapper flagged it there
> too (`claude-r2.md — CREATED by the agent during the run`), along with its own log.
>
> **Conclusion: `codex-review.py` cannot distinguish the coordinator's writes from the agent's, so
> running the two halves CONCURRENTLY always cries wolf — and `docs/plugins.md` REQUIRES both
> halves.** The warning therefore fires on the normal path, which is precisely how the real overwrite
> it exists to catch would get waved through. Verified benign both times: `git status` showed only
> the expected untracked files and both Claude halves retained their own text.
>
> **Worth a backlog row. Not filed — the user's step.**

---

<!-- codex-review: model=gpt-5.5 -->

Blocking — `run_mutations` returning is not enough to make the final tally meaningful.

Evidence: `docs/superpowers/specs/2026-09-03-mutation-drift-report-contract-design.md:90-94` defines the suppress-tally predicate as “when `run_mutations` has not returned”; `scripts/check-plan-code.py:647-663` then has a post-mutation control failure path that appends “Treat this run as NOT CHECKED” after `run_mutations` already returned and `ev["mutations"]` was populated. The existing self-test fixture at `scripts/check-plan-code.py:1912-1933` proves this path is intentional.

Observation that would make it FAIL: a target that goes red only on the after-control returns `FAILED — delivered scripts mutated: 1 file(s), 1 mutation(s), 0 survivor(s)` while also reporting “Treat this run as NOT CHECKED.” That is the same misleading “0 survivor(s)” shape v2 is trying to remove.

Medium — F2 is still not three concrete shell recipes.

Evidence: `docs/superpowers/specs/2026-09-03-mutation-drift-report-contract-design.md:163-169` gives one shell block with comments for F2a/F2b/F2c, but no commands that actually clone a manifest entry, add a distinct entry, or append `raise SystemExit(1)`.

Observation that would make it FAIL: copying and running the block as written exercises the unchanged temp tree, not the claimed `:586`, `:626`, or `:646` returns. I verified the described edits can reach those returns, but the spec does not provide executable recipes.

Medium — F4 says the manifest entry is “written out,” but it still contains placeholders.

Evidence: `docs/superpowers/specs/2026-09-03-mutation-drift-report-contract-design.md:178-188` introduces “The entry appended … is:” and then uses `"<the ran-flip statement as delivered at :648>"` and `"<the named case asserting a control-failure run prints no tally>"`.

Observation that would make it FAIL: an implementer can satisfy the prose without a real anchor or real `expect` case name; copied literally, the entry is not a meaningful mutation and repeats the vacuity v2 claims to fix.

Low — v2 fixed the sibling order arithmetic in §7 but still states this spec’s own global total as fixed.

Evidence: `docs/superpowers/specs/2026-09-03-mutation-drift-report-contract-design.md:195-196` says the sum literal rises `162 → 163`; `:205-217` correctly says the sibling plan may land first and make the sibling total `168` before this spec lands.

Observation that would make it FAIL: if the sibling plan lands first, this spec’s implementation must update the global sum `168 → 169`, not `162 → 163`.

NOT CONVERGED
