Reviewed head: 074ff677b020f9ce34408fe3f71767fa6bfa8207

# goal-placement (backlog #514 c + d) — round 1 — Claude half

Branch `goal-placement`, diff `origin/master...HEAD`.

Method: read the full diff of `scripts/goal-tree.py`, `scripts/session-state.py`, both manifests, the pin and the
backlog row. EXECUTED: both `--self-test`s in the worktree (goal-tree 495/495, session-state 134/134); a probe script
driving `derive` / `changes` / `agenda_digest` / `agenda_now_items` / `render_text` on the self-test's own two-goal
fixture (`_g2`); every one of the 15 new or re-bound backlog #514 mutations applied to a scratch COPY of `scripts/`
(plus `docs/goal-threads.md`, `docs/backlog.md`) and that copy's self-test run, reading which `[FAIL]` lines appear —
with an unmutated control copy (goal-tree: 492/495, the 3 reds are the Ask-tray explainer cases that need the
tracked explainers, unrelated). The full `check-plan-code.py --mutate` sweep was NOT run (379 + 117 mutants);
its attribution rule (`run_mutations`: `expect` must equal exactly one parsed `[FAIL]` name) was read and applied by
hand. Callers of `--add` grepped across `scripts/`, `.claude/`, `.agents/`, `.githooks/`, `.github/`, `docs/`.
Nothing in the repo was modified; no GitHub.

Confirmed correct (attacked, held): a ref match wins and the entry is not ALSO placed (no double placement — the
placement loop runs over `unnamed` only); an owner-wait with a goal stays a NEED; an undeclared goal stays under no
goal and is both a ledger problem and flagged on its line; a goal compared case- and whitespace-sensitively (`G`,
` g` are not `g` — never a loose match); `--goal ""` with no thread is refused (exit 2), `--thread X` with
`--goal ""` raises and is caught as CANNOT RUN (exit 2); the one external caller of `--add`
(`.claude/commands/goal-tree.md:40`) passes both flags and still works; all 11 goal-tree mutations go red via the
case they name.

## Findings

### F1 — MAJOR — the "waits for" half of (d) is not built, yet the backlog row says (d) is built

