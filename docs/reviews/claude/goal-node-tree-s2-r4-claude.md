Reviewed head: 1b8d75d515386a0609f91860e0c5c408aa8fab01

# PR #637 (goal-node-tree-s2) — round 4 (the round cap), Claude half: the fold, and the loosening answers

Scope: the r3 fold `bdaeff75` (`git diff 465de1ce bdaeff75`), which fixes r3 F1 and F3, plus the same 72
flagged ids, regenerated on this head. The brief was to REFUTE the fold. Under the round cap
(`docs/review-method.md` §0 Q4c), a new finding is FILED unless it is a BLOCKER. I report one, Low.

## The fold

### F1 (check-goal-status arming): resolved, with one narrow residual (R4-F1 below)

The fold adds a `lenient` keyword to `check-anchors.parse_header`. When the strict reader finds no
anchor, the lenient one applies master's arming regex (`\*\*Anchor:\*\*\s*`([^`]+)``) to the first 18
lines. `check-goal-status.living_documents` calls it with `lenient=True`, and
`with_document_anchors` adds any document whose anchor only the lenient reader finds to the
`anchored` map before `armed()` and `misnamed_anchors` read it. The default stays strict. Every
caller in `check-anchors` itself passes no `lenient`, so the header gate's strictness is unchanged.

What I tried:
- **The corpus.** I ran master's reader (`ANCHOR_LINE` over `splitlines()[:18]`, quoted from
  `git show origin/master:scripts/check-goal-status.py:120-121`) and the branch's
  `parse_header(text, lenient=True)` over all 207 specs and plans. They disagree on **0**.
- **The window.** The branch splits on `"\n"` and master used `splitlines()`. `splitlines` also
  splits on `\r`, `\v`, `\f`, `\x1c`-`\x1e`, `\x85` and ` `/` `. So the branch's 18 lines always
  hold at least as much text as master's. The branch can find more, never less. CRLF reads the same
  (`x` on both sides, run).
- **The r3 input.** It is now a self-test case (`⛔ F1: a pre-cutoff spec with a bare, short Anchor
  header and no Status is ARMED and FAILS`), and it is rc 1 as on master.
- **A lenient anchor that is not a node** (for example prose like ``**Anchor:** `foo` `` in the first
  18 lines) now FAILS through `misnamed_anchors`. On master it was silently unarmed. That is stricter,
  not looser, and no such document exists today (the live run is rc 0).
- **The precedence.** This is where the fold differs from master, and it is R4-F1.

Mutations: `check-plan-code.py --mutate . --only scripts/check-anchors.py` gives 13/13 killed, all
attributed. `--only scripts/check-goal-status.py` gives 13/13 killed, all attributed. Both new
check-goal-status mutations (the strict reader restored, and `with_document_anchors` dropped) are
killed by the F1 case.

### F3 (`epic:` naming a `proposed:` node): resolved

`check-features.settled_slugs` is `{n.slug for n in nodes if not n.proposed}`. It feeds both
`epic:` consumers: `check-features.main` → `kind_problems`, and `gen-backlog-page.node_slugs` →
`parent_errors` (the page build at `gen-backlog-page.py:4447` and the live self-test at `:4115`). It
is the same set that `check-anchors.name_problem` accepts. I searched every caller of
`current_slugs`, `node_slugs` and `settled_slugs` in `scripts/*.py`. The remaining `current_slugs`
users are `check-anchors.name_problem` (which refuses a proposed slug itself, on the next branch),
`check-goal-status.stale_exemptions` (it asks whether an exemption's node still exists, and a
proposed node does), and `gen-goals-page.collect` (an Anchor-header path, gated by check-anchors G1).
None of them is an `epic:` check. `gen-features-page` does not read `epic:` links. The spec's S2 row
says the epic check "takes the tree's CURRENT slugs". The settled subset is stricter than that and
agrees with §2.7. Live: `parent_errors(real, node_slugs()) == []` holds (gen-backlog-page self-test
253/253), so no live row names a proposed node. Mutations: `--only scripts/check-features.py` gives
60/60 killed, all attributed, including the new `settled_slugs` one. The gen-backlog-page sweep (85
mutations) was **NOT RUN** here, because it does not fit one call's time bound. CI's PR sweep selects it.

