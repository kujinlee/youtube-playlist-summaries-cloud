Reviewed head: 8a4d25b515c2fb836397930752259662286fecf8

# goal-node-tree spec — round 1, Claude half

**Subject:** `docs/superpowers/specs/2026-11-23-goal-node-tree-design.md` and
`docs/adr/0016-names-live-in-one-node-tree.md`, worktree `node-tree-spec`, HEAD `8a4d25b5`.
**Mandate:** adversarial. Refute the design. Re-derive the measured claims. The owner's settled
decisions (D1–D8) are not under review; whether the design delivers them is.

## What I re-derived, and what held

| Claim | Result |
|---|---|
| 35 feature nodes, 3 trunks, 31 built, 4 absent | HELD: `python3 scripts/check-features.py` |
| 15 anchors; 12 also a same-name feature node; the 3 that are not | HELD: `docs/anchors.md:30-44` against `docs/features.md` headings |
| 9 goals, 144 threads, 44 requests, per-goal thread and request counts quoted in §4 (43, 33, 29, 22, 7, 7, 1, 1, 1; 13, 10, 8, 4, 2, 2, 2, 2, 1) | HELD: a script over `docs/goal-threads.md` |
| 4 refs under more than one goal (PR #421, #422, #557, backlog #384) | HELD |
| `parse_threads` refuses the living file at line 229 | HELD as an observation. The DIAGNOSIS is wrong, see M1 |
| The 59 names → 45 nodes arithmetic | HELD: 59 − 12 (A+F) − 1 (harness-ships G) − 2 (dev-speed triple) − 1 (guard-harness-audit) − 1 (compaction-guards) + 3 trunks − 1 (`product` onto its trunk) + 1 (`memory-recall`) = 45. Every A, G and F name appears in exactly one row; none is double-mapped |
| 63 anchored specs/plans, 23 under `status-visibility` (before this spec) | HELD: 64 and 24 counting this spec |
| `ARMED_ANCHORS` names 13 of 15 and reads no registry | HELD: `scripts/check-goal-status.py:88-102` |
| 17 files name `docs/anchors.md` | HELD (`git grep -l`) |
| 358 snapshots; every goal slug in them is one of today's 9 | HELD, read-only on the main checkout's log. So `resolve()` over the existing log has a complete map |
| `.claude/agenda-log.jsonl` holds "focus per goal" | NOT HELD, see m3 |
| `-first` literal counts | HELD as LINE counts, not literals, see m13 |

## Findings

### M1 — Major — the line-229 refusal is a mis-typed ref, not a grammar gap; and the spec leaves `/goal-tree` broken for three slices

`docs/goal-threads.md:229` reads `- fix · PR #376 · plan Task 16: the publishability scan …`. Task 16
merged as **PR #613** (`36deefc9 Marketplace Task 16: the publishability scan predicts … (#613)`);
PR #376 is the marketplace-inventory SPEC (`d18167ce … (#376)`), correctly listed at line 226. The
duplicate was introduced by #613's own commit (`git log -S'Task 16: the publishability' -- docs/goal-threads.md`).

So the spec's §1 claim "One PR served two pieces of work under one goal and the grammar has no way to say
so" is false, and the `also` field would not address it anyway — `also` names OTHER nodes, while this is
a duplicate inside ONE goal. Worse, §5.3 says "The living file's line-229 duplicate is fixed in S3 by
the `also` grammar, not before": the snapshot refuses the living file today, so `/goal-tree` (and the
agenda on it) stays unbuildable across S1 and S2.

**Fix:** change line 229's ref to `PR #613` now, in its own one-line PR, ahead of this work. Delete the
§1 bullet's diagnosis and the §5.3 sentence; keep the `also` motivation on the 4 cross-goal refs, which
are real.

### M2 — Major — S2 cannot be green: two documents anchor to `dev-speed-first`, which is not a tree node until S3

