---
name: slice-history
description: "FIRES-WHEN: I need the PR number, SHA, round count or verdict for a slice that ALREADY SHIPPED — which PR carried a change, what its SHA was, how many review rounds it took, or whether it merged CONVERGED. History and pointers only, NEVER current state: read [[launch-roadmap-state]] for what is true now"
metadata:
  type: project
---

> Split out of [[MEMORY.md]] on 2026-10-19 because the index had grown to **26,930 characters
> against the harness's 24,985-CHARACTER limit** and was being silently truncated mid-session —
> **8 index rows** were dropped before any of it was read, and *which* rows survived was not a
> choice anyone made. ⟳ This first said "27,805 bytes" and "roughly 30 rows"; the unit was wrong and
> the count was a mean-row-size estimate dressed as a measurement.
> Rows below are **VERBATIM**; they carry PR numbers and SHAs that cannot be re-derived.
>
> ⛔ **This is history, not current state.** Following the pattern of [[m4-superseded-trail]], these
> rows are now reached by the matcher on the trigger above rather than loaded on every turn — so they
> arrive when someone asks which PR shipped what, and cost nothing otherwise. Relative links resolve
> because this file sits in the same directory as the entries it points at.

## Slice history (all MERGED unless noted — open the file for PR/SHA)

- [⭐⭐ chrome-bar + Phase 6 — #378 MERGED](chrome-bar-reachable-378-merged.md) — `11c1d5db`, NOT CONVERGED, 1 Blocking FILED. ⭐⭐ The suite is **monotone**: 17 added bytes kill the feature, all gates green (manifests 2.0% additive). The 8-round gate cleared on a **prose-only** round — `is_prose()` · #300/#304/#305/#306 OPEN
- [⭐⭐ recall fold — PR #360 MERGED](recall-fold-360-merged.md) — `5128b99b`, **merged NOT CONVERGED with 3 Highs open**. 9 rounds; each fix CREATED the next instance. ⭐⭐ The fix was already in the repo at `check-ci-watched.py:860` and reached **zero** siblings → ADR-0014
- [⭐⭐ backlog #154 — PR #331 READY](backlog-154-dash-scalar-ready-331.md) — `0791ca6f`, **not merged**. EIGHT rounds, each a NEW GRANULARITY (line→node→document→key-depth). Fix changed KIND: **refuse, don't widen**. ⭐ My class-fix made 6 mutations UNKILLABLE, suite green — only the sweep saw it
- [⭐ arch review #153 — PR #329 READY](arch-review-153-workflow-readers.md) — `ccff9878`, **not merged**. Verdict: extract `_structural()`, NOT parse. Found a **LIVE false green** → #154 first. 4 rounds; #155 SIZE NOT KNOWN → size by ATTEMPTING
- [M4 superseded trail](m4-superseded-trail.md) — history only, split out of the RESUME file when it outgrew the read limit. Fork (a), `0028` cannot be a migration, Phase 6 ran TWICE
- [⭐⭐ pin-python — #317](pin-python-317-merged.md) — `e7ed8c1a`. **TEN defects, ONE function, 7 rounds**, all one root cause. ⭐ I tested the CONTAINER's shape not its CONTENTS (2×); a fix landed at the WRONG LAYER (2×); my pre-committed falsifier FIRED
- [⭐⭐ closing-table r7–r11 — #327 + #328](closing-table-r7-r8-merged-327.md) — the independent read #325 shipped without. 16 findings/5 rounds. Marker fired on **96.7%→49%**, false-sentence firings **372→0**. ⛔ `check-review-recorded` keys on CODEX VERDICTS, not commit order — 2 of 5 reds
- [⭐ merge-ready + budget slack — #324](merge-ready-slice-merged-324.md) — `af4d9033`. `check-merge-ready.py` runs the **PR-only** gates a local run can't reach; relay its verdict VERBATIM. ⭐ **2026-09-26: I skipped it and put TWO PRs red** — run it, not a gate subset; `NO-ENTRY:` ≠ `NO-REVIEW:`; and it reads the COMMITTED diff, so an uncommitted entry is a vacuous rc=0. 3 rounds, 4 silent misses, ONE parser. `--tick` REFUSES while `paused:`
- [⭐ Wake-on-visit — #322](wake-on-visit-merged-322.md) — `e693f36a`. Worker sleeps/wakes, own Fly app NO public IP. INERT except the drain-key fix
- [Lease-sweep cadence — #318](lease-sweep-merged-318.md) — ⭐ `35cf44c6`. Idle worker was **100%** of prod DB traffic. Found 🔴 **#139**; `fly.toml` drift reverts it
- [#137 schema-gates REQUIRED — #315+#316](schema-gates-required-137-merged.md) — ⭐ `[verify, schema-gates]` live. The deleted filter had a SECOND CONSUMER (#138)
- [peer-sites — #313](peer-sites-merged-pr-313.md) — `14063fe5`. Ships with NO caller by design (#134). ⛔ `NO-REVIEW:` must start the line
- [#122 manifest seeded — #311](seed-manifest-122-merged.md) — 42 entries, 7 live defects. ⛔ Codex timed out ALL 3 rounds; #129/#130 open
- [Split #295: /src/ half — #310](split-295-src-root-merged.md) — ⛔ #295 STILL OPEN, do NOT merge as-is; restart half parked
- [Guard-ratchet scope — #298](guard-coverage-scope-merged.md) — ⭐ saw 41 guards, ignored 14 on tables it BUILDS; now has a falsifier
- [Schema gates in CI — #297](schema-gates-in-ci-merged.md) — ⭐ 15 gates, 93s, zero added wall clock. ⛔ nightly cron UNARMED
- [#91 coverage-verdict union — #269](coverage-verdict-union-91-merged.md) — ⭐ 374 mutations / 0 survivors
- [Selection-card guard LIVE](selection-card-guard-built.md) — ⭐ a hook REFUSES a malformed card. Its 2 rounds found **4 Blockings**
- [#110 parser completeness](backlog-110-parser-completeness-merged.md) — ⭐⭐ BOTH Blockings were the row's own defect, reintroduced by its fix
- [Retire plan mode — #270+#271](retire-plan-mode-merged.md) — ⭐ 3,607 → 2,013 lines. The only sanctioned ratchet FALL
- [Ask-choices — #186](dashboard-ask-choices-merged.md) — ⭐⭐ **CONSENSUS IS NOT VERIFICATION**: all three agreed, `git diff` refuted
- [Page chrome seam — #185](page-chrome-seam-merged.md) — ⭐ theme+provenance on all five page producers
- [HOME-redirect — #181](mutation-harness-home-redirect-state.md) — ⭐ `$HOME` governs `Path.home()` and a bare `~`, **NOTHING else**
- [Inline renderer seam](inline-renderer-seam-merged.md) — ⭐ ONE renderer, four pages; the sum HELD at 73
- [Fixing a PREMISE ≠ covering the BRANCH](fixing-a-premise-is-not-covering-the-branch.md) — ⭐⭐ **12 unfalsifiable cases across 8 guards**
- [Mutation-manifest retarget](mutation-manifest-retarget-merged.md) — ⭐ `--mutate .` mutates DELIVERED scripts
- [Link-contrast slice](link-contrast-slice-merged.md) — ⭐ shipped UNREVIEWED; 2 rounds then found 6 defects
- [Integration suite skips migrations](integration-suite-does-not-apply-migrations.md) — ✅ FIXED (#46). A GREEN gate on the wrong schema is worse than none
- **Older slices, all MERGED unless marked:**
  [Stage 3 cloud-sync](stage3-cloud-sync-branch-state.md) (honest-blob-read open) ·
  [Blob addressing](blob-addressing-spec-state.md) ⏸ PARKED, round 10 mandatory if unparked ·
  [Worker-vs-sync fencing](worker-vs-sync-fencing-gap.md) · [Serial coherence](serial-coherence-slice-state.md) ·
  [Reservation release](reservation-release-slice-state.md) · [Section timestamps](summary-section-timestamp-guarantee-state.md) ·
  [Dig frontend](cloud-dig-deeper-frontend-state.md) · [Dig serving](cloud-dig-serving-branch-state.md) ·
  [Sidebar UX](playlist-sidebar-ux-branch-state.md) · [Summary PDF](cloud-summary-pdf-slice-state.md) ·
  [Frontend sub-project](frontend-subproject-design-state.md) · [Stage 2 autonomy](stage-2-batch-autonomy-plan.md) ·
  [1G](stage-1g-design-state.md) · [1F-c](stage-1f-c-design-state.md) · [1F-b](stage-1f-b-design-state.md) ·
  [1F-a](stage-1f-a-design-state.md) · [1D](stage-1d-merged-followups.md)

## Moved out of the index 2026-10-28 (owner's decision L2: trim it mechanically) — VERBATIM

### The index's header note

> One line per memory. ⛔ **CORRECTED 2026-09-28: NOTHING DECIDES RELEVANCE.** This line used to say *"the hook decides relevance"* and that was never true — measured: no file in the `remember` plugin references `MEMORY.md` at all, and all **133** rows arrive every session, unfiltered. **So every row below is always in context and none of them is ever matched to the moment** — which is why recall fails here, and why the hook's title has to do the matching by itself. Write each hook as the SITUATION you would be in, not the subject it is about (backlog #191).

### The index's former Slice-history section

> ⛔ **NEW SLICE ROWS GO IN THAT FILE, NOT IN THIS INDEX.** This index is injected WHOLE on
> every turn and the harness truncates it in silence once it passes 24,985 CHARACTERS — measured
> 2026-10-19, it stood at 26,930 and **8 rows** had stopped arriving, with every other memory
> signal green. ⟳ Both the unit and the count are corrections: this said "bytes" and "~30 rows",
> and the real figures were established by reading the cut point out of a consuming agent's own
> injected context. `scripts/check-memory-index-budget.py` now fails on that, so this is enforced
> rather than remembered; a convention only catches what someone happens to read.

- [⭐ Slice history — every shipped slice, with PR + SHA](slice-history.md) — 28 rows, MOVED OUT of this index 2026-10-19. ⛔ Reached by TRIGGER now, not always-loaded — verified by firing: ask for a PR number or SHA and it returns. The index was 26,930 of a 24,985-CHARACTER budget; the 28 rows are **4,912** chars without line endings, 4,940 with one newline each (the whole section 5,990). ⚠ Two earlier versions were wrong: "6,232 of 27,805 bytes" (wrong unit, and it charged the rows with the whole SECTION's cost), then "4,985" (r2 CODEX #6 — that joined 29 `- ` lines, counting the "Older slices" bullet as a 29th row)

### Rows about finished slices

- [⭐ RESUME: anchors + stable ids](anchor-name-and-stable-id-handoff.md) — M4 MERGED (#155); `0027` LIVE ON PROD. The stable-id roadmap **EXISTS** — I once re-derived it wrongly
- [Serve-path bounding MERGED](serve-path-bounding-merged.md) — a single CONVERGED verdict was WRONG 4 of 5 times
- [gh two-remotes footgun](gh-two-remotes-footgun.md) — ✅ RESOLVED; keep `--body-file`

### Rows moved out of the index 2026-11-01

Moved to bring `MEMORY.md` under 90% of its budget; each link still resolves.

- [Detached dig retention](detached-dig-retention-decision.md) — retiring a rule dissolved a review High with zero code change
- [CANDIDATE stopping rule](stopping-rule-defect-class-shift.md) — ⏳ untested and partly falsified
- [check-main-drivable is slow PER main() CALL SITE](main-drivable-cost-is-per-call-site.md) — main([...]) inside a long _self_test: 50s → 209s, past the 120s shard timeout. One call in a small helper → 52s
- [⭐ Scoped mutation run in 4s](scoped-mutation-run-in-four-seconds.md) — ⛔ DECIDED: PARTIAL locally (only manifests whose file MOVED — co-scoping an unchanged 183 cost 4h), FULL in CI shards. 8 local shards TIME OUT → NOT MEASURED; `--shard` is round-robin and cannot isolate a file. Prune a COPY of HARNESS_TREE's SIX paths. ⭐ The harness is structurally browserless (`typescript` only → ERR_MODULE_NOT_FOUND)
- [Local manual-test env](local-manual-test-env.md) — `~/code/agentic-ai-docs/yps-sync-test/`; sync is ADDITIVE
- [Staging Supabase](staging-supabase-project.md) — ⚠ throwaway `neeufoxdbgbpkjukzzuc`; DELETE when B3/B4 done
- [Cost per video](cost-per-video-analysis.md) — real Flash ≈8¢/video vs the 150¢ reservation
