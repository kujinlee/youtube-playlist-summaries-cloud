Reviewed head: b6110b2d713e755aeb78dfed077bee12ae4b5358

# Round 3 — `marketplace-task19` — Claude half — a 100,000-deep JSON value parses but cannot be repr'd, so `_check_inputs`' own messages raise; the map's package is type-checked but never resolved

Subject: PR #618, plan Task 19, `scripts/check-inventory.py`. The fold under review is `git diff c9228bbf..HEAD`
(the r2 fold, d56f267c). Python 3.14.4, macOS. Every probe below was run. The scratch trees and scripts are under
`/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/b387c8e6-9003-42f5-a944-1d4eb1de0c9b/scratchpad/task19/r3-claude-work/`
(`t20.py`, `deep.py`, `deep_old.py`, `probe2.py`, `mut1.py`).

## What held

- **Self-test:** 267/267 in a full clone at b6110b2d. The docstring says 267.
- **Real committed inputs:** no over-refusal. The live tree gives rc 1, 34 errors, all `[missing]`, and no CANNOT RUN. A copy of the live tree gives the same.
- **Plausible Task 20 rows:** no over-refusal.
  - I added 34 synthesized effort-3 rows to a copy of the live tree (`t20.py`), so that every component in `components.json` has a row. They include:
    - integer and float costs;
    - integer route costs (cheap routes, `cost_hours` 0.5 and 1);
    - `harvest: practice` rows naming a real heading, and `practice_entry: null` on the others;
    - `scenario: null`, `notes: null` and `struck` C4 on data rows;
    - `measured` rows with finding and experiment grounds.
  - That tree gives rc 0. A variant with `inherited` library rows also gives rc 0.
  - With every phase-1 row at 6/1, it gives rc 3 (34 phase-1 rows).
  - An unbacked SHIP entry-point gives rc 1 `[ship-experiment]`.
- **Fix-induced numeric boundaries** (each on a live-tree copy, field `brief-compose.cost` or `.route`):

  | Input | Field | Result |
  |---|---|---|
  | `-0.0` | public bar | rc 1 `[shape]` |
  | `-0.0` | next project | rc 1 `[next-project]` |
  | `-0.0` | route | rc 1 `[shape]` |
  | `True` | all three fields | rc 1 `[shape]` (`bool` is never treated as an int) |
  | `int(sys.float_info.max)` | public bar | rc 0 |
  | `int(sys.float_info.max)` | next project | rc 0 |
  | `2**1024 - 1` | all three fields | rc 1 `[shape]` |
  | `1e-320` (subnormal) | next project | rc 0 |

  The `abs(v) <= sys.float_info.max` guard is slightly stricter than `float()`. An integer in `(float_max, 2**1024 - 2**970)` would round to `float_max` rather than overflow, and it is refused. No cost in hours lives there, so this is not a finding.
- **Under-refusal, by my own enumeration of every input access:** I read every input access in `row_errors`, `_backs`, `_named_entry_point`, `inventory_errors`, `load` and `checkpoint_fires`.
  - Every field a rule reads, for its TYPE, is in `_check_inputs` or `ROW_SCHEMA`.
  - `recall.a` and `recall.b` are compared with `is True` and `== "pass"`, which is safe for any type.
  - `inventory.scan` is compared with `!=`.
  - The scan's `mentions` and `status` are never read.
  - The fuzz pass's sampled-out region (scan list items past the second, and entries no row names) is covered by code that loops over every entry with `all(...)`. I established that by reading the code, not by a probe in that exact region. The probe I ran was a 100000-deep finding id on `skill-brief`'s first finding: rc 2 CANNOT RUN.
- **Exit-code ranks:**
  - An early CANNOT RUN (rc 2) outranks rc 1.
  - The `ctx` construction (`v["channel"]`, `set(v["components"])`) is equivalent to the old `(v or {})` form once `_check_inputs` has passed.
  - I found no input that was rc 1 or rc 3 at c9228bbf and is rc 0 now.
- **Mutations**, in a full `git clone` at b6110b2d with `node_modules` linked (`typescript` present), at `.../r3-claude-work/clone`:
  - `check-plan-code.py --mutate . --only scripts/check-inventory.py` reports "124 mutation(s), 124 killed, 124 attributed to the case each names, 0 survivor(s)" (60 s).
  - I also applied 9 of the 26 new mutations by hand (`mut1.py`) and confirmed that each one's NAMED case is among the failures. The file was restored byte-identical afterwards. The 9: "an integer past the float range reaches math.isfinite", "an integer is never finite", "a non-string finding id reaches the id set (CODEX X2)", "a non-object scan entry outside the map is accepted", "a non-object recall is accepted", "JSON nested too deep reaches a RecursionError", "a spec that is not UTF-8 reaches a UnicodeDecodeError", "a boolean component effort is an integer" and "a sidecar scenario of any type is accepted".
  - Pins: the manifest has 124 entries; `expected_mutations.py` says 124; the self-test runs 267 cases. They agree.

## Findings

### C1 — MAJOR — `fix_induced: true` — a value nested between the repr limit and the parser limit parses, then `_check_inputs`' own error message raises `RecursionError`: a traceback with exit 1, not CANNOT RUN with exit 2

**What the fold did.** The r2 fold made JSON nested *past the parser's stack* unreadable (`_read_json` catches `RecursionError` from `json.loads`).