`Anchor: dev-speed-first` is carried by `docs/superpowers/specs/2026-11-09-observed-reach-selection-design.md`
and its plan. In the tree, `dev-speed-first` is only an `anchors:` value of `guard-and-gate-harness`
(`docs/features.md:133`); the feature is `harness-speed`. S2 deletes `docs/anchors.md`, removes every
`anchors:` line and makes `check-anchors.py` resolve `Anchor:` against the tree — but S2's list of new
nodes is only `cloud-publishing` and `serve-money-guard`. The `dev-speed` node (and the rename) arrives in
S3. Between them, both documents fail G1, contradicting §5.1's "each step leaves every gate green".

**Fix:** S2 must create a node for this anchor — either move the 4.24 merge/rename (`dev-speed`, `was:
dev-speed-first, harness-speed`) into S2, or add a `dev-speed-first` node in S2 and rename it in S3. Say
which in §5.1, and add "S2: every `Anchor:` in specs/plans resolves" as the slice's FAILS IF.

### M3 — Major — the page-regeneration and staleness plumbing is missing from the migration, and S2 turns a self-test red

Files that key on the old sources and are not in any slice's "scripts touched" column:

- `scripts/explainer-serve.py:257` — `PAGE_SOURCES["features"]` lists `docs/anchors.md`; the comment
  at :244-247 says its self-test asserts every declared source is a real FILE. Deleting the file in S2
  turns that case red.
- `.claude/hooks/regen-goals-page.sh:36` and `.claude/hooks/regen-features-page.sh:61` trigger on
  `docs/anchors.md`. After S2, `/goals` is derived from `docs/features.md`, but no hook rebuilds `/goals`
  on an edit of `features.md`.
- After S4, `/goals` derives requests from `docs/goal-threads.md` (§2.2) and `/goal-tree` reads parent and
  `done:` from `features.md` (§3 table). `PAGE_SOURCES["goals"]` is `["docs/roadmap-to-launch.md"]`
  (:246), `PAGE_SOURCES["goal-tree"]` lacks `features.md` (:264), and `scripts/regen-pages.py`
  routes a `goal-threads.md` edit to `goal-tree` only (`regen-pages.py:952-954`). Result: a stale
  `/goals` with no `/_stale` banner — the exact silent failure the hooks exist to stop.
- `scripts/gen-features-page.py:286` and `:745` read `docs/anchors.md` (the ADR column), but S2's
  touched list omits `gen-features-page.py`. The prose "the 17 files that name it are updated" covers
  it; the column — which a plan will be written from — does not.

**Fix:** add `explainer-serve.py`, `regen-pages.py`, both hooks and `gen-features-page.py` to the S2/S4
rows, each with its mutation manifest (`scripts/mutations/regen-pages.json` exists). Add a FAILS IF:
"an edit to `docs/features.md` or `docs/goal-threads.md` does not rebuild every page that derives from
it", tested through `pages_for`.

### M4 — Major — G1 is weaker than the rule it replaces, and never checks ADRs

Today R2 checks EVERY `Anchor:` header in specs and plans, any date (`scripts/check-anchors.py:142-146`;
the date only decides whether a header is REQUIRED, :126). G1 as written fails only "a spec, plan or ADR
**dated on or after** the cutoff". Two holes:

1. Pre-cutoff documents that carry a header lose their resolution check — a loosening the spec does not
   name.
2. ADRs are named, but ADR filenames are `0016-…`, which `DATED = ^(\d{4}-\d{2}-\d{2})-` (:67) never
   matches, and `SUBDIRS` (:54) does not include `docs/adr` at all. 6 ADRs carry a header (including
   ADR-0016 itself); none would be checked.

**Fix:** G1 = every `Anchor:` header in `docs/superpowers/specs`, `docs/superpowers/plans` and `docs/adr`
resolves to a current node, regardless of date; the cutoff governs R1 only. Add `adr` to `SUBDIRS` and say
so in S2.

### M5 — Major — G5 refuses what the owner's rule requires, and the spec never says how a new name is born

