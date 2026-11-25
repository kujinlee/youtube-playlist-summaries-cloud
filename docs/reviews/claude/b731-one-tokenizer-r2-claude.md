Reviewed head: 8c2e5880059d5f50f6dd1199c551030d2196517d
# Round 2 — b731-one-tokenizer — claude — 2 findings

Scope: the round-1 fixes `80c78c69` (cases) and `dcbc5145` (L, S), plus the `8c2e5880` count bump, judged against
`origin/master` = `e96c4775` (also the merge base). Master's code ran from a detached scratch worktree of
`origin/master` outside the repo, removed afterwards. Every mutation was made in a scratch copy of `scripts/`,
never in the worktree. Harness files: `<scratchpad>/r2/{gen,run,cmp,cmp2,adrfuzz,mut,deepadr}.py`.

Both findings are LOW. Neither is a loosening of today's behaviour that an ordinary (UTF-8) document can reach.

## Self-tests (head `8c2e5880`, exit codes read directly, not through a pipe)

| Script | Result | rc |
|---|---|---|
| check-anchors | 27/27 | 0 |
| check-goal-status | 50/50 | 0 |
| check-features | 101/101 | 0 |
| gen-goals-page | 85/85 | 0 |
| gen-features-page | 54/54 | 0 |

Live: `check-goal-status` rc 0, 13 armed (the same 13 as master); `check-anchors` rc 0.

## (a) Differential sweep: master vs branch, same trees

Two seeds × 3,000 random trees. Each tree has a features tree with settled nodes, a `proposed:` node (`fresh`), a
`was:` alias (`oldname` → `beta`) and both UNARMED slugs. It has 1–3 specs/plans and 0–2 ADRs of 3–30 lines. Each
document holds 0–3 anchor lines drawn from 10 forms (well-formed, bare, quoted, prose `Example:`, no closing
backtick, trailing junk, two claims on one line). The slugs are drawn from 9 values (settled, proposed, exempt,
former, `nonexistent`, uppercase, a slug with a space). A random Status line (valid, ambiguous 🟠, `Approved`, or
none) is added, plus random `## ` headings in ADRs, `Goal:` lines, line separators `\r\n \x0c \r   \x85`, and
a non-UTF-8 spec or ADR in ~3% of trees.

| (master rc, branch rc) | seed 7 | seed 99 |
|---|---|---|
| (0, 0) | 854 | 842 |
| (1, 1) | 1929 | 1947 |
| (0, 1): branch stricter | 29 | 39 |
| (master raised `UnicodeDecodeError`, 1) | 158 | 150 |
| **(master raised `UnicodeDecodeError`, 0)** | **30** | **22** |

- **Master rc 1 → branch rc 0: zero in 6,000.** The 41 ADR cases from round 1 are gone. L removed them.
- All 68 branch-stricter cases come from a non-named claim arming a node: 54 are a missing Status, and 14 are a
  malformed Status (ambiguous 🟠 or `Approved`) under a now-armed claim. That is the P class, declined.
- All 52 "master raised, branch 0" trees contain a non-UTF-8 file (0 without one). See finding 2.

## (b) L reads ADRs exactly as master did

- Function fuzz: 30,000 ADR texts of 1–70 lines, with optional frontmatter, 0–4 anchor lines in 7 forms
  (well-formed, ADR lists, ASCII `-`, unquoted, doubled spaces, trailing `\r`), random or misspelled `## ` headings,
  and odd separators. Master `parse_header(t, adr_head(t))` was compared with the branch's. 9,597 texts had an
  anchor, 3,855 of them past line 18. **0 differ.**
- Tree level: 2,000 random ADR directories. Master `anchored_slugs(d)` restricted to `docs/adr/` was compared with
  the branch `adr_anchors(d)`. **0 differ.**
- An ADR anchored at line 12 (frontmatter and preamble above it) naming `nonexistent` gives rc 1 on master and rc 1
  on the branch.

## (c) S: the `settled_slugs` filter

The filter is right. On master a proposed node could never be armed. Every armed slug was a NAMED slug, and
`misnamed_anchors` → `name_problem` refuses a named proposed slug before arming. The branch keeps that: a primary
claim naming a proposed node is still refused at `check-goal-status.py:358`. A non-named claim naming one is now
dropped at `:365`. A proposed node SHOULD NOT arm the check. It is a name "awaiting the owner's pick" (check-features
`settled_slugs`), and arming it would oblige documents to declare a status under a goal that may never be chosen.
Once it settles it arms through the same filter with no edit, which is the wanted behaviour. A former slug (`was:`)
in a non-named claim is neither current nor settled, so it is dropped. Master never read such a claim either. Not a
loosening.

## (d) `splitlines()` vs `split("\n")`

Correct, with one scoping note.

