Reviewed head: 11f02283baeb290f707a3277798b74bc07bb5e51
# Round 1 — b731-one-tokenizer — claude — 2 findings

Scope: `git diff origin/master...HEAD` (origin/master = `e96c4775`). Master's code was run from a detached
scratch worktree of `origin/master`, created outside the repo and removed afterwards. Every mutation was made in
a scratch COPY of `scripts/`, never in this worktree.

## What was run, and what it showed

| Check | Result |
|---|---|
| `check-anchors.py --self-test` | 27/27 |
| `check-goal-status.py --self-test` | 45/45 |
| `check-features.py --self-test` | 101/101 |
| `gen-goals-page.py --self-test` | 85/85 |
| `gen-features-page.py --self-test` | 54/54 |
| `check-goal-status.py` on the live tree, master vs branch | both rc 0, byte-identical output (66 of 207 declare a state, the same 13 armed anchors) |
| `check-anchors.py` on the live tree, master vs branch | both rc 0, identical summary line; `audit` 0 findings on both |
| Live corpus: specs/plans with 2+ distinct claims, or a named slug that is not the first claim | 0 |
| `parse_header` master vs branch, 8,784 documents (fuzz trees + every `docs/**/*.md`) × head_lines 10/18/40/2000 | 35,136 comparisons, 0 differences |
| Differential fuzz of `check-goal-status.main`, 1,500 random trees (1–3 specs/plans, 0–3 claims in 8 forms at lines 1–22 naming armed / exempt / typo / proposed / wrong-case slugs, a random Status, an ADR 40% of the time) | rc agrees on 1,435. **Master 1 / branch 0: 41**, every one an ADR whose slug is misnamed (see (c)). Master 0 / branch 1: 24, all "any claim enforces" refusals |
| (c) Those 41 trees under the branch's `check-anchors.audit` | 41 of 41 refused by G1 (`docs/adr/0001-x.md claims anchor ...`). `check-anchors` runs in CI (`ci.yml:541`) |
| `check-plan-code.py --mutate . --only` each script, in a `git archive` copy | check-goal-status 13/13 killed, check-anchors 13/13 killed, each attributed to its named case |
| `check-fixture-variation.py` on the two scripts | OK |

**(a) A loosening: none found beyond the stated ADR narrowing.** The only inputs master refuses and the branch
passes are an ADR whose `Anchor:` names a non-node or a proposed node. `check-anchors`' G1 refuses every one
of them on both sides (it reads ADRs "any date, ADRs too", `check-anchors.py:251`). The other half of the
narrowing, ADR slugs no longer feeding the armed set, has no effect on enforcement. To be enforced on master a
spec must name slug X itself, and on the branch that same claim puts X in `claimed`. X is current, because the
misnamed check passed. Tree A3 confirms it: when a slug is named only by an ADR plus a bare spec claim, both
sides give rc 1.

**(b) A correct document refused: yes.** See F1.

**Step 3, the property case's copy.** `_MASTER_CLAIM` and `_MASTER_HEAD` are literals, and they match
`git show f5fa9011:scripts/check-goal-status.py:120-121`. Nothing is imported from the code under test. The
identity case can go red:
- copy window 18→17: `[FAIL] #731 identity`, 44/45;
- copy pattern `\s*` → a single space: `[FAIL] #731 identity`, 44/45;
- tokenizer `CLAIM_HEAD_LINES` 18→10 in `check-anchors`: identity, property and `living_documents reads every
  claim` all red, 42/45.

(Note for anyone repeating this: a same-size edit to `check-anchors.py` within one second can be masked by a
stale `__pycache__`. I re-ran with `PYTHONDONTWRITEBYTECODE=1` and a cleared cache. The first run was an
artefact.)

**Step 4, the enforcement line** (`check-goal-status.py:260`, `armed_by = next((c for c in d["claims"] if c in armed), None)`):

| Mutant | Red cases |
|---|---|
| `d["claims"][:1]` (first claim only) | `#731: exempt well-formed claim FIRST...` (44/45) |
| `d["claims"][-1:]` (last claim only) | `#731: armed claim FIRST...`, `#731 property` (43/45) |
| `(d["anchor"],)` (the named claim only) | both `#731` order cases and the property case (42/45) |
| armed set from `named` instead of `claimed` | both `#731` order cases and the property case (42/45) |

All of them are killed. Two mutants survived; neither is a loosening:
- `unarmed_blank` reverted to `d["anchor"] not in armed` gives 45/45. It is an EQUIVALENT mutant. The count is
  reached only when nothing was missing. At that point no state-less document has an armed claim, so both
  expressions are true for every document that reaches it. No finding.
- Dropping the `if slug in current` filter on the armed set gives 45/45. It is a real survivor, folded into F2.

---

## F1 — MEDIUM — a quoted Anchor line in the prose ARMS its slug and refuses a correct document. The redesign was measured as causing no such refusal

**File:** `scripts/check-goal-status.py:260` (the `armed_by` line) and `:327-338` (the `claimed` map that builds
the armed set). The tokenizer is `scripts/check-anchors.py:anchor_claims`.

**Input P1.** Two specs. `a.md` is about the anchor scheme itself. Its real header is well formed and names the
exempt node, its prose quotes an example header, and it has no Status:
```
# Anchor scheme

> **Anchor:** `dev-speed` — **ADR:** none

A header looks like ``> **Anchor:** `alpha` — **ADR:** none``.
```
`b.md` is `> **Anchor:** \`alpha\` — **ADR:** none` plus `**Status:** ✅ shipped`.