**The gap.** The parser's limit and `repr`'s limit are different:
- `json.loads` accepts a list nested 116,207 deep (measured here).
- `repr` overflows from about 87,157.

A value in that window parses. Then every `{...!r}` of it in an error message raises `RecursionError: Stack overflow ... while getting the repr of an object`. That is an uncaught traceback, and **Python exits 1**. Exit 1 is the "row errors" code, not 2, so the rank "unreadable → 2" is broken. CI still goes red, so this fails closed, not open. The r2 fuzz pass's 21 fixed values and 6 random nested values never reached that depth.

**Input** (`deep.py`, a copy of the complete t20 tree; the value `"[" * 100000 + "]" * 100000` is substituted into one field):

| Field | b6110b2d (this fold) | c9228bbf (before the fold) |
|---|---|---|
| `inventory.json` `recall` | **rc 1, RecursionError** (new `_check_inputs` message) | rc 0 (accepted) |
| `components.json` `components[0].phase` | **rc 1, RecursionError** (new `_check_inputs` message) | rc 0 |
| `components[0].effort` / `.roles` / `.id` | rc 1, RecursionError (now in `_check_inputs`) | rc 1, RecursionError (in `row_errors`' `[map]` message) |
| `components[0].package` | rc 1, RecursionError | rc 1, TypeError (unhashable) |
| `inventory.json` `rows[0].effort`, a ground `kind`, a ground `ids` item | rc 1, RecursionError (`_shape_errors` / `row_errors` messages, r1 code) | the same |
| `inventory.json` `scan` | rc 1, RecursionError (`inventory_errors` message) | the same |
| sidecar `scenario`; scan finding `id` | rc 2 CANNOT RUN (these messages repr only the key) | — |
| a row's `notes` (unread) | rc 0 | rc 0 |

**Why it counts as fix-induced.**
- Two of these sites, `recall` and the component `phase`, went from a clean rc 0 to a traceback *because of* the fold's new `!r` messages.
- The fold's own recursion fix claims the class ("JSON nested past the parser's stack is unreadable, never a crash"), but covers only the part above the parser's limit.
- The row-level sites are r1 code with the same cause.

**Expected:** rc 2, `CANNOT RUN`, for every one of these.

**Proposed fix: one structural refusal, not per-message patches.** In `_read_json`, after the parse, walk the value iteratively and raise `CannotRun` when the nesting depth exceeds a small bound (for example 64). The committed inputs nest at most 7 deep: inventory 7, shipping-sets 7, scan 6, components 5, sidecar 5. That puts every value a message could repr under the limit, whatever the stack size.
- Case: the `recall` input above at depth 100,000 gives rc 2 "nested too deep". The adjacent negative is the live tree at depth 7, which gives no CANNOT RUN.
- Mutation: the bound removed, killed by that case.
- Using `reprlib` in the messages would also work, but it is N edits that the next new message can miss.

### C2 — MINOR — `fix_induced: false` — the map's `package` is type-checked but never resolved, so a component whose package names no `packages` entry silently skips the SHIP rule (rc 0 where rc 1 is due)

**What the fold checks.** `_check_inputs` checks that `package` is a string. It does not check that `cmap["packages"]` has that package. `row_errors` gates the §9 SHIP rule on `ctx.channels.get(package) == "plugin"`, so an unresolved package reads as "not a plugin" and the rule is skipped.

**Input** (`probe2.py`, a copy of the complete t20 tree):
- **Control:** `brief-compose` at `verdict: SHIP`, `route: null`, `phase: later`, with no backing tier-A entry. This gives **rc 1** `[ship-experiment]`.
- **The probe:** the same row, plus `components.json` `brief-compose.package` set to `"comprehensibilty"` (a typo) and its `phase` set to `later`. This gives **rc 0**, "OK: 46 rows, 0 errors".

For a phase-1 component, the typo is caught anyway by `[shipping-set]` or `[package-shipping]`; for a later-phase one, nothing catches it.

**A neighbour of the same kind:** a duplicate component id in `components.json` is not refused.
- An identical duplicate gives rc 0.
- A duplicate whose copy has effort 2 gives rc 1, with a `[map]` message that blames the row rather than the map.

**Mitigation, measured by reading:** `check-shipping-sets.py`'s `load_map` already refuses both cases on the committed map ("a `package` that `packages` names"; "component id ... appears twice"). So this is a gap in depth, not an open hole on the live tree today, and it was the same at c9228bbf.

There is also an observation for the coordinator here. `_check_inputs`' map clauses are a second, weaker copy of `load_map`'s rules: type-only, with no uniqueness, no reference check and no vocabulary check.

**Expected:** rc 2 CANNOT RUN, "component brief-compose names package 'comprehensibilty', which components.json's packages does not have".

**Proposed fix:** add the two checks (the package resolves, and ids are unique) to `_check_inputs`, each with a case and a mutation. Or call `load_map` instead, if its file-existence rule can be satisfied in the fixture worlds. File it rather than fold it if round 4 is under the cap.

## Phase 6 note for the coordinator

C1 is fix-induced. The r2 coordinator filed X2 (the input validation) under component `inputs` and X1 under `shape`. C1's new sites are in `_check_inputs` and `_read_json`, which is the `inputs` component. Whether this arms the thrashing condition ("two consecutive rounds whose findings came from the previous round's fix, in one component") turns on whether r2's fix-induced finding (X1, `shape`) and this one count as the same component. That is the coordinator's call to record.

VERDICT: NOT CONVERGED
