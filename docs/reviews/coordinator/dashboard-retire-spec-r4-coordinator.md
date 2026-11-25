# Round 4 — `dashboard-retire-spec` — coordinator — ⟳ NOT CONVERGED (Codex); ROUND CAP → repair path REMOVED; 3 fixed, 0 rejected

REVIEW GAP: claude — alternation (rounds 2+ run one half; Claude ran round 3, Codex runs round 4).

```yaml
round: 4
fixes_nontrivial: true
subject: dashboard-retire-spec
halves:
  codex: ran
  claude: gap
findings:
  - {id: B1, severity: Blocking, aim: deliverable, fix_induced: true, component: store-gate, disposition: fixed}
  - {id: B2, severity: Blocking, aim: deliverable, fix_induced: true, component: store-gate, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: false, component: page-identity-consumers, disposition: fixed}
```

Subject: `docs/superpowers/specs/2026-11-24-dashboard-retire-design.md` at `3b818c35` (reviewed); fold at the
commit after it.

- Codex half: `docs/reviews/codex/dashboard-retire-spec-r4-codex.md` (model `gpt-6.1-terra`, verdict
  `docs/reviews/verdicts/dashboard-retire-spec-r4-codex.verdict.json`) — 2 BLOCKER, 1 MAJOR. NOT CONVERGED.
- Claude half: not run (alternation).

## ROUND CAP — thrashing or prose floor?

`docs/review-method.md` §0 Q4c: from round 4, findings are FILED unless a BLOCKER. Both BLOCKERs change the spec;
the MAJOR is folded only because it is an inventory omission (below), not new mechanism.

**Answer: THRASHING, not a prose floor.** Per-finding evidence:

| Round | Finding | Caused by | Evidence |
|---|---|---|---|
| r2 | XM1 — a same-day merge shifts positional ids; an answer closes the wrong ask | r1's K9 mechanism (see the r3 doc for the `fix_induced` record) | r2 coordinator, four-entry fixture |
| r3 | B1, M1, m1 — K10's history walk vacuous / defeatable | r2's K10 | r3 Claude half, measured |
| r4 | **B1** — re-keying one of two duplicate asks in place re-points an existing `[resolved: shared-key]` to the other ask | r3's in-place duplicate-key repair (spec §2.3a *Bound*, r3 text) | Codex r4 against the r3 text at `:200`, `:241` |
| r4 | **B2** — K9's parse-error exception lets an old ask lose its flag or gain an answer in place | r3's K9 exception (added in the r3 fold itself, marked INFERRED, not run) | Codex r4 against `:241`; K1 only constrains entries after the prefix, so the edited entry is checked by nothing |

Same component (`store-gate`, *how an answer identifies its ask*), the third consecutive round whose findings
come from the previous fold. Each fold added a mechanism (K9's base, K10's history, K9's exception) that made an
EDIT of identity safe after the fact. **The decision is to remove the repair path, not fence it:** Codex's own
proposed fix (restrict the exception to a narrow key repair preserving flags, resolutions, body, position, and
validate affected references) would be a fourth such mechanism in the same place. With no edit permitted, the
two BLOCKERs have no subject.

## What changed

1. **K9 strict again** — every base entry unchanged and in order (`rstrip` only); the exception is deleted.
2. **Duplicates prevented at PR time** — K11 refuses an ADDED ask whose key any other entry of HEAD's store
   carries (CI's HEAD is GitHub's merge ref, master + branch), and an ADDED answer naming a duplicated key. A
   duplicate held wholly in the merge-base prefix is NOT refused — otherwise every later PR would fail on it.
3. **The residual race is stated and read FAIL-SAFE** (two PRs merged on stale CI): a duplicated key is not a
   parse error; each such entry shows OPEN with a duplicate-key warning, its `ref` falls back to its positional
   `id`, and `[resolved: <dup key>]` closes nothing (`unapplied`, reported). An ask the key had closed REOPENS
   when a duplicate lands — loud, the safe direction.
4. **Recovery is append-only** — a new ask with a fresh key restating the question; each duplicated ask retired
   by a positional `[resolved: <its id>]`. **Permanent warning? Without a marker, yes** — nothing could close the
   duplicated asks. The smallest marker justified is no new grammar: the existing positional resolve, permitted
   for a keyed ask ONLY when its key is duplicated. Safe because K11 refuses any added entry that creates a
   duplicate, so every duplicated ask a green PR sees is in K9's frozen prefix and its ordinal cannot move.

## Method — run in the fold, not taken from the half

Scratch copy = the r3 fold's keyed copy of `scripts/` plus the fail-safe rule in parse pass 2 (`dup_key`,
`unapplied`, `ref` → `id` for a duplicated key); real `parse_entries` / `unresolved` / `unresolved_heads_up`;
K11's added-only duplicate rule as a sketch over `parse_entries(base)` / `parse_entries(head)`:

| Case | Result |
|---|---|
| live store, 591 entries | identical to the r3 keyed parse in every field but the two new ones; no `dup_key`; 0 open; heads-ups `2026-08-31/5`, `2026-09-15/10` |
| two `same-key` asks on master | both open, `dup_key` set, refs `2026-11-25/1`, `/2`; no parse error |
| + `[resolved: same-key]` on a branch (the brief's fixture) | both still open; the answer `unapplied`; K11 sketch refuses the added answer |
| A answered by key, then B races in | A REOPENS; both open; A's answer `unapplied` |
| branch adds an ask colliding with master's key | K11 sketch refuses |
| unrelated branch on a master already holding the duplicate | K11 sketch: not refused |
| recovery: restate (fresh key) + positional retire of both | only the restated ask open; K11 sketch passes; then answered by key → none open |
| positional resolve of a NON-duplicated keyed ask | still refused (r3 rule unchanged) |

## Dispositions

| Finding | Severity | Disposition | Spec section changed |
|---|---|---|---|
| **B1** re-keying a duplicate re-points an existing answer | Blocking | FIXED BY REMOVAL — no entry is ever re-keyed; a duplicate is read fail-safe and an answer by the shared key closes nothing; fixture (f) | §2.3a *Unique* row, *Bound* rewritten, §3 K11 |
| **B2** K9's exception permits answering / unflagging an old ask in place | Blocking | FIXED BY REMOVAL — the exception is deleted; K9 is strict | §3 K9, §5 S2 row, §8 evidence table |
| **M1** `gen-dashboard.py:481` (`badge_of`) and `:1117` (`_resolvers.get`) still read `id` through S2 | Medium | **folded (inventory), not new mechanism** — a one-line omission from §2.3a's consumer list; both moved to `ref` in S2, with a rendered-page case (a resolved keyed ask wears *resolved* and names its resolver) | §2.3a consumer table, §4.2 file row, §5 S2 row |

**Non-trivial fixes (why `fixes_nontrivial: true`):** a deleted exception, a changed duplicate-key semantics
(error → fail-safe read), a widened K11, a permitted positional resolve for duplicated keys. Under the cap a
round 5 files anything below a BLOCKER.
