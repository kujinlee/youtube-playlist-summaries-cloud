---
name: a-measurement-is-only-as-good-as-its-corpus
description: "FIRES-WHEN: about to state a measurement — name the SET before the number — ⭐ 6 instances — the code did what I measured; I measured the wrong SET, the wrong PREDICATE (a name-match said 0 of 44 where a line-range test said 21), a corpus empty in TIME, or the right corpus under the wrong LABEL. Enumerate from the RULE; name the POPULATION beside every number"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 138a01b6-fe0e-4a55-ab4d-ad4f06513742
  modified: 2026-09-13T01:35:20.587Z
---

**The rule: running the mechanism is necessary and NOT sufficient — the measurement is only as good as the set it
ran over.** Every instance below was genuinely measured; each corpus omitted the dimension that mattered.

**How to apply:**
1. **Enumerate the corpus from the RULE, not from recall.** Write down every dimension the rule mentions and check the
   probe covers each (CommonMark fences: character, length, indent, trailing text). Read a sibling implementation's
   comments as a checklist of dimensions already paid for.
2. **Ask WHOSE rule you are checking** and take the set from that rule (file vs manifest).
3. **For any before/after or windowed check, ask TWO questions:** (a) did the event actually occur inside the window —
   prove it with a timestamp, not by having started both things; (b) could this assertion have failed at all? If the
   watched set cannot contain the thing, write the NARROW claim ("X is invisible to THIS detector").
4. **Use a predicate that matches the claim's own words** — "inside X" is a line-range test, not a substring test;
   "unused" means no surviving caller anywhere. **Re-derive a surprising count (a ZERO, a round number) a second way.**
5. **Write the POPULATION next to every count, in the units the command produces.** A number from a handoff carries
   its author's corpus — re-derive it on both sides before quoting a before/after.
6. Ask which direction an approximation fails in — the same over-approximation is SAFE for one question and
   DANGEROUS for another. In an append-only store, a correction is a NEW entry.

**The tell:** a probe assembled from "shapes that came to mind", or a pass with no evidence anything was ever in scope
to fail.

## History (measured)

1. **2026-09-01, backlog #84:** reusing `_inert_lines` for block-splitting passed a probe with no HTML comment; against
   the real store it DELETED entry `2026-09-01/16` (47 → 46) because an unclosed `<!--` in prose runs to end-of-input.
2. **Same branch:** `fenced_lines` had cases for fence character and length, none for **trailing text on a closer**;
   the Codex half built one and a phantom entry with a real id reappeared. I had ported two of `exemption_reason`'s three
   hard-won rules.
3. **2026-09-07, PR #257:** a manifest generator asserted anchors unique per FILE; `load_manifests`' rule is per
   MANIFEST. A duplicate was dropped and `run_mutations` reported **8 of 9 with no error**.
4. **2026-09-08, backlog #89 T4 — empty in TIME:** `intrusions` returned `[]` because the page write (`10:18:36`) landed
   **87 s after** the final snapshot (`10:17:09`). The subagent and I made this error independently. A review then showed
   the falsifier could **never** fire: `watched_dirs()` covers only `dirname(--out)` + `docs/reviews`, non-recursively.
5. **2026-09-09 — the PREDICATE:** "does the anchor TEXT contain a doomed function name?" → **0 of 44**; "is it LOCATED
   inside one?" → **21 of 44**. Same run, an AST reachability walk seeded from one entry point (`mutate_delivered`)
   called `not_measured_line` safe to delete; `main()` calls it twice.
6. **2026-09-12, PR #296 — the LABEL:** I wrote `harness 71 ✓ / 1 ✗ -> 73 ✓ / 0 ✗`; those were `check-schema-gates.sh`
   SUITE totals across fifteen gates. The harness alone: `54 ✓ / 1 ✗ -> 56 ✓ / 0 ✗`. The `71/1` came pre-packaged from a
   session handoff; the Codex half caught it by running the harness alone.

Related: [[quote-the-code-dont-characterise-it]], [[measure-the-population-the-code-actually-sees]],
[[the-control-refuted-the-premise]], [[fixing-a-premise-is-not-covering-the-branch]], [[a-test-that-cannot-fail]].
