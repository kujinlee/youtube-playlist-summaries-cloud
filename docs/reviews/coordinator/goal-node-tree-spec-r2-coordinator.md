# Round 2 — `goal-node-tree-spec` — coordinator — ⟳ NOT CONVERGED (Codex); 3 fixed, 0 rejected, 3 more found and fixed

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

Subject: the round-1 fold (`efab5936`) of `docs/superpowers/specs/2026-11-23-goal-node-tree-design.md` and
`docs/adr/0016-names-live-in-one-node-tree.md`, reviewed by Codex in
`docs/reviews/codex/goal-node-tree-spec-r2-codex.md` (1 BLOCKER, 1 Major, 1 Minor).

```yaml
round: 2
fixes_nontrivial: true
subject: goal-node-tree-spec
halves:
  claude: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
  codex: ran
findings:
  - {id: XB1, severity: Blocking, aim: deliverable, fix_induced: false, component: guard, disposition: fixed}
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: true, component: migration-slices, disposition: fixed}
  - {id: Xm1, severity: Low, aim: deliverable, fix_induced: true, component: prose, disposition: fixed}
  - {id: N1, severity: Medium, aim: deliverable, fix_induced: true, component: guard, disposition: fixed}
  - {id: N2, severity: Medium, aim: deliverable, fix_induced: true, component: migration-slices, disposition: fixed}
  - {id: N3, severity: Medium, aim: deliverable, fix_induced: false, component: migration-slices, disposition: fixed}
```

Severity mapped BLOCKER → Blocking, Major → Medium, Minor → Low. N1–N3 are the coordinator's own, from the
same-class search the brief asked for. `fix_induced` was decided by `git log -S` on each finding's text: the G6
wording dates from the draft (`8a4d25b5`); the S4 routing, the "63 + 6" count, the ADR widening of G1 and the
S2 `dev-speed` creation all came in with the round-1 fold (`efab5936`). The owner's decisions D1–D8 and the ✍
questions Q11–Q13 were not touched; no owner quote was rewritten.

**Thrashing check (Phase 6 arming):** this is the first round with fix-induced findings (4 of 6, components
`migration-slices`, `guard`, `prose`); round 1 had none. Two CONSECUTIVE rounds are needed, so Phase 6 is not
armed. If round 3 carries a finding caused by this fold in `migration-slices` or `guard`, it is.

## Findings

| id | half | Verified? — evidence | Action |
|---|---|---|---|
| XB1 | codex | YES. G6's FAILS IF read "two nodes share a slug, or a slug appears in any `was:` list". Every `was:` entry appears in a `was:` list by definition, so the 5 renames of §4 (and S2's `was: dev-speed-first, harness-speed`) all fail it. §2.4's last bullet and ADR-0016 (*a slug is unique across current AND former slugs*) already stated the intended rule; only the G6 cell was wrong | FIXED: G6 now fails when a slug occurs more than once in the COMBINED list of current slugs and every `was:` entry, and says explicitly that a former slug listed once and held by no node passes. ADR-0016's FAILS IF line gains the same clarification. The walk is below |
| XM1 | codex | PARTLY. True that `.claude/hooks/regen-goals-page.sh` filters at `:35-42` and does not take `docs/goal-threads.md`. NOT true that S4's design would have missed the rebuild: `regen-pages.sh` is registered under PostToolUse `Edit\|Write` (`.claude/settings.json:174`) and runs `regen-pages.py --hook` → `pages_for`, so S4's `pages_for` change WOULD have rebuilt `/goals`. The real defect is narrower and still real: one page's edit triggers split over two dispatchers, no listed trigger inventory, and a `pages_for`-only test that cannot see a shell `case` list | FIXED, with Codex's route: S4 adds `docs/goal-threads.md` to `regen-goals-page.sh` and DROPS the `pages_for` → `goals` routing (both would double-build). New §5.1.1 lists every trigger of every page, measured, with what each slice changes, under the rule "each page has ONE edit dispatcher". The S2/S3/S4 FAILS IF now tests both dispatchers — each hook run in a temp copy with a recording `regen-pages.py` stub, `pages_for` per source, and a case that fails if a (source, page) pair is dispatched by neither or both |
| Xm1 | codex | YES, and the count was also mislabelled. Re-run with `check-anchors.py`'s `ANCHOR` regex: at the base `fa11456f`, 63 specs+plans, 5 ADRs, 3 frozen reviews; on this branch 64 and 6. §7 called the 63 "documents across `docs/`"; §2.5.1's "63 + 6" mixed a base count with a branch count | FIXED: §2.5.1, §7, 4.37, Q7 and ADR-0016 *Consequences* state disjoint counts with their base |
| N1 | coordinator | NEW (same class as XB1: a guard rule that cannot do what the migration needs). `parse_header` reads `HEAD_LINES = 10` (`scripts/check-anchors.py:61`); the 6 ADR headers sit at lines 12, 9, 11, 11, 13, 8 (0011–0016). G1 "adds `docs/adr`" with today's window would check 2 and pass 4 silently | FIXED: G1 reads an ADR up to its first `## ` heading (every header precedes it: measured per file), with a case asserting all 6 are read; ADR-0016's FAILS IF says the same |
| N2 | coordinator | NEW (found by the G6 walk). S2 said `dev-speed` is "created" with `was: … harness-speed` while the `harness-speed` heading (`docs/features.md:136`) still exists — current slug and `was:` entry at once, which the corrected G6 refuses | FIXED: S2 makes `dev-speed` by RENAMING the `harness-speed` heading and lifting it to the trunk, never as a new node beside it |
| N3 | coordinator | NEW (same class: a check the migration breaks). `check_cross` (`scripts/check-features.py:249-253`, `:271-273`, `:276-278`) has three anchor rules fed by `ANCHORS_MD` (`:284`, `:289`, `:297`); S2 deletes the file and the field but did not name these | FIXED: S2 removes the three rules and the read |