### F2: withdrawn, because the approved spec decides it

The spec `docs/superpowers/specs/2026-11-23-goal-node-tree-design.md:501` (the S2 row) says
`check-anchors.py` "drops the claimed-by-a-document rule". ADR-0016 § Consequences records the drop:
"ADR-0010's rule 'a registry entry no document claims fails' is dropped". The loosening is therefore
the goal as approved, not a defect of the slice. I answer its two ids `not a loosening` on that
ground, per the brief. The coordinator's r3 account declines it on the same evidence.

## Findings

### R4-F1 — Low (FILED, round cap; not a BLOCKER) — the lenient reader falls back, it does not take precedence
Id `41db02b70dc0`.

Master took the FIRST `**Anchor:** `x`` in 18 lines. The branch takes the strict match whenever one
exists in the first 10 lines, and uses the lenient search only when there is none. A document with a
bare Anchor line followed by a well-formed one naming a different slug is armed by different slugs on
the two sides. I ran this input: a tree holding `cloud-sync` plus the two UNARMED nodes
(`dev-speed`, `harness-ships-elsewhere`), and
`docs/superpowers/specs/2026-01-01-two.md` =
`# Two\n\n**Anchor:** `cloud-sync`\n\n> **Anchor:** `dev-speed` — **ADR:** none\n\nno status\n`.
- master: `cloud-sync` is first and in `ARMED_ANCHORS`, so the missing Status is **rc 1**.
- branch `check-goal-status.main`: **rc 0**, "armed anchors: " (empty), with one UNARMED warning.

The corpus holds 0 documents with two `**Anchor:**` lines in their first 18 (counted over every spec
and plan). This is latent and needs a self-contradictory header. Fix (one line): in lenient mode,
let the `LENIENT_ANCHOR` search decide whenever it matches, which is exactly master's rule. The strict
result is then only the default mode's answer. Alternatively, `check-anchors` could refuse a header
with two Anchor lines in any mode.

## Self-tests (run at the reviewed head)

| Script | Result |
|---|---|
| `check-anchors.py --self-test` | 24/24, rc 0 |
| `check-goal-status.py --self-test` | 41/41, rc 0 |
| `check-features.py --self-test` | 101/101, rc 0 |
| `gen-backlog-page.py --self-test` | 253/253, rc 0 |

Live runs: `check-anchors` rc 0 (73 headers name 15 nodes, 6 ADR headers). `check-goal-status` rc 0,
with the same 13 armed slugs as master. `check-features` rc 0 (37 nodes, 29 areas).

## Loosening answers
LOOSENING-CHECK ae760b4ab0f9: not a loosening
LOOSENING-CHECK bb1a8c666480: not a loosening
LOOSENING-CHECK f1c9aace0e5c: not a loosening
LOOSENING-CHECK 638463189ba3: not a loosening
LOOSENING-CHECK 3a3a2417a186: not a loosening
LOOSENING-CHECK 2f93ab5c0a6a: not a loosening
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
LOOSENING-CHECK 2ec67e35ad65: not a loosening
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
LOOSENING-CHECK cb8bb9964f53: not a loosening
LOOSENING-CHECK 41db02b70dc0: finding: a pre-cutoff document with two Anchor lines in its first 18 (a bare one first, a well-formed one after) is armed on master by the FIRST and on the branch by the well-formed one, so when that one is UNARMED its missing Status goes from rc 1 to rc 0 (reproduced; 0 such documents in the corpus today)
LOOSENING-CHECK 281fa3f23926: not a loosening
LOOSENING-CHECK 004aa7155968: not a loosening
LOOSENING-CHECK 09f7e8cfc7c9: not a loosening
LOOSENING-CHECK 8e23f719a350: not a loosening
LOOSENING-CHECK 99f12f04ec8d: not a loosening
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

VERDICT: CONVERGED
