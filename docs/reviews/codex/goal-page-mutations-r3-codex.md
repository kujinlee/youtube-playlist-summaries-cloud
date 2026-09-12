# Codex adversarial review — branch `goal-page-mutations`, round 3

**Subject:** `git diff e3e44637..HEAD` — the round-2 fixes (two-input tracking assertions, the
`parse_adr` fixture and entry 25, the deleted provenance enumeration, and the corrected
`check-fixture-variation` / `--follow` / "ONE sibling generator" claims).

**Gate provenance:** `scripts/codex-review.py`, model `gpt-5.5`, `gate_ran: true` — testimony at
`docs/reviews/verdicts/goal-page-mutations-r3-codex.verdict.json`.

**Verdict: NOT-CONVERGED — but with NO Blocking and NO High.** All three findings are documentation
staleness in `docs/dashboard-entries.md` and one pre-existing unsupported count; all three were
fixed in the commit that files this review. The severity curve across the branch is
Blocking+High → Blocking+High → none, and the CHARACTER changed with it: rounds 1 and 2 found rules
nothing could reach and cases that could not fail; round 3 found only prose that had not been
updated to match the code.


"front matter is NOT counted as an amendment" — `scripts/mutations/gen-goals-page.json` now has 25 entries.

**Findings**

Blocking: none.

High: none.

Medium — [docs/dashboard-entries.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/dashboard-entries.md:7750)

Where: `docs/dashboard-entries.md:7750`.

What: the dashboard still says, “Round 1 — both halves NOT-CONVERGED, one High each, same structural cause.” That is the exact false account round 2 says was caused by the overwritten review file. The committed Claude r1 High is `parse_adr`, not the seam.

Concrete failing scenario: a reader uses the dashboard as the durable record and concludes both r1 Highs supported the seam work. The very same entry later says `parse_adr` was still open, so the record contradicts itself.

Evidence run/read: `docs/reviews/claude/goal-page-mutations-r1-claude.md:70` is the `parse_adr` High; `rg "24 candidate|11 SURVIV"` finds no such measurement in the committed Claude r1 review. `scripts/check-plan-code.py:571-587` has the corrected account, but the dashboard did not receive the same correction.

Medium — [docs/dashboard-entries.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/dashboard-entries.md:7717)

Where: `docs/dashboard-entries.md:7717-7719` and `:7774-7775`.

What: stale mutation totals survived the round-2 fix. The prose says “Five hundred and thirty-eight breakages now all kill,” and the tech block says “CI at 548 attributed,” while this round moved the ratchet to 549 and added entry 25.

Concrete failing scenario: the dashboard reads as if the new `parse_adr` mutation is not included in the attributed total, even though the manifest and ratchet say it is.

Evidence run: `EXPECTED_MUTATIONS["scripts/gen-goals-page.py"] == 25`, `sum(EXPECTED_MUTATIONS.values()) == 549`, manifest length is 25, and a temp-copy full pass produced `caught=25 attributed=25 measured=25`.

Low — [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:1225)

Where: `scripts/check-plan-code.py:1225-1227` and `:2966-2971`.

What: the already-filed Low about `brief-compose.py paid 8` remains. The committed observable count is 16, not 8.

Concrete failing scenario: the next reader treats “brief-compose.py (8)” / “paid 8” as an artifact-backed entry count. It is not backed by the committed manifest or ratchet.

Evidence run: `len(scripts/mutations/brief-compose.json) == 16`; `EXPECTED_MUTATIONS["scripts/brief-compose.py"] == 16`; `git log -S'"scripts/brief-compose.py": 8' -- scripts/check-plan-code.py` returns no commits.

**Round 2 Findings — Closed Or Not**

Codex Blocking, argv cases compared one call to one literal: CLOSED. Temp-copy probes hardcoding first value, second value, basename-only path, first sha, second sha, and sha prefix all failed via the intended case.

Claude High, `parse_adr` front-matter split still open: CLOSED. The fixture now has `⟳ SUPERSEDED` inside front matter; deleting the split fails via `front matter is NOT counted as an amendment`; entry 25 attributes.

Provenance enumeration deleted instead of corrected: PARTIAL. The enumeration is gone from source, but dashboard prose still has the stale “same structural cause” account and stale 538/548 totals.

`check-fixture-variation` credit corrected: CLOSED in the detailed prose; the remaining “came from check-fixture-variation” wording is tolerable with the surrounding caveat.

`--follow` impossibility replaced with pure-functions constraint: CLOSED.

“ONE sibling generator” narrowed and `gen-m4-manifest.py` named: CLOSED in `check-plan-code.py`.

Five nonexistent r1 finding IDs restated: CLOSED.

Round-2 Low, `brief-compose.py paid 8`: OPEN.

Round-2 Low, `~540 lines`: OPEN but not escalated here; it is old and not made worse by the round-2 fix.

**Checked And Found Sound**

`python3 scripts/gen-goals-page.py --self-test` passed `75/75`.

`python3 scripts/check-plan-code.py --self-test` passed `128/128`.

`python3 scripts/check-fixture-variation.py` passed.

`python3 scripts/check-selftest-counts.py` passed across 36 declaring scripts.

`python3 scripts/check-ratchet-contract.py` passed.

All 25 manifest `before` anchors are unique and match once. Entries 23/24 anchor on the specific argv fragments and do not collide with the broader git-log/git-show anchors. Full temp-copy mutation pass: control green, 25/25 killed, 25/25 attributed, no survivors.

NOT-CONVERGED
