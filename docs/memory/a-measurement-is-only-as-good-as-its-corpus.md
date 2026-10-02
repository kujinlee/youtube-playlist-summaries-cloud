---
name: a-measurement-is-only-as-good-as-its-corpus
description: "FIRES-WHEN: about to state a measurement — name the SET before the number — ⭐ 6 instances — the code did what I measured; I measured the wrong SET, the wrong PREDICATE (a name-match said 0 of 44 where a line-range test said 21), or a corpus empty in TIME. Newest and cheapest: the corpus was right and the LABEL was wrong — suite-wide counts written down as harness counts, inherited pre-packaged from a handoff. Enumerate from the RULE; name the POPULATION beside every number"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 138a01b6-fe0e-4a55-ab4d-ad4f06513742
  modified: 2026-09-13T01:35:20.587Z
---

Running the mechanism instead of asserting about it (see [[quote-the-code-dont-characterise-it]])
is necessary and **not sufficient**. Both failures below were genuinely *measured* — and both
measurements were over a corpus that omitted the dimension that mattered.

**Instance 1 (2026-09-01, backlog #84).** Reusing `_inert_lines` for block-splitting looked safe:
a probe over blockquote / indent / fence shapes showed the only newly-suppressed line was the
fenced header. The probe had **no HTML comment in it**. Against the real store it DELETED entry
`2026-09-01/16` — 47 entries → 46 — because another entry mentions `<!--` in prose and
`_inert_lines` treats an unclosed `<!--` as running to end-of-input.

**Instance 2 (same branch, hours later).** `fenced_lines` had cases for the fence *character* and
the fence *length* but none for **trailing text on a closer**. The Codex half constructed one and
the branch's own defect reproduced, one shape over: an annotated inner fence read as a closer and
a valid phantom entry with a real id reappeared.

**How to apply — enumerate from the RULE, not from recall.** Before trusting a probe, write down
every dimension the rule mentions and check the corpus covers each. CommonMark fences have four
(character, length, indent, trailing text); my corpus had two. If a sibling implementation already
exists, read its comments as a **checklist of dimensions already paid for** — `exemption_reason`
carried a comment about the length rule for exactly this reason, and I ported two of its three
hard-won rules and missed the third.

**Instance 3 (2026-09-07, PR #257).** A generator I wrote to build mutation manifests asserted
every anchor occurs **exactly once in the FILE** — and that is the wrong set. The rule it was
defending is `load_manifests`', and *that* rule is "no two mutations share an anchor". Two
mutations disabling opposite halves of one `if` passed my check, `load_manifests` refused the
duplicate, dropped one, and `run_mutations` reported **8 of 9 with no error at the call site** — a
partial that reads exactly like a complete run. The check was real, executed, and scoped to the
file when the rule is scoped to the manifest.

⚠ **Ask whose rule you are checking, and enumerate the set from THAT rule.** Mine said *file*;
the consumer's said *manifest*. Both are "unique anchors", and only one is the one that bites.
Fixed by checking both. Note the shape: this is the same session's headline finding — five
self-test cases passing because a *different* rule filtered the input first — one layer out, in
the tool built to find it.

**Instance 4 (2026-09-08, backlog #89 T4) — ⭐ THE CORPUS CAN BE EMPTY IN *TIME*, and that is the
hardest one to see, because nothing looks wrong.** The test: run a page-building fork beside a Codex
review and read the wrapper's `intrusions` field. It returned `[]`. Clean run, real instrument, real
verdict file — and it measured **nothing**. A page build researches for minutes and writes for a
fraction of a second at the very end: page mtime `10:18:36`, verdict `10:17:09`. The write landed
**87 seconds after the final snapshot**, so the before/after window contained no concurrent write at
all. Starting two processes together does not make them overlap; overlap has to be *arranged*.
⚠ **The subagent and I made this error independently and both reported it as a result** — it took
comparing two mtimes to see it, which is why this belongs in the harness and not in judgement.
Attempt 2 fixed it by writing five times at ~40s intervals across the window (one landed inside,
provably) — and an adversarial review then established the deeper point: the falsifier **could never
fire**, because `watched_dirs()` covers only `dirname(--out)` plus `docs/reviews` and the snapshot is
non-recursive, so a writer confined to `~/explainers/` can never appear there *whatever the timing*.

**How to apply — for any before/after or windowed check, ask TWO questions, not one.** (a) *Did the
event I am testing for actually occur inside the window?* Prove it with a timestamp, not by having
started both things. (b) *Could this assertion have failed at all?* If the watched set cannot
contain the thing being watched for, a green result is true and worthless — write up the **narrow**
claim ("X is invisible to THIS detector"), never the comfortable one ("X is safe").

**The tell:** a probe assembled from "shapes that came to mind" rather than from the rule's own
terms — or, for instance 4, a pass with **no evidence anything was ever in scope to fail**. Also ask
which direction an approximation fails in — `_inert_lines` over-approximates, which fails SAFE for
*"is there an ask here?"* and DANGEROUS for *"does a block start here?"*. Same set, opposite safety
direction. Related: [[measure-the-population-the-code-actually-sees]],
[[the-control-refuted-the-premise]], [[fixing-a-premise-is-not-covering-the-branch]],
[[a-test-that-cannot-fail]].

⟳ **5th instance, 2026-09-09 — the PREDICATE, not the corpus.** Building the PR-2 deletion
inventory I asked *"does this mutation anchor's TEXT contain a doomed function name?"* and got
**0 of 44**. The right question was *"is the anchor LOCATED INSIDE a doomed function?"* — the
answer is **21 of 44**. The entry I had retargeted myself that morning reads `not_measured_line(v)`
and lives at `evidence():1541`; a name match cannot see it. Same run, a second error in the
opposite direction: seeding an AST reachability walk from one entry point (`mutate_delivered`)
instead of all of them reported `not_measured_line` as safe to delete, when `main()` calls it twice
— a `NameError` in the entry point, found the slow way.

**How to apply:** when a count surprises you — especially a ZERO or a suspiciously round number —
re-derive it a SECOND way before believing it. Prefer a predicate that matches the claim's own
words: "inside X" means a line-range test, not a substring test; "unused" means *no surviving
caller anywhere*, not *unreachable from the one entry point I thought of*. See
[[measure-the-population-the-code-actually-sees]] for the sibling failure about the SET.

⟳ **6th instance, 2026-09-12 (PR #296) — the corpus was right and the LABEL was wrong, which is the
cheapest version of this and still shipped a false claim.** I wrote `harness 71 ✓ / 1 ✗ -> 73 ✓ / 0 ✗`
into a dashboard entry. Those are `check-schema-gates.sh` **suite** totals — ticks from all fifteen
gates. The harness alone is `54 ✓ / 1 ✗ -> 56 ✓ / 0 ✗`. Both numbers are correct; only the noun in
front of them was false. ⚠ **I inherited the `71/1` half from a session handoff that had counted the
same way**, so the error arrived pre-packaged and re-reading my own sentence could never catch it —
the Codex half did, by running the harness alone and getting 56.

**How to apply — write the POPULATION next to every count, in the units the command produces.** If a
figure came from `grep -c` over a log, name the log, not the component you were thinking about. When
a number arrives from a handoff or a previous session, it carries its author's corpus and not yours:
re-derive it on both sides of the change before quoting it as a before/after. And when the store is
append-only, the correction is a NEW entry — rewriting renumbers positional ids other entries cite.