`scripts/goal-tree.py:1490-1491`, `docs/backlog.md:503` (row 514's status cell).

The row's part (d) has two halves: placement by the `goal` field, and *"the same gap empties the page's 'waits
for' … so read the entry's own `waits` too."* The branch builds the first and hard-codes the second:
`agenda_digest` emits every placed entry with `"running": False, "waits": None`. The comment's reason is true — the
ledger has no `waits` field — but that makes the row's proposed fix a hypothesis that failed, not a part that was
built. Executed input: a ledger of `{"id": "x3", "what": "agent building", "goal": "g"}` →
`agenda_now_items` gives `{'label': 'x3', 'goals': ['GOAL 1 · g'], 'running': False, 'waits': None}`, which
`agenda_html` (`goal-tree.py:2055-2056`) draws under **"Owed — not being worked"** with **"waits for: not
recorded"** — the exact symptom the owner raised, now for work that IS in flight and placed. The status cell
"parts (c) and (d) built" overclaims, and the review brief itself repeated the claim ("no longer starts hard-coded
to None").

Fix: either (i) build it — a `--waits TEXT` on `session-state.py --add`, stored, carried into the `placed` dict and
read in `agenda_digest` (and decide `running` for a placed entry rather than defaulting to owed); or (ii) narrow the
row: "(d) placement built; the waits half is NOT — the ledger records no `waits` field, so it needs one (part e)",
and file that, so the row is not closed on a half.

### F2 — MAJOR — mutation "backlog #514 (c): a goal-only entry is refused" crashes the suite before its named case

`scripts/mutations/session-state.json` (that entry); crash at `scripts/session-state.py:924-926`.

The edit `if thread and not goal:` → `if not (thread and goal):` makes every goal-only `--add` raise. The fixture at
`session-state.py:915-924` now adds its entries with `--goal g` and no thread (this branch's own edit), so they are
all refused and `led3["new-instr"]` raises `KeyError: 'new-instr'` — the self-test dies with a traceback and prints
no `[FAIL]` line at all. EXECUTED in a scratch copy: rc=1, zero `[FAIL]` lines. `run_mutations` requires the
`expect` name to equal exactly one parsed `[FAIL]` (zero matches = "caught by something else", not attributed),
so this mutant is a SURVIVOR in the sweep — CI red on the first run that selects `session-state.json`.

Fix: make the earlier fixture not crash when an add is refused (read `led3.get(k, {}).get("kind")`, or assert the
adds' return codes as a case first), or re-anchor the mutation on `main`'s path only; then re-run the mutant and see
its named case red.

### F3 — MAJOR — mutation "backlog #514 (c): the refusal never says to propose a goal" does not compile

`scripts/mutations/session-state.json` (that entry), target `scripts/session-state.py:342-345` (`ADD_NEEDS_GOAL`).

The edit replaces `When no "\n                  "goal fits, … counter-proposes) "` with `"\n                  "`,
which leaves a `"` opening a literal at end of line: EXECUTED → `SyntaxError: unterminated string literal
(detected at line 345)`. No case runs, no `[FAIL]` is printed, so it is a survivor (as F2), and even if it were
credited it would prove nothing about the sentence it names. Fix: an edit that stays inside one literal, e.g.
replace `propose a new goal named for its objective (the owner picks the name or counter-proposes) ` with `` — then
the `"propose" … "objective" … "owner picks"` case goes red by itself.

### F4 — MINOR — a ref in prose silently overrides the declared goal, with no flag

`scripts/goal-tree.py:601-608` (placement only over `unnamed`).

Input: `{"id": "x1", "what": "fold r2; unblocks PR #21", "goal": "g"}` where `PR #21` is a thread under goal `h`.
Result: hung under `h` (`… in flight: fold r2; unblocks PR #21`), nothing under `g`, no ledger problem. For a
goal-only entry `_ledger_refs` reads refs from free prose, so an incidental mention outranks the one structured
declaration the entry carries. This matches the row's wording ("when no ref matches"), so it is MINOR — but the
disagreement is invisible. Fix: when a goal-only entry's ref-matched threads lie in no thread of its declared goal,
add a ledger problem ("entry x1 declares goal g but its refs place it under h").

### F5 — MINOR — the timeline misreports two transitions of a placed entry

`scripts/goal-tree.py:696-702` (`changes`).

(a) Placed → ref-matched (a PR gets declared): `changes` prints `no longer in flight: x2` while the entry is still in
flight on the thread (EXECUTED; the same class existed for loose → thread before, now extended to placed).
(b) Placed → parked (or back): `changes` returns `NO_READER_CHANGE` ("differs only in wording") although the tree
redraws `⏳` as `⬜ parked` (EXECUTED both directions). Fix: index in-flight by id across loose, placed AND
thread-hung ledger ids, and emit a line when a placed entry's `parked` flips.

### F6 — MINOR — the undeclared-goal flag can name a goal that IS declared; `--add` accepts any string

`scripts/goal-tree.py:610,617` (`_SS.clean` on `goal_undeclared`), `scripts/session-state.py:1580`.

Input: `goal: " g"`. The ledger problem says `goal ' g' is not declared` (correct), but the entry's own line,
through `_SS.clean`, says `its goal 'g' is not declared` — and `g` is declared, so the reader is told something
false. Separately, the refusal is satisfied by `--goal " "` or a typo; the tree catches it, but only after the fact.
Fix: render the flag with `repr` of the raw value (as the problem does); optionally have `--add` warn when the slug
is not a `## GOAL` of `docs/goal-threads.md`.

VERDICT: NOT CONVERGED