`scripts/session-state.py:377-381` (backlog #514, the owner's rule of 2026-11-05): work in flight is
never added under no goal; when none fits, the AGENT PROPOSES one and the owner picks. Today a proposed
goal is allowed to reach the page and is SHOWN as a problem (`goal-tree.py:350`, "never dropped in
silence"). G5 turns that into a refusal at `--add`, so proposed-not-yet-picked work cannot be recorded at
all — unless a node, with a parent and a `for:` sentence, is first written into `docs/features.md`, i.e.
the agent allocates the name the owner was supposed to pick.

The spec has no section on how a NEW node comes to exist (who writes it, where it hangs, what marks it
proposed). Every name today was allocated by one of three routes; the spec merges the lists but not the
routes. This is a judgment call and it carries no ✍.

**Fix:** add §2.7 "How a name is born": e.g. a node may carry `proposed: <date>` (allowed for `--add`,
shown as awaiting the owner on the agenda, refused by G1 on a living spec); or keep G5 as a page problem.
Flag ✍.

### M6 — Major — a backlog row with several tags has no primary, so D5's "counted once" is not delivered on `/features`

§2.3: a backlog row's primary is "the node that claims its area tag (`areas:`, nearest claim — today's
rule)". Today's rule (`docs/features.md:15-17`) shows a row carrying several tags "under the node
claiming each one" — there is no primary. The spec measures 27 such rows (23 open). G7 only asserts a
PARENT's total equals the distinct set beneath it, so two sibling nodes may each count the same row and
G7 stays green; the owner's "counted once" holds only at the root.

**Fix:** define primary for a multi-tag row (first tag, or an explicit marker) and show the others as
shared, like an `also` thread. Extend G7: the sum of primary counts over all nodes equals the number of
distinct open rows.

### M7 — Major — "living `-first` literals rewritten" would rewrite the owner's quoted words

Of the 10 `-first` occurrences in `docs/goal-threads.md`, 8 are inside request lines —
`> 2026-11-07 20:06 "… on dev-speed-first, token-usage-first, …"` at lines 35, 86, 150 and 169 (one
request copied under four goals). The grammar says a request is "quoted exactly"
(`goal-threads.md:14-15`). §1 counts these lines among the living literals to rewrite, and S3 says
"living `-first` literals rewritten". A literal rewrite falsifies the owner's record; a text-level
"former slug in a living source fails" check would fire on them.

**Fix:** state that request lines (and `done:` quotes) are HISTORY for G1–G5: never rewritten, never
checked for former slugs. Recount §1's "6 in goal-threads.md" as 2 headings + 4 quoted requests.

### m1 — Minor — wrong cross-reference and an inconsistent depth claim

§2.2's parent row says "see ✍ row 4.20"; 4.20 is `cloud-blob-key-encoding`. The deep row is 4.38. §4.4
counts "the depth in 4.38" as a ✍ row, but row 4.38 carries no ✍. 4.38 says it is "the one place the tree
is five deep", yet 4.39, 4.40 and 4.41 sit at the same `#####` depth. **Fix:** 4.20 → 4.38; mark 4.38
✍; say "the one branch".

### m2 — Minor — `state:` of four new nodes is unstated or unflagged

§4.4 says 7 nodes have no `state:`. `memory-hygiene` (4.27) and `dashboard-decisions` (4.41) are new
from goals and given none, so it is 9 — or they need a state, which is a judgment. `cloud-publishing` and
`serve-money-guard` are given `state: built` with no ✍; ADR-0008 (serve-money-guard) is about a
dependency on grant granularity, so "built" is a claim someone should check. **Fix:** state each, ✍ the
`built` ones.

### m3 — Minor — `.claude/agenda-log.jsonl` holds no goal slugs

Measured (read-only, main checkout): 54 records; keys `kind, at, window, change_if, steps, id, of,
states, step`; no goal slug in any. §5.2's row "focus per goal … read through `resolve()`" is unfounded.
**Fix:** drop the row, or mark it INFERRED.

### m4 — Minor — `docs/goal-tree-answers.json` is a slug reader nobody lists

Its keys are `goal:<slug>` (its own `_doc`). An answer keyed on a renamed slug moves to "Older
questions". Empty today, so no data loss — but it belongs in §5.2 and in `resolve()`'s callers.

### m5 — Minor — duplicated requests have no once-only form

3 requests appear under more than one goal (one of them 4×). §3.1 derives each node's requests onto
`/goals`, so the same owner sentence repeats on several cards. D5's primary/other shape is given for
threads, ledger entries and backlog rows but not requests. **Fix:** say a request is stored once under
its primary node with `· also` (or accept the repetition, stated).

### m6 — Minor — `key_link` has a second node kind, and the link check already exists

`scripts/page_markup.py:979` — `key_link("feature", slug)` → `/features#<slug>`. The spec describes only
the `goal` kind. G8's "one link function" must fold `feature` into `goal` + `view`. `scripts/check-page-links.py`
(dangling-fragment check, :704) is the natural instrument for §3.5's "old ids keep landing"; name it as
that FAILS IF.

### m7 — Minor — D8 is a hard prerequisite of S1, and S1 reworks it

The local branch `features-tree-index` (`3221040d..30f3fad3`) builds `render_index` on the two-level
`group_tree` (`gen-features-page.py:184-195`) and pins 27 mutations. S1 changes depths and trunks. §3.2
says D8 is "built on, not redone"; S1 necessarily re-does its grouping. **Fix:** make "D8 merged" S1's
entry condition and list `render_index` plus the 27-entry pin in S1.

### m8 — Minor — G4's "any tuple of slugs in `scripts/`" names no detector

How a tuple is recognised as "of slugs" is undefined, so the rule cannot fail as written. If Q6's
recommendation (derive) is taken, the tuple is deleted and G4 reduces to "`ARMED_ANCHORS` does not exist".
Say that.

### m9 — Minor — G9 is SHAPE-only for an owner-only field

D6: `done:` is set "only on the owner's word". G9 checks a date and a quote; any agent-written line
passes. **Fix:** require the `done:` timestamp and words to equal a request line under that node in
`docs/goal-threads.md`.

### m10 — Minor — goal numbering is undefined for a node with no request

`docs/goal-threads.md:12-13`: the page numbers goals by their first request's time. §2.2 drops "a goal has
at least one request". Say how `/goal-tree` numbers or orders a node with threads but no request.

### m11 — Minor — `/goals` shows a backlog band today

`scripts/gen-goals-page.py:498` and `:769-779` render the ROOTS/DEPENDS rows per anchor. §3's table says
`/goals` does not show gaps. Say whether that band stays (G3 keeps `ROOTS`).

### m12 — Minor — `docs/features.md` becomes a conflict hotspot with no resolver

`scripts/batch-ci.py:95-101` auto-resolves `goal-threads.md` conflicts because new goals were added there
by parallel PRs. New names now land in `docs/features.md`, which has no resolver. Note it, or file it.

### m13 — Minor — "literals" are lines

`docs/dashboard-entries.md`: 9 occurrences on 8 lines; `docs/goal-threads.md`: 10 on 6. §1 says
"literals". Say "lines".

### m14 — Minor — `token-usage` will show zero gaps while its rows sit under `dev-speed`

`harness-speed`'s sentence (`docs/features.md:139`) names token usage, and its area `(tooling/speed)` goes
to `dev-speed`. `token-usage` claims no area (Q5 defers), so `/features` shows it with no gaps while its
gaps are counted elsewhere — the owner's "built hides open gaps" complaint in a new form. **Fix:** until
Q5's follow-up, render "claims no area — gaps not counted" on such a node rather than an empty count.

## ✍ coverage

Unflagged judgment calls: G5's refusal and how a name is born (M5); the `state:` of four new nodes (m2);
the primary of a multi-tag row (M6). Q6's recommendation reverses a stated design choice —
`check-goal-status.py:85-87` says arming is "a deliberate act with a visible diff" — and it is a Q, so
that one is covered. The rest of the §4 ✍ marks are where the judgment is.

## ADR conflicts beyond ADR-0010

None found. ADR-0014 (a guard's `main` is drivable) binds the new G-rules but is not contradicted; ADR-0015
is unaffected. ADR-0016's FAILS-IF list inherits M4's hole ("an `Anchor:` … that is not a current node
slug" must say "in specs, plans and ADRs, any date").

## Count

0 BLOCKER · 7 Major · 14 Minor.

VERDICT: NOT CONVERGED
