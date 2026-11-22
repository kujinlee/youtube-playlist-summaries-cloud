# Round 2 — `marketplace-task18` — coordinator — the quote check misses a quote split by Markdown links; renamed excluded content evades by whitespace; the edge pin is a re-pin, not a loosening

Codex reviewed 3aa64ab6 (the round 1 fold of plan Task 18, PR #617): `docs/reviews/codex/marketplace-task18-r2-codex.md`.
It reports X1 MAJOR and X2 MINOR, both `fix_induced: false`, with verdict NOT CONVERGED.

REVIEW GAP: claude — alternation

Neither finding comes from round 1's fold. Both are further gaps of the same kind in the two checks, so this is not
thrashing.

## Dispositions

- **X1 (MAJOR, not fix-induced): a quote whose words are each wrapped in a Markdown link passes. ACCEPT.**
  - Under word-level normalisation, the link destinations (`https x`) become words between the quoted ones.
  - Fix: before normalising, reduce a Markdown link `[text](url)` to its text on both sides, and drop bare URLs.
  - Add a case using Codex's exact input, and a mutation for the clause.
  - The real build must still PASS.
- **X2 (MINOR, not fix-induced): renamed excluded content passes after a whitespace change. ACCEPT** (cheap).
  - The content check compares raw-byte hashes.
  - Fix: hash a canonical form (line endings unified, trailing whitespace per line dropped, trailing blank lines
    dropped) on both sides.
  - Add a case (Codex's ` \n` append, plus a CRLF copy) and a mutation.
- **The loosening answer: the `check-shipping-sets` edge pin went 356 → 358. NOT A LOOSENING.**
  - The pin is an exact edge-set digest, so any new script that imports or is imported must re-pin it.
  - The previous re-pin was backlog #685, which went 354 + 2 = 356 for the rm-backup hook in the same shape.
  - This one gained two edges and lost 0, both listed by hand in the pin's comment:
    - `check-selftest-counts.py` → `build-shipped-corpus.py`, its POPULATION row;
    - `build-shipped-corpus.py` → `fixture_git.py`, its suite's isolation.
  - The comment's two edges are this diff's two new script relations; the pin itself was not loosened.
  - What master rejects is a set master does not have, because the new script is not on master yet.