## G6 — every `was:` slug walked through the revised rule

Current slugs = the 45 nodes of §4 (listed from its rows: `product` … `harness-ships-elsewhere`). Former slugs =
every `was:` entry. Rule: no slug occurs twice in the combined list.

| `was:` slug | On node (row) | Is it a current slug? | In another `was:`? | Result |
|---|---|---|---|---|
| `dev-speed-first` | `dev-speed` (4.24) | no — the anchor row is deleted in S2; the `## GOAL` heading is not a tree node | no | PASS |
| `harness-speed` | `dev-speed` (4.24) | after S2, no — IF the heading is renamed, not duplicated (N2) | no | PASS (FAILED before N2's fix, in S2) |
| `token-usage-first` | `token-usage` (4.25) | no — a goal heading only | no | PASS |
| `guard-harness-audit` | `guard-and-gate-harness` (4.30) | no — a goal heading only | no | PASS |
| `compaction-guards` | `hooks-and-session-continuity` (4.33) | no — a goal heading only | no | PASS |
| `cloud-publishing` | `summarise-a-playlist` — ONLY under 4.3's ✍ alternative (merge) | no — under the alternative it is not a node | no | PASS |
| `memory-hygiene` | `memory-recall` — ONLY under 4.27's ✍ alternative | no | no | PASS |
| `dashboard-decisions` | `status-visibility` — ONLY under 4.41's ✍ alternative | no | no | PASS |

Per slice: S1 adds no `was:`. S2 adds the two on `dev-speed` (both pass once `harness-speed` is renamed). S3
adds the other three (pass: none is a tree node at any point). The new nodes' own slugs (`dev-speed`,
`token-usage`, `memory-recall`, `product`, `platform`, `dev-infrastructure`, …) were checked against every
`was:` entry above: none matches. A future `proposed:` node renamed at the owner's pick records its proposed
slug once; it passes for the same reason.

## Same-class search

- **A guard rule that contradicts a transition the migration needs** — read G1–G9 and today's
  `check-features.py` / `check-anchors.py` rules against each slice. Found N1, N2, N3 (above). Checked and
  clean: G1 after S2 (all 6 ADR slugs and every spec/plan slug except the two `dev-speed-first` headers are
  current nodes; those two re-point in S2); G2/G3 (both `epic:` parents and the one `ROOTS` key are current
  nodes; 0 answer keys); G9 (no `done:` exists during the migration); the area rules (`tooling/speed` moves
  with the renamed heading, `comprehensibility` moves in one edit, so it is never claimed twice or by none);
  the `for:` status-word ban (`STATUS_TOKENS`, `scripts/check-features.py:13`), run over all 11 NEW and (A)
  purpose sentences of §4 — 0 hits; the same-goal duplicate refusal (`scripts/goal-tree.py:312`) — no §4 merge
  puts two lines with one ref under one node (§2.3).
- **Another page with an unlisted trigger** — the full inventory is §5.1.1. Found: `/goal-tree` reads
  `docs/features.md` from S3 (`resolve()`, the node set) and nothing would have rebuilt it on an edit of that
  file — `regen-features-page.sh` rebuilds `/features` only, and `pages_for` routes only `goal-threads.md`.
  Fixed inside XM1: S3 routes `docs/features.md` → `goal-tree` in `pages_for` and adds it to
  `PAGE_SOURCES["goal-tree"]` (moved from S4, where it was a slice too late). Recorded, not fixed (not this
  design's): `PAGE_SOURCES["goals"]` (`scripts/explainer-serve.py:246`) names `docs/roadmap-to-launch.md`,
  which `gen-goals-page.py` does not read (its reads: `:435-459`); stated in §5.1.1.
- Also corrected while there: §5.1's "manifests checked for all 14" — the slice table names 15 scripts, each
  with a manifest (re-checked `scripts/mutations/<name>.json`); the hook is shell, covered by the dispatcher test.

## Count

6 findings (3 Codex + 3 coordinator): **6 fixed, 0 rejected, 0 to the owner.** XM1 is fixed by Codex's
route, with its "would miss the trigger" premise recorded as only partly true.

VERDICT: NOT CONVERGED — round 3 owed (alternation: the Claude half).
