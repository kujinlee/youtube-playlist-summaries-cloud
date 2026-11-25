# After round 4 — `dashboard-retire-spec` — coordinator — Phase 6 FOLD: option (b) adopted; r1–r4 store-gate findings MOOT; 5 checks deleted, 4 added

REVIEW GAP: codex — Phase 6 fold, not a review round; the input is the architecture review, and round 1 runs again on the changed sections.
REVIEW GAP: claude — Phase 6 fold, not a review round; the input is the architecture review, and round 1 runs again on the changed sections.

```yaml
round: 5
phase: 6
fixes_nontrivial: true
subject: dashboard-retire-spec
halves:
  codex: gap
  claude: gap
findings: []
adopted: architecture-review-2026-11-24-ask-store option (b)
findings_moot:
  - {round: 2, id: XM1, component: store-gate}
  - {round: 3, id: B1, component: store-gate}
  - {round: 3, id: M1, component: store-gate}
  - {round: 3, id: m1, component: store-gate}
  - {round: 4, id: B1, component: store-gate}
  - {round: 4, id: B2, component: store-gate}
  - {round: 4, id: M1, component: page-identity-consumers}
checks_deleted: [K1, K2, K3, K9, K10, K11, key-grammar]
checks_added: [A1, F1, L1, C1]
```

`round: 5` is the slot after r4 — `check-review-decision.py` refuses two documents claiming one round — and no
review ran in it; `findings: []` is the fold's own, since the review's recommendation is not a finding.

Subject: `docs/superpowers/specs/2026-11-24-dashboard-retire-design.md` at `0c0a3368` (before); the fold is the
commit after it. Input: `docs/reviews/architecture-review-2026-11-24-ask-store.md` (Phase 6, armed by r4's
THRASHING answer in `dashboard-retire-spec-r4-coordinator.md`).

## What was adopted

The review's option (b), unchanged in shape: **one file per ask at `docs/asks/YYYY-MM-DD-<slug>.md`, the answer
written into the same file under `## Answer`.** Identity is the file stem, allocated by the tree; no answer names
its ask, so nothing can resolve to the wrong one. The old store `docs/dashboard-entries.md` is kept whole and
FROZEN (§7 Q1 A stands — header lines 3–6 only, once, in S2).

The thrashing class had two properties (review §2): an answer is a separate entry that NAMES its ask, and identity
is allocated inside one shared, ordered file. (b) removes both; the r1–r4 mechanisms each fenced one consequence.

## Which r1–r4 findings are now moot

| Round | Finding | Why it has no subject under (b) |
|---|---|---|
| r2 | XM1 — a same-day merge shifts a positional id; an answer closes the wrong ask | no positional id; no answer refers to anything |
| r3 | B1, M1 — K10's history walk vacuous / defeatable | K10 was already withdrawn; nothing walks history |
| r3 | m1 — K10 wording | as above |
| r4 | B1 — re-keying a duplicate re-points an answer | no keys; a duplicate path cannot merge (`AA`, measured by the review in both orders) |
| r4 | B2 — K9's exception lets an old ask change in place | K9 is deleted; L1 freezes the old file by digest; F1 lets a new ask only grow |
| r4 | M1 — `badge_of` / `_resolvers` read `id` through S2 | no `ref` field exists; the page reads the frozen store unchanged until S3 deletes it |

