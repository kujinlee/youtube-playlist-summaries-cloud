Reviewed head: 465de1ce982ad598fc8e09d05802c76306f55d38

# PR #637 (goal-node-tree-s2) — round 3, Claude half: the loosening answers

Scope: the 72 lines `check-merge-ready.py` flags as removed or rewritten near a failure path. For each one
I read the change in context (`git diff origin/master...HEAD -- <file>`) and tried to build an input that
master refused and the branch now accepts. Where I found one, I ran it.

## How I judged the vocabulary swap

The slice replaces the registry's 15 slugs with the tree's node slugs (37 nodes today). That makes one
kind of input pass on every path: a slug that is a tree node but was never a registry row, for example
`Anchor: summarise-a-video`, `epic: summarise-a-video`, or a ROOTS key `summarise-a-video`. Master
refused it and the branch accepts it. I do **not** count this as a loosening. The refusal still exists
("a name outside the defining vocabulary fails"), the vocabulary is defined in a different file, and
spec §S2 together with ADR-0016 says so in plain words ("every former consumer of the registry's slug
set takes the tree's CURRENT slugs instead"). Adding a node is the same one-line act as adding a
registry row was. I checked that all 15 former registry slugs are nodes of `docs/features.md`. Five of
them sit at `####` depth: `cloud-publishing:27`, `serve-money-guard:97`, `cloud-blob-key-encoding:107`,
`feature-map:174` and `harness-ships-elsewhere:205`. `dev-speed-first` survives as a `was:` of
`dev-speed`. The live `check-goal-status` armed set is still exactly the 13 slugs master hard-coded.

The findings below are therefore about rules that are gone, or about a reader that got narrower. They
are not about the vocabulary being swapped.

## Findings

### F1 — Medium — check-goal-status: a header that only master's reader could read no longer arms its document
Ids `cb8bb9964f53`, `41db02b70dc0`, `281fa3f23926`.

Master read the anchor in `check-goal-status.living_documents` with
`ANCHOR_LINE = \*\*Anchor:\*\*\s*`([^`]+)`` anywhere in the first **18** lines. That regex needs no
blockquote and no `— **ADR:**` tail. The branch reads it with `check-anchors.parse_header`, which looks
at the first **10** lines and requires the full `> **Anchor:** `x` — **ADR:** …` form. A document dated
before CUTOFF (2026-08-25) whose header master could read but the branch cannot is now unarmed. Its
missing Status turns from a FAILURE into a warning. `check-anchors` R1 does not catch it either, because
R1 applies only to documents dated on or after CUTOFF.

I ran this input: a tree holding `cloud-sync`, plus
`docs/superpowers/specs/2026-01-01-old.md` = `# Old\n\n**Anchor:** `cloud-sync`\n\nno status\n`.
- master `check-goal-status.main`: **rc 1**, "`cloud-sync` is armed".
- branch `check-goal-status.main`: **rc 0**, "armed anchors: " (empty).
- branch `check-anchors.audit`: `[]`.

Today the corpus contains no such document. Over all 207 specs and plans, the old and new readers
disagree on **0** documents (measured by running both readers over every file). So this is a latent
loosening, not a live miss. The r1 MINOR-4 fold made the change on purpose ("ONE header reader"), and
the self-test pins it (`living_documents reads the anchor with check-anchors' reader`). Possible fixes:
make a header-shaped line that `parse_header` rejects (a bare or mis-formed `**Anchor:**` in the first
18 lines) a failure in `check-goal-status`, or extend R1-style shape checking to every date. Either one
keeps the single reader without the silent unarming. Or the owner accepts the narrowing as it stands.

### F2 — Low — check-anchors: R4 "every registry anchor is claimed by a document" is dropped, not moved
Ids `3a3a2417a186`, `2f93ab5c0a6a`.

No reader anywhere still refuses a goal name that no document claims. The closest neighbour is the
`built`-needs-a-fragment rule in `check-features.check_nodes`, and an `areas:` or `adrs:` line
satisfies it. The page also still gives such a node a goal card: `gen-goals-page.goal_nodes` includes
any node with `adrs:`, even when no document names it. Master's R4 refused exactly that shape (a
registry row with ADRs and no document). The self-test pins the drop ("a node with no document is
fine"). **ADR-0016 § Consequences, line 99, records the drop as decided**, so this is an approved
loosening. It is still a loosening, and the merge gate should send it to the owner. It should not be
waved through.

### F3 — Low — a backlog `epic:` may name a `proposed:` node, which every other G3 consumer refuses
Ids `2ec67e35ad65`, `99f12f04ec8d`.

`check-features.kind_problems` and `gen-backlog-page.parent_errors` take `current_slugs(nodes)`, and that
set includes proposed nodes. `check-anchors.name_problem` refuses a proposed slug for an `Anchor:`
header, a ROOTS key and a DEPENDS root, on the grounds that the name is unsettled (spec §2.7). Spec §S2
lists the `epic:` check among the G3 consumers. I ran this input: a tree with
`### fresh\nfor: …\nproposed: 2026-11-23 10:00` and a row with `epic: fresh`. Master refused it,
because `fresh` is not a registry row. On the branch, `parent_errors(...) == []`, while
`name_problem(nodes, "fresh")` refuses the same slug. Fix: route the `epic:` check through
`name_problem`, or through a "current and settled" set, so that one G3 rule holds for all four
consumers.

### Notes, no finding
- `check-features`: master's three `check_cross` anchor rules (unknown anchor, anchor claimed by two
  nodes, anchor claimed by no node) are gone together with the `anchors:` field. A node can no longer
  carry the field. `parse_features` refuses it by name (`RETIRED_FIELDS`). Slug uniqueness is
  `slug_problems` (G6). "A node claims no anchor" cannot happen now that the anchor IS the slug.
  `check_nodes` now receives the live anchored set (`main` → `check-anchors.anchored_slugs`) in place
  of `frozenset()`. That is stricter: a `built` node whose only fragment is a document fails once the
  document is gone.
- When the tree is missing or empty, every reader that used to refuse a missing or hollow registry
  still refuses, now with exit 2 (CANNOT RUN): `check-anchors.main` → `read_tree` / `TreeUnreadable`,
  `check-goal-status.main` → `ca.read_tree`, `gen-goals-page.main` → `read_tree`,
  `gen-backlog-page.node_slugs` (raises `ValueError`), and `check-features.main` (`not nodes`). A
  malformed tree is refused too, which master never checked. For `check-anchors`, master's
  missing-registry result was an exit-1 finding and the branch's is exit 2. Both refuse.
- `gen-goals-page.collect` is now stricter. A document anchored to a non-node used to be dropped
  silently (`continue`) and now raises `SystemExit` naming the document.
- G1 is stricter than R2. It applies at any date and also to ADRs, it refuses a `was:` slug, and it
  refuses a proposed slug. G3 is stricter than R5 because it adds DEPENDS roots.
- `check-shipping-sets` `(363, …)` → `(368, "bdc110af044ece88")`. This is an exact-equality pin moved
  to the new live set, and each step has a hand diff in the comment. It accepts nothing new.

## Self-tests (run at the reviewed head)

| Script | Result |
|---|---|
| `check-anchors.py --self-test` | 23/23, rc 0 |
| `check-goal-status.py --self-test` | 40/40, rc 0 |
| `check-features.py --self-test` | 100/100, rc 0 |
| `gen-goals-page.py --self-test` | 85/85, rc 0 |
| `gen-features-page.py --self-test` | 54/54, rc 0 |
| `gen-backlog-page.py --self-test` | 252/252, rc 0 |
| `check-shipping-sets.py --self-test` (its 368 pin is a flagged line) | 170/170, rc 0 |

Live runs: `check-anchors` rc 0 (73 headers name 15 nodes, 6 ADR headers), `check-goal-status` rc 0
(the same 13 armed slugs as master), `check-features` rc 0 (37 nodes).

VERDICT: NOT CONVERGED

## Loosening answers
LOOSENING-CHECK ae760b4ab0f9: not a loosening
LOOSENING-CHECK bb1a8c666480: not a loosening
LOOSENING-CHECK f1c9aace0e5c: not a loosening
LOOSENING-CHECK 638463189ba3: not a loosening
LOOSENING-CHECK 3a3a2417a186: finding: R4 is dropped — a goal node that no document claims (one with only adrs: still gets a goal card) now passes; master refused a registry anchor that no document claimed (approved in ADR-0016 Consequences, owner to confirm)
LOOSENING-CHECK 2f93ab5c0a6a: finding: R4 is dropped — an allocated name that no document uses passes; master refused it (approved in ADR-0016 Consequences, owner to confirm)
LOOSENING-CHECK ae0653c750c9: not a loosening
LOOSENING-CHECK aa56b36981a5: not a loosening
LOOSENING-CHECK 45c717f44d4b: not a loosening
LOOSENING-CHECK 6f62d37ef77e: not a loosening
LOOSENING-CHECK b7e6b4a76ac8: not a loosening
LOOSENING-CHECK 4daa86e4400b: not a loosening
LOOSENING-CHECK 98804b00886a: not a loosening
LOOSENING-CHECK 4a5b8647cab6: not a loosening
LOOSENING-CHECK 61e8188ea1e9: not a loosening
LOOSENING-CHECK f3799c3062d6: not a loosening
LOOSENING-CHECK 084926e46434: not a loosening
LOOSENING-CHECK 1938e73467f3: not a loosening
LOOSENING-CHECK 4622be3b40b8: not a loosening
LOOSENING-CHECK 023b3d0e2c82: not a loosening
LOOSENING-CHECK 68b10485a2de: not a loosening
LOOSENING-CHECK 9f3ae631661f: not a loosening
LOOSENING-CHECK 08f9434c73c6: not a loosening
LOOSENING-CHECK bd78b9dd33e3: not a loosening
LOOSENING-CHECK 8d2660d651d0: not a loosening
LOOSENING-CHECK 6d3627dc24c3: not a loosening
LOOSENING-CHECK 11fcbf1fb18e: not a loosening
LOOSENING-CHECK 1f1bff3ecb85: not a loosening
LOOSENING-CHECK eef5137742b8: not a loosening
LOOSENING-CHECK ff6143ac0ea6: not a loosening
LOOSENING-CHECK 2ec67e35ad65: finding: a backlog epic: naming a proposed: node now passes check-features; master refused it (not a registry row), and the branch's own name_problem refuses that slug for Anchor, ROOTS and DEPENDS
LOOSENING-CHECK 4b3aefc7bdd5: not a loosening
LOOSENING-CHECK 924ecb78d7df: not a loosening
LOOSENING-CHECK 2125da821a62: not a loosening
LOOSENING-CHECK a4ed6ea66535: not a loosening
LOOSENING-CHECK e7667529e10b: not a loosening
LOOSENING-CHECK 3f19ab284962: not a loosening
LOOSENING-CHECK 30ac42cf829d: not a loosening
LOOSENING-CHECK 199affb5f476: not a loosening
LOOSENING-CHECK 53b9c46b58fe: not a loosening
LOOSENING-CHECK 1a7f6d5d9263: not a loosening
LOOSENING-CHECK f33bb38157cf: not a loosening
LOOSENING-CHECK 23a3ffcd765a: not a loosening
LOOSENING-CHECK e70f6b50debf: not a loosening
LOOSENING-CHECK 3d6c9265eb4a: not a loosening
LOOSENING-CHECK 8cb847cd39b8: not a loosening
LOOSENING-CHECK bf3e4c151c11: not a loosening
LOOSENING-CHECK 8868390a9f12: not a loosening
LOOSENING-CHECK 81b38ad60d84: not a loosening
LOOSENING-CHECK 02f32358cc56: not a loosening
LOOSENING-CHECK 64b7ae045d6c: not a loosening
LOOSENING-CHECK d73e7d733a1f: not a loosening
LOOSENING-CHECK 4230a5071232: not a loosening
LOOSENING-CHECK cb8bb9964f53: finding: a pre-cutoff spec or plan whose Anchor header is bare, has no ADR part, or sits on lines 11-18 is no longer armed, so its missing Status goes from rc 1 to rc 0 (reproduced; 0 such documents in the corpus today)
LOOSENING-CHECK 41db02b70dc0: finding: the master anchor reader (18 lines, any **Anchor:** form) is replaced by parse_header (10 lines, full blockquote form), so a document master armed is unarmed and its missing Status passes
LOOSENING-CHECK 281fa3f23926: finding: the anchor value is now parse_header's, which returns None for header forms master read, so the document escapes the armed check
LOOSENING-CHECK 004aa7155968: not a loosening
LOOSENING-CHECK 09f7e8cfc7c9: not a loosening
LOOSENING-CHECK 8e23f719a350: not a loosening
LOOSENING-CHECK 99f12f04ec8d: finding: the backlog page build accepts an epic: naming a proposed: node; master refused it as not a registry row
LOOSENING-CHECK af75797e1e03: not a loosening
LOOSENING-CHECK 0ec9b46ed751: not a loosening
LOOSENING-CHECK 712b76fa3b13: not a loosening
LOOSENING-CHECK 8d3677e94d34: not a loosening
LOOSENING-CHECK 8d9e61b7a135: not a loosening
LOOSENING-CHECK ab380ecc2f26: not a loosening
LOOSENING-CHECK dcdf23f85c2d: not a loosening
LOOSENING-CHECK e9fea33a93fe: not a loosening
LOOSENING-CHECK 4c6d1d19b1c7: not a loosening
LOOSENING-CHECK 025445bdbfb0: not a loosening
LOOSENING-CHECK 58818912fab8: not a loosening
LOOSENING-CHECK 4bc58dfb4b7b: not a loosening
