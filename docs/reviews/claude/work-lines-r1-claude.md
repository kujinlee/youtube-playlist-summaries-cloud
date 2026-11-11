# work-lines — round 1 — Claude half

Reviewed range: `d9f27342..479114be` (branch `feat/work-lines-page`).

Method: read the full diff; ran both `--self-test`s in the repo (30/30, 68/68); ran `begin-plan.py`
and `gen-work-lines.py` ONLY against copies under a scratch root
(`<scratchpad>/wl/root*/scripts/`, own `.claude/`), never against the live sentinel; applied
mutations to a scratch copy of `gen-work-lines.py` and ran its self-test. No git writes, no Postgres.
Everything below marked EXECUTED was run; anything else is labelled UNVERIFIED.

---

## B1 — Blocking — a cycle or self-parent HANGS the generator forever; the cycle "break" is dead code

**Where:** `scripts/gen-work-lines.py:97-110` (`build_forest` cycle pass), `:114-129`
(`line_state`), `:178-194` (`_render_node`).

**Input:** the exact sequence the docstring at `:81-83` names as the case it handles — arm A, arm
B, re-arm A — or simply re-arming the slug that is currently armed. Both are produced by
`begin-plan.py` itself (see M1):

```
python3 scripts/begin-plan.py A s1 --serving "the ask"
python3 scripts/begin-plan.py B s1
python3 scripts/begin-plan.py A s1
# a.md: <!-- parent: b -->     b.md: <!-- parent: a -->
perl -e 'alarm 5; exec @ARGV' python3 scripts/gen-work-lines.py --out .../out.html
-> Alarm clock: 14   rc=142
```

and `begin-plan.py C s1; begin-plan.py C s1` writes `<!-- parent: c -->` into `c.md` (EXECUTED).

**What happens (EXECUTED, pure functions with a 3 s alarm):**

```
self-parent roots: ['a'] children: [['a']]
 line_state RAISED TimeoutError: hung >3s
 render RAISED TimeoutError: hung >3s
two-cycle roots: ['a', 'b'] children: [['b'], ['a']]
 line_state RAISED TimeoutError: hung >3s
 render RAISED TimeoutError: hung >3s
```

`build_forest` attaches every node to its parent's `children` before the cycle pass. Cycle members
are never reachable from a parentless root (each node has exactly one parent, and theirs is inside
the cycle), so the `if n["slug"] in seen: n["children"] = [...]` filter at `:101-102` can never
fire — it is dead code. The fallback at `:106-110` then appends each cycle member as a root WITH ITS
CYCLIC `children` INTACT. `line_state` has no visited set, so it loops forever (no RecursionError —
a true hang); `_render_node` would recurse without bound. For a two-cycle each member is also
listed as its own root, so the line count would double-count them even if it terminated.

**Why the suite is green:** the two cycle cases (`:339-343`) assert only `build_forest`'s root
slugs; neither ever calls `line_state` or `render` on the result. Mutations EXECUTED against a
scratch copy, both survive with `30/30 self-test cases passed`:
- delete the filter at `:102` (replace with `pass`) — survives (confirms dead code);
- delete `p["cycle"] = True` at `:108` — survives (the `⛔ cycle` badge is asserted nowhere).

**Fix:** break the edge, not just the membership: when a cycle member is promoted to a root, remove
it from its in-cycle parent's `children` (e.g. walk each unseen node's parent chain to detect the
cycle, pick one member as root, and drop the back-edge). Give `line_state` and `_render_node` a
`seen` set as a second line of defence. Add cases that call `render(*build_forest(cycle))` and
`line_state` under `_try`, and assert the `⛔ cycle` badge appears exactly once per cycle and each
slug appears exactly once on the page.

---

## M1 — Major — re-arming an existing slug rewrites its lineage: self-parent, cycles, and the root's `serving` is erased

**Where:** `scripts/begin-plan.py:346-365` (`cmd_begin`).

**Input:** the "walk back to the original objective" workflow this feature exists for — the user
returns to plan A by running `begin-plan.py A …` again.