Not moot, carried unchanged: the r1 findings outside the ask identity (the by-filename loaders, `exemption_reason`
staying, R4's narrowed diagnosis, the page counts, the decision-warning in §2.4).

## Checks deleted, and what replaces them

| Deleted | Replaced by |
|---|---|
| K1 — an added store entry parses | **A1** — every file in `docs/asks/` is a readable ask (HEAD's tree only) |
| K2 — a resolve targets an earlier entry | nothing: there are no references |
| K3 — the store takes asks and answers only | A1: the directory holds ask files only |
| K9 — the store is append-only over entries | **L1** — the old store's SHA-256 equals a pin written once in S2; and **F1** — an ask in `docs/asks/` only grows (base text a prefix of HEAD's), with a PRE-COMMITTED RETREAT: a fix-induced defect in F1 deletes F1 rather than patching it |
| K10 — the history walk | (withdrawn in r3) |
| K11 and the key grammar (`[needs-you: <key>]`, `key` / `ref`, `dup_key`, `unapplied`, the fail-safe duplicate read, the conditional positional resolve) | git: the path is the key |
| — | **C1**, S2 only — `unresolved(parse_entries(store))` is empty on S2's merge ref, so the cutover leaves no ask behind |

Kept with a falsifier each: K4–K8 (K4–K6 now name `read_asks`; K7, K8 unchanged).

## Slices re-cut, and the cutover

**S1 (old: move the ask model beside the grammar) is DROPPED** — the ask model has no reader after S2, so it
leaves with the page in S3. New **S1** opens the new store beside the old one, additively (both read); **S2** cuts
over (C1, header edit, L1 pinned, old-store readers dropped, R1 and `NO-ENTRY:` removed, the rename, the skill);
**S3** deletes the page.

**Cutover rule:** master appends to the old store until S2 merges, and the goal tree reads both sources in that
window. S2 cannot merge while an ask is open in the old store (C1 on the merge ref). After S2, L1 refuses any change
to the old store on every PR (a PR's CI runs the merge commit's workflow) and on master pushes. A PR green on stale
pre-S2 CI that merges an entry after S2 turns L1 red on master and on every later PR, printing the stray text and
the restore command; the repair restores the pinned bytes and re-asks the content as a file. Loud, never lost.

## The review's open items — run in this fold

| Item | Result |
|---|---|
| `explainer-serve.py` `PAGE_SOURCES` staleness for a new ask file | `PAGE_SOURCES` is files-only (`:243`, `/_stale` at `:2070`, coverage case `:3197`). MEASURED on this machine: a created file and an atomic replace change the directory's mtime; an in-place append does NOT. Decision (spec §2.3c): a declared-directory source whose time is the max over the directory and its `*.md` children; `regen-pages.pages_for` maps `docs/asks/` to `goal-tree` |
| Path-exempt document guards over a scratch `docs/asks/` file | 24 guards, same rc with and without two clean ask files (two pre-existing non-zero, unchanged). Planted defects: `check-doc-citations` SEES `docs/asks/` (refused an out-of-range line); `check-reference-namespace` does NOT (a bare `#623` passed — `SCOPE` at `:111` is an allow-list) → S1 adds `docs/asks/` to it; `check-plan-leak` CANNOT RUN in the clone (no plan text) — NOT RUN, not a pass. No path exemption is added |
| compaction-state's bounded per-file read | `read_asks` opens each entry as `_open_regular` does (`:343`: `O_NONBLOCK`, `fstat`, regular only), cap `MAX_ASK_BYTES` 64 KiB per file and `MAX_ASKS` 1,000 entries; over either is a PROBLEM → CANNOT RUN, never a truncation. A FIFO ask file is a case |

## Spec sections changed

Status; In plain words; §1.2 loader row; prior-art row (referential gate); §2.1–§2.3c (rewritten); §2.4 (from S1,
over ask files; A1's bound); §3 Kept (A1, F1, L1, C1, K4–K6 reworded) and *Deleted*; §3 doc rules (dev-process row,
skill row); §4.2 rows (gate file, goal tree, compaction-state, gen-dashboard, explainer-serve, regen-pages, the store,
`docs/asks/`, reference-namespace); §5 (re-cut); §7 Q1 wording, the mechanical list, the mechanism paragraph and
the walkthrough line (owner's 11-24 09:57 wording named `docs/dashboard-entries.md`; to confirm in the walkthrough,
not blocking); §8 (key and duplicate rows removed, the fold's measurements added); Out of scope.

**Non-trivial (why `fixes_nontrivial: true`):** a new store shape, four new checks, six deleted, a re-cut slice
order. Owed next: a review round — both halves — on the changed sections. `check-review-decision.py` answers
ROUND_OWED for this header (r5's fixes non-trivial). ⚠ Whether that round is numbered r6 under the cap (from r4 only
BLOCKERs fold) or starts a fresh count after Phase 6 is the coordinator's call; this fold does not decide it.
