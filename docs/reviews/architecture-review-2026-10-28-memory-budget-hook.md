# Architecture review — 2026-10-28 — which file is "the memory index"? (PR #430, the memory-budget hook)

**Convened by THRASHING** (`docs/dev-process.md`): `hook` carries findings caused by the previous round's own fix in
rounds 2, 3, 4 and 5 (Q1, R2, S3, T2). `check-review-decision.py` ranks `hook` first by 4. The subject is small — an
advisory PostToolUse hook registered by the owner's decision — and that is the point: the wall below is not a property
of large code.

## The wall, named once — the fifth subject in two days to hit it

After the fixture, em, import-time-launch and compaction-guard reviews: **a check that asserts a property of ARBITRARY
INPUT that the input itself can defeat.** Here the claim was *"the hook fires on every tool write to the index"*, and
the input is a pathname. Each round found one more spelling of the same file that the last rule did not recognise:
the harness symlink (r1), a lexically matching alias into another checkout and a newline-named checkout (r2), a
newline-named alias file and a link to a non-index file (r3), a case alias and a hard link (r4), a hard link inside an
unrelated checkout (r5). Rounds 2–3 were also bash mangling names (`dirname`, `$(…)`), removed by structure in r3.

## What held, measured

Bash no longer touches a pathname (r3). The index is identified by FILE IDENTITY — `samefile` against the index of each
checkout containing the edited path, from its lexical and resolved forms (r4) — so every alias that lies INSIDE its own
checkout is seen by construction, and every earlier reproduction stays fixed. rc 0 on every hostile input tried; the
checker is bounded at 20 s and its output at 4,000 characters, decided before truncation (r5).

## Decision (owner's standing AFK rule — not critical)

**DEFER, terminal: ship it with the bound stated, and stop.** No further rule over pathnames is attempted. What the
hook does not see is written in its header, its `decide` docstring and `ci.yml`: a hard link to one checkout's index
placed in another checkout or outside every checkout, and any write not made through the tool. Both are advisory
misses — the CI step on committed growth remains the failing gate — and the second was already the case before this
PR. A complete answer would need a registry of every checkout's index identity, which is a different and larger
mechanism than an advisory hook; it is not filed, because no observed write has taken either route.

⚠ **Falsifier for this decision:** an over-budget index reached by a tool write whose path lies INSIDE the index's own
checkout, for which the hook stays silent. That would mean the identity rule itself is wrong, not just bounded.