**What happens (EXECUTED in a scratch root):** `cmd_begin` unconditionally rewrites
`.claude/plans/a.md`. Its parent is re-derived from whatever is armed NOW (B), so A's true parent
is replaced and the A↔B cycle of B1 is created; its `serving` line is gone unless re-passed
(`grep -c serving .claude/plans/a.md` → `0` after the re-arm, where the first arm passed
`--serving "the ask"`). Re-arming the currently armed slug records the plan as its own parent
(`<!-- parent: c -->`). The one field the docstring says "cannot be derived from anything" is the
one silently destroyed by walking back. (The re-arm also resets the ticks — pre-existing behaviour,
but now it also destroys the head of a line.)

The new self-test even performs this sequence (`wiring` → `branch` → `wiring`, `begin-plan.py`
self-test) and so leaves `wiring.md` with `parent: branch` and `branch.md` with `parent: wiring` — a
cycle — without asserting anything about it.

**Fix:** in `cmd_begin`, never record `parent == slug`; if `PLAN_DIR/<slug>.md` already exists,
either refuse (point at `--plan .claude/plans/<slug>.md`, which re-arms without rewriting) or carry
the existing `parent:`/`serving:` markers forward rather than re-deriving them. Add a case for each.

---

## M2 — Major — the page asserts "this plan predates the work-line fields" about plans created today; "absence is a value" is not true of the writer

**Where:** `scripts/begin-plan.py:189-194` (`render_plan` emits nothing when `parent` is None),
`scripts/gen-work-lines.py:168-170`.

**Input:** arm a plan when no plan is armed and without `--serving` — i.e. any genuine new root.

**What happens (EXECUTED):** the file has no marker at all, byte-shape identical to the 121 legacy
plans, and the page renders:

```
serving absent">no parent recorded, and no stated objective — this plan predates the work-line fields
```

That is a fact the page cannot know, and for this input it is false. The comments at
`begin-plan.py` render_plan (*"Absence is a VALUE here: 'root' and 'no parent recorded' are
different claims"*) and `gen-work-lines.py:32-36` claim the distinction is recorded; the writer
never records "root", so the reader cannot draw it. The brief's own question ("does it ever state
something it cannot know … a plan with no recorded parent a 'root'?") — it does the converse:
it states "predates" for something it cannot date.

The same silent absence happens when the sentinel is present but has no `plan:` key, or the except
at `:360` fires: `parent = None`, no message on stderr, and the plan is rendered as legacy.

**Fix:** have `render_plan` always emit a marker for new plans — e.g. `<!-- parent: (none) -->`
or a `<!-- work-line: v1 -->` stamp — and have the reader render "started a new line" vs "no parent
recorded (predates the field)" from that. Print a stderr warning whenever a sentinel exists but no
parent could be derived.

---

## M3 — Major — a parent armed via `--plan` from outside `.claude/plans/` is reported as "no longer exists"

**Where:** `scripts/begin-plan.py:359` (`parent = Path(prev).stem`), `gen-work-lines.py:91-94`,
`:150-153`, `:165-167`.

**Input:** `begin-plan.py --plan docs/plans/design.md` (a documented, supported command), then
`begin-plan.py kid s1`.

**What happens (EXECUTED):** `kid.md` gets `<!-- parent: design -->`; the reader looks only in
`.claude/plans/`, so the page shows

```
⛔ 1 plan(s) name a parent that no longer exists: design — their line has lost its head.
continues <code>design</code>, which no longer exists
```

while `docs/plans/design.md` exists. Reducing the sentinel's path to its stem also lets two plans
in different directories with the same stem be conflated (UNVERIFIED as an observed case; follows
from the code).

**Fix:** record the repo-relative path (`<!-- parent: docs/plans/design.md -->`), and have the
reader resolve it relative to the repo root; only call it "no longer exists" after checking the
path itself.

---

## M4 — Major — the end-to-end nesting case passes for an ambient reason (CSS)

**Where:** `scripts/gen-work-lines.py:403-404`.

```
case("...and the child is nested under its parent in the output",
     _txt.index("one") < _txt.index("two"), True)
```

**What happens (EXECUTED):** `"one"` first occurs inside the inlined CSS (`list-style:none`, and
`.line.done` at offset 1082), which precedes all body content, so the predicate is true whatever the
tree looks like. With the nesting deliberately inverted (`one.md` given `parent: two`), the same
predicate still evaluates `True`. The case can only fail if the word `two` vanishes from the page.

**Fix:** assert on the body only and on structure, e.g. that the `<li>` for `two` sits inside the
`<ul>` opened within `one`'s `<li>` (or compare indices within the `<main>` slice, using
`<code>one</code>` / `<code>two</code>` as the tokens). Add the inverted world as the adjacent
negative.