`splitlines()` breaks at a superset of `"\n"`'s breaks (`\r\n` counts once in both), so its 18-line window is a
prefix of the tokenizer's. Separator substitution cannot create a match. `\s` matches every substituted separator on
both sides, and `[^`]+` matches both `\n` and the original separator. So a slug that crosses a separator is a
non-node on both sides. Only refusals are added.

The scoping note: `splitlines()` is the reader at `f5fa9011` (pre-S2), which the property case copies. It is
**not** `origin/master`'s reader. `origin/master` reads with `split("\n")` (check-anchors `LENIENT_ANCHOR`) and lets
a well-formed header win over an earlier loose claim. So the property case witnesses "pre-S2 refusals ⊆ branch".
No case in the suite witnesses "origin/master refusals ⊆ branch". The sweep above does: 0 in 6,000. Not a finding,
but the property case's name ("master's refusal") should not be quoted as covering `e96c4775`.

## (e) Can the new cases fail? (mutations in a scratch copy)

| Mutation | Result |
|---|---|
| `adrs = {}` | KILLED (both r1 L cases) |
| ADRs feed `claimed` only | KILLED (`r1 L: … FAILS the misnamed-slug check`) |
| ADRs feed `named` only | KILLED (`r1 L: an ADR's header arms its node`) |
| `settled = set(claimed)` | KILLED (r1 S) |
| `settled_slugs` → `current_slugs` | KILLED (r1 S) |
| `settled = set(named)` (master's arming set) | KILLED (#731 two-claim cases + property) |
| ADR window `adr_head(text)` → default 10 lines | **SURVIVED** (finding 1) |
| ADR window → 18 lines | **SURVIVED** (finding 1) |
| ADR read as the first claim of ANY form | **SURVIVED** (finding 1) |
| ADR read as the last claim of ANY form | **SURVIVED** (finding 1) |
| ADR read as the FIRST well-formed claim | **SURVIVED** (finding 1) |
| unreadable ADR `raise` → `continue` | SURVIVED (master crashed there; no behaviour to pin) |

---

## Finding 1 — LOW — the L fix re-implements check-anchors' ADR read, and no case pins its window or grammar

**Where:** `scripts/check-goal-status.py:240-247` (`adr_anchors`); cases at `:597-613`.

**Input:** an ADR whose header sits past line 10, the usual shape here. Live ADRs 0013, 0014 and 0015 carry their
`Anchor:` at lines 11, 11 and 13. Example:
`---\nstatus: accepted\ndate: …\n---\n\n# 9. Deep\n\nDate: x\nDeciders: y\n\nContext line\n> **Anchor:** \`nonexistent\` — **ADR:** none\n\n## Context\n`
(anchor at line 12).

**Observed:** master rc 1, branch rc 1. Today's behaviour is correct. But with
`ca.parse_header(text, ca.adr_head(text))[0]` mutated to `ca.parse_header(text)[0]`, the misnamed-slug refusal is
lost: rc 0, `armed anchors: alpha`. That is the round-1 L loosening again, for every ADR headed past line 10. All
50 cases still pass. Four other grammar mutations (window 18, first or last claim of any form, first well-formed
claim) also survive. Both r1 L cases put the anchor on line 3, inside every window and every grammar.

**Expected:** a regression to the r1 L class goes red by name.

**Why it survives:** `adr_anchors` is a second copy of `check-anchors._documents` + `_header(text, is_adr=True)`
(the glob, the read and the window choice). check-anchors' own suite pins its copy. Nothing pins this one.

**Fix:** call the owner instead of restating it: `anchor = ca._header(text, True)[0]` (or make `_header` public).
Add one case: an ADR with frontmatter whose well-formed `Anchor:` naming `nonexistent` is at line ≥ 12. It must give
rc 1. Add a second, stricter case if wanted: a later well-formed claim must win over an earlier one. That kills the
"first well-formed" survivor.

## Finding 2 — LOW — a non-UTF-8 spec or ADR: master crashed (exit 1), the branch passes (rc 0)

**Where:** `scripts/check-goal-status.py:242` (`read_text(errors="replace")` in `adr_anchors`). On master the
check-goal-status path went through `check-anchors.anchored_slugs` → `_documents` → `f.read_text()` (strict).

**Input:** a tree whose only problem is `docs/adr/0009-bin.md` = `b"# A\n\xff\n## C\n"` (sweep tree `t32`, seed 7).

**Observed:** master raises an uncaught `UnicodeDecodeError` (process exit 1). Branch: `goal status OK`, rc 0. This
happened in 52 of 6,000 sweep trees, every one with a non-UTF-8 file. Branch `check-anchors` still raises the same
`UnicodeDecodeError` on that tree, so the repository's gates as a whole still go red.

**Expected:** a decision rather than an accident. Master's red here was a traceback, not a refusal: master's own
`living_documents` already chose `errors="replace"`. So the branch is arguably MORE faithful to this script's stated
intent. But it is still a master-nonzero → branch-zero input for THIS gate. That is the same shape the coordinator
fixed as L, while the lenient sibling gate catches it.

**Fix:** either (a) record it as accepted in the r2 coordinator note ("non-UTF-8 is read with replacement by design;
check-anchors remains the decode gate"), or (b) make it explicit in `adr_anchors` and `living_documents`: catch
`UnicodeDecodeError` from a strict read and return CANNOT RUN (rc 2). I recommend (a). No live document is affected.

---

Not raised: P (declined; the decline's measurement holds — the branch refuses the pinned P input with rc 1, and
`_master_slug` returns `alpha` for it, as the case asserts). The 108-head count is correct: 4 forms × 3 positions ×
(1 + 4 × 2).

VERDICT: CONVERGED
