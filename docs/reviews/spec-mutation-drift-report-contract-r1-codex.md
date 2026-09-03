# Spec review round 1 — Codex half — mutation drift report contract

**Subject:** `docs/superpowers/specs/2026-09-03-mutation-drift-report-contract-design.md` v1
(candidate 2′, architecture review #5 finding B). **Date:** 2026-09-03.
**Model:** `gpt-5.5` — `gpt-5.6-sol`, `-terra` and `-luna` each returned HTTP 400 and the wrapper
fell through, exactly as `docs/plugins.md` documents. Ran with `-s danger-full-access`, so it
**executed** F1 and F3 rather than reading them.

> ⚠ **WRAPPER WARNING WAS A FALSE POSITIVE — checked, not assumed.** `codex-review.py` reported
> *"THE AGENT WROTE BEHIND THE WRAPPER"* naming its own log and
> `docs/reviews/spec-mutation-drift-report-contract-r1-claude.md`. Neither was Codex. The wrapper
> snapshots files before/after the run, and **the coordinator was writing the Claude half
> concurrently**, so its own writes were attributed to the agent. Verified: `git status` showed only
> the two expected untracked files, and the Claude half still contains its own `B1` heading and
> verdict line — nothing was overwritten.
>
> **This is a real, if benign, defect in the detector: running the two halves in parallel makes it
> cry wolf**, and a detector that cries wolf is how the overwrite it exists to catch gets ignored.
> Worth a backlog row — the user's call to file.

---

<!-- codex-review: model=gpt-5.5 -->

**Findings**

Blocking: Option (a)’s “flip after `copytree`” is too early; it marks a run as measured when the control fails before any mutation is applied.  
Evidence: [spec line 83](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-09-03-mutation-drift-report-contract-design.md:83) says flip after `copytree`; [code line 630](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:630) copies, [line 637](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:637) starts control runs, [line 646](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:646) returns before [line 647](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:647) calls `run_mutations`.  
Observation that would make it fail: a control-red fixture would need to produce a final line that clearly says mutation measurement did not run, with no mutation/survivor tally. A sentinel flipped right after `copytree` cannot do that.

Medium: Section 7’s “sum 168” is not stable under this spec’s own required mutation-count change.  
Evidence: [spec line 123](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-09-03-mutation-drift-report-contract-design.md:123) requires `check-plan-code.py` to rise `21 -> 22`; [spec line 124](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-09-03-mutation-drift-report-contract-design.md:124) requires total `162 -> 163`; [spec line 130](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-09-03-mutation-drift-report-contract-design.md:130) still says the other plan’s corrected total is `168`. Current code confirms `check-plan-code.py: 21` at [line 473](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:473) and sum `162` at [line 2021](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:2021).  
Observation that would make it fail: if this spec explicitly said “168 only before this spec lands; 169 if this spec lands first,” or avoided giving the sibling plan’s global total.

Medium: F2/F4 are not executable exactly as written; F4 is especially vulnerable to a vacuous implementation.  
Evidence: F2 is prose-only at [spec line 117](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-09-03-mutation-drift-report-contract-design.md:117); F4 says “a manifest entry that deletes the `ran` flip” but names no anchor, no manifest target, and no expected case at [line 122](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-09-03-mutation-drift-report-contract-design.md:122). The existing mutation contract requires named manifest entries with concrete edit anchors and expectations; see `run_mutations` handling anchors and `expect` at [line 687](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:687) and [line 756](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:756).  
Observation that would make it fail: F2/F4 would need exact commands or exact manifest entry text, including the named case that reddens when the sentinel flip is removed.

Low: The call-site count for option (b) is false.  
Evidence: [spec line 84](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-09-03-mutation-drift-report-contract-design.md:84) says 7 `_self_test` call sites; [line 87](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-09-03-mutation-drift-report-contract-design.md:87) says 9 call sites total. Actual `mutate_delivered` calls are 7 in `_self_test` plus 1 in `main`: [line 1866](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:1866), [line 1875](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:1875), [line 1883](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:1883), [line 1897](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:1897), [line 1909](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:1909), [line 1930](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:1930), [line 1943](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:1943), [line 2069](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:2069).  
Observation that would make it fail: another actual call site in the file.

**Checked**

R1 early returns before `copytree`: `load_manifests` problems return at [line 586](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:586), including no manifest dir, no manifests, missing target, invalid JSON, empty manifest, duplicate name/anchors, or file mismatch; drift returns at [line 626](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:626), including count mismatch, undeclared target, unreadable target, target home escape, or replacement home escape.

Severity downgrade: confirmed. I found no `mutate_delivered` early-return path that yields exit `0` or a line beginning `OK`; the early returns are `False`, and `main` prints `FAILED` then returns `1` at [line 2072](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:2072) and [line 2075](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:2075).

Option (c): refutation confirmed. `ok=False` is also the survivor/failed-expect path after actual mutation execution; see [line 773](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:773) and [line 779](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:779).

F1: ran in a temp copy; reproduced `FAILED — delivered scripts mutated: 0 file(s), 0 mutation(s), 0 survivor(s)` with exit `1`. F3: ran clean `--mutate .`; final line was `OK — delivered scripts mutated: 7 file(s), 162 mutation(s), 0 survivor(s)` with exit `0`.

Verdict: NOT CONVERGED.