---

## m1 — Minor — a multi-line `--serving` silently drops the objective and injects a step the Stop guard counts

**Where:** `scripts/begin-plan.py:191-192`, `gen-work-lines.py:52`.

**Input (EXECUTED):** `begin-plan.py nl s1 --serving $'first line\n- [ ] injected'`.

**What happens:** the marker spans two lines, the `SERVING` regex (single-line, `$`-anchored)
does not match, and the page shows no objective (`grep -c 'first line'` → `0`). The second line is
a checkbox: the page shows `0/2 not ticked closed`, and `--status` reports `0/2 steps ticked, 2
remaining` / `next: (before the first task heading)` — the Stop guard now counts a phantom step. A
`-->` inside the text would also close the comment early (UNVERIFIED for display impact).

**Fix:** refuse (or collapse) newlines and `-->` in `--serving`, with a case.

## m2 — Minor — the `except` tuple still catches the programming-error class it was narrowed to exclude

**Where:** `scripts/begin-plan.py:360`. `AttributeError` and `KeyError` cannot arise from a
well-formed call here (`parse_sentinel` returns a dict, `.get` cannot raise); they arise only from
code defects such as a misspelt `_pp_local.parse_sentinal` — the same class as the NameError the
comment describes, swallowed into `parent = None` with no message. The "parent is DERIVED" case
would catch that particular typo today, so this is defence-in-depth (UNVERIFIED by mutation). Also
no begin-plan mutation entry covers the new derivation block (`EXPECTED_MUTATIONS["scripts/begin-plan.py"]`
is still 18).

**Fix:** catch `(OSError, UnicodeDecodeError)` only, print a warning to stderr when the link is
lost, and add a begin-plan mutation (e.g. `parent = None` unconditionally) naming the derivation case.

## m3 — Minor — HTML escaping of `serving` and orphan names is unguarded

**Where:** `gen-work-lines.py:164`, `:151-153`. The code does escape, but EXECUTED mutations
removing `esc()` from the serving line and from the orphan list both survive (`30/30`). Only the slug
escape is held by a case. `serving` is the only free-text field on the page, so it is the one most
in need of the case.

## m4 — Minor — child order contradicts the docstring; dashboard entry is stale

- `build_forest` docstring (`:74`) says children are "newest line first"; `_render_node` (`:191`)
  sorts children ascending by `touched` (oldest first). One of the two is wrong.
- `docs/dashboard-entries.md` (new entry) says "NOT DONE: … a `ci.yml` caller step", but
  `479114be`, inside the reviewed range, adds exactly that step (`ci.yml`, `gen-work-lines
  self-test`). The entry also says the plan count is 121; the live directory now holds 122
  (EXECUTED: `work lines: 122 plan(s), 122 line(s), 26 still owing`) — fine as a dated measurement,
  noted only because the page's lede says "121 PLANS PREDATE" as a standing fact in the docstring.

---

## What I checked and found sound

- Empty and missing plan directory both return rc=2 with a named reason (EXECUTED via the suite; the
  "names the directory" case is the right repair of the masked mutation).
- Slug escaping; marker must be on its own line; step-less plan is "empty", not done.
- Open-first sort, then newest-first within state (EXECUTED, cases hold and their mutations are
  in the manifest).
- Against the real `.claude/plans/` (read-only, output to scratch): 122 plans, no markers other than
  the one `serving:` line, renders without error. B1 is therefore latent today — it fires the first
  time anyone re-arms a slug.

VERDICT: NOT CONVERGED
