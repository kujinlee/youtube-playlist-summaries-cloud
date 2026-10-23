<!-- codex-review: model=gpt-6.1-sol -->

**Major — `scripts/gen-work-lines.py:425–435`: generated labels can collide with real plan names, silently hiding unfinished work.**

The reader preserves `(checkout, slug)` records, but encodes their identity in a display string. Both `build_forest` (`gen-work-lines.py:100`) and `work_line` (`begin-plan.py:324`) then key dictionaries by that string, overwriting collisions.

**Executed fixture:** temporary repository with a real linked worktree:

- Main: completed `kid.md`; unfinished `kid @ main.md`, with serving text “unrelated unfinished work”.
- Side: completed `kid.md`.

Observed:

```text
LABEL_COLLISION ROWS [('kid @ main', None), ('kid @ main', None), ('kid @ side', None)]
LABEL_COLLISION STATES [('kid @ main', 'done'), ('kid @ side', 'done')] OPEN 0 PRESERVED False
COLLIDING_FILE_BANNER > **Line:** _(no objective recorded)_ `kid @ main`
```

Actual page generation returned:

```text
work lines: 3 plan(s), 2 line(s), 0 still owing
```

The unfinished plan disappears from the forest, and its banner describes the completed copy. This requires a manually named file: `begin-plan` normalizes new names, but the reader accepts this filename without restriction.

**Fix:** carry `(checkout, bare slug)` as the internal key through parent resolution, forest construction, and banner lookup. Keep display labels separate. Add this collision fixture asserting three retained nodes, one open line, and the unfinished plan’s serving text in its banner.

Other executed results over final HEAD `30c8fe9c`:

- Round-4 fixture: **two open lines**, each child and banner naming its own checkout’s parent.
- Three checkouts: **three open lines**, correct ancestry throughout.
- Missing side parent: documented main-first fallback; every row retained.
- Cross-checkout cycle: traversal terminates, cycle is reported, every row retained.
- Self-tests: work-lines **56/56**, begin-plan **122/122**, banner-armed **236/236**, mutation runner **215/215**.
- Scoped mutation run: **85 killed, 85 attributed, zero survivors**.
- Restoring `894db579`’s collapse makes F5b fail: **121/122**. The original round-4 regression is now detected.

All writes and execution occurred in temporary copies/repositories. The subject worktree remained clean; no real Stop hook or real `.claude/` state was exercised.

VERDICT: NOT CONVERGED