**Observed:** branch rc 1: `✗ docs/superpowers/specs/2026-09-01-a.md: no **Status:** line ... and \`alpha\` is armed`.
**Master:** rc 0. Master's first match is `dev-speed`, which is exempt.

**Input P2.** The prose mention arms a node that no header names. `a.md` is a well-formed `alpha` header with a
Status, plus a prose line ``**Anchor:** `beta` ``. `b.md` is a well-formed `dev-speed` header, a prose line
``see **Anchor:** `beta` ``, and no Status.
**Observed:** branch rc 1, `\`beta\` is armed`, and the armed set now includes `beta`. No document anchors to
`beta`. **Master:** rc 0, armed `alpha`.

**Input P3.** As P1, but the prose names a PROPOSED node. Branch rc 1, `\`prop\` is armed`. Master rc 0. See F2.

**Expected:** rc 0. The architecture review this PR implements
(`architecture-review-2026-11-25-node-tree-s2-living-documents.md` §3, the table) records **"New refusal of a
correct document: none"** for this exact rule. Its only probe put a NON-node slug in the prose, and that is
filtered out by `slug in current`. With a current node in the prose, the rule refuses. The backlog #731 row warns
that a refusal of "a correct document whose prose mentions the header syntax" is "the next fix-induced finding".
This rule produces that refusal for a prose mention BELOW the header as well as above it.

**Why MEDIUM, not HIGH:** it fails safe (a refusal, never a pass), the live exposure is 0 of 207, and the
remedy for an author is one Status line. It is still a measured claim in the design's evidence that is false,
and documents ABOUT the anchor scheme (a spec or plan for check-anchors itself) are where this input occurs
naturally.

**Fix, one of:**
1. **(Code; contains master by construction, with no precedence.)** Enforce when the FIRST claim (master's
   reader, exactly) OR any WELL-FORMED claim names an armed slug, and build the armed set from the same claims.
   This is a union of two named readers, not a precedence. Master's first match is still always included, so the
   property case still holds. P1, P2 and P3 return rc 0, because their prose claims are neither first nor
   well formed. Add P1 as an adjacent negative next to the two `#731` order cases.
2. **(Decision.)** Keep "any claim" and write the choice down: correct the architecture review's table row, and
   pin P1 in a case named as an INTENDED refusal. Then the next round cannot "find" it again.

Either way, a case with a CURRENT armed node in prose has to exist. Without one, this behaviour is unmeasured
in both directions.

## F2 — LOW — the armed set admits PROPOSED nodes, and the `slug in current` filter is unguarded

**File:** `scripts/check-goal-status.py:337-338`:
`current = ca.check_features.current_slugs(nodes)` and
`armed_set = armed({slug: rels for slug, rels in claimed.items() if slug in current})`.

`check_features.current_slugs` includes `proposed:` nodes (`check-features.py:254`). `settled_slugs` (`:258`)
is the set that `name_problem` accepts.

**Input:** P3 above. Tree t218 of the fuzz shows the same thing: one plan has a loose `> **Anchor:** \`prop\``
(where `prop` is a `proposed: 2026-11-01 10:00` node) and a well-formed `dev-speed` header, with no Status.

**Observed:** rc 1, `\`prop\` is armed`, and `armed anchors:` lists `prop`. The message tells the author to add a
Status. If `prop` were the named anchor, `misnamed_anchors` would instead say "`prop` is a proposed name
awaiting the owner's pick — it cannot anchor a document". So a proposed name can be ARMED by a claim that is
not allowed to ANCHOR.

**Expected:** a proposed node is never armed. On master it never was, because `misnamed_anchors` refused every
slug in the armed set first.

**Second half:** removing the `if slug in current` clause altogether leaves `--self-test` at 45/45. No case
puts a non-current or proposed slug in a non-named claim, so the clause that keeps prose from arming typos is
unguarded. There is no mutation entry for it either (13/13 killed, none targets it).

**Fix:** filter with `ca.check_features.settled_slugs(nodes)`. Add one case: a document whose named header is
exempt and which carries a second claim naming a typo and a proposed node, with no Status. It must give rc 0 and
an `armed anchors:` line without either slug. That case kills the dropped-filter mutant and the
`current`→everything mutant. If F1 fix 1 is taken, the case still applies to well-formed second claims.

---

## Notes (no finding)

- `_master_slug` splits with `splitlines()`. The tokenizer splits with `split("\n")`. They disagree on `\r`,
  `\x0b`, `\x0c`, `\x1c-\x1e`, `\x85`, ` ` and ` `. The tokenizer's 18 lines always cover a superset
  of master's 18, so it is stricter and never looser. The grid contains none of these characters, and the
  identity case compares only pattern and window, not the splitter. The architecture review already lists the
  form-feed case as a known stricter direction.
- An unclosed backtick before a real claim swallows it on BOTH sides (`[^\`]+` spans newlines). The slug becomes
  something like `foo\n**Anchor:** `, and both sides report it as misnamed. Master and the branch agree.
- `anchor_claims(head_lines > 18)` (the ADR path) gives well-formed claims past 18 but loose claims only to 18.
  That is consistent with its docstring, and `parse_header` reads only well-formed claims.

VERDICT: NOT CONVERGED
