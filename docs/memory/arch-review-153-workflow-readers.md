---
name: arch-review-153-workflow-readers
description: "FIRES-WHEN: citing architecture review #153 / PR #329, or starting backlog #155 (extract _structural()) — PR #329 MERGED (5ffe6017). Verdict: extract _structural() into scripts/workflow_structure.py, NOT a real YAML parse; #155 still OPEN and sized by attempting it"
metadata: 
  node_type: memory
  type: project
  originSessionId: 0cfd7079-9c4f-4f89-9a59-337f426f6311
  modified: 2026-09-22T01:00:41.419Z
---

**CURRENT STATE (verified 2026-11-14):** PR #329 MERGED as `5ffe6017`. #154 (the live false green it
found) ✅ closed by PR #331. **#155, the extraction, is still OPEN 🟡** — `scripts/workflow_structure.py`
does not exist yet. #156 🟡, #161 🟡, #162 🟢, #163 🟢 open; #160 ✅.
Artifact: `docs/reviews/architecture-review-2026-09-21-workflow-readers.md`.

## The verdict, so it is not re-derived
**Extract `_structural()` into `scripts/workflow_structure.py`** (underscored = importable library;
`page_markup.py` is the precedent, and `coverage_verdict.py` is a worked precedent for the same extraction
**including moving its mutations**). **NOT a real parse** — no guard imports a third-party package, PyYAML
is absent, no `requirements.txt`, so a parser dependency lands inside the interpreter `check-python-pin.py`
exists to pin. Local helper imports ARE house style.

**#155 sizing — decided with the user 2026-09-21: size it by ATTEMPTING it, not by more review rounds.**
Three rounds each found another unbudgeted consumer: the consumer has no test seam (the mask lives in
`main()`, which `--self-test` returns before reaching — extract the blob construction to a pure function
first); `check-fixture-variation.py` skips `_`-prefixed names, so keeping underscore names pins an EMPTY key
set; `check-ratchet-contract` owes its own bookkeeping. The consumer set is `check-plan-code`,
`check-selftest-counts`, `check-ratchet-contract`, `check-fixture-variation` (r4 swept for a fifth: none).
Mutation transfer by ANCHOR LINE, not index: `:232 :244 :245 :249 :254 :260 :263 :264 :278 :295 :298 :349`
= 12; `EXPECTED_MUTATIONS` 39 → 27 + a new key of 12 — a transfer, not a ratchet fall; the 12 killing
cases move too and the declared count 84 falls (pinned in `check-selftest-counts.POPULATION`).
⚠ **These line numbers are from 2026-09-21; #154 has since landed — re-derive all four before acting.**

## What the review found
1. #153's scope was wrong both ways: `check-ci-watched.py` opens no workflow; `check-ratchet-contract.py:835`
   is the only member that fails OPEN.
2. R3's fail-open: a YAML comment describing a removed step, block-scalar text, and `if: false` all satisfy
   "something executes this guard". 59% of `ci.yml` is text it reads as executable. Latent — 0 of 40 guards
   depend on it.
3. A live false green (→ #154): `_BLOCK_SCALAR` could not span the space in `- run:`; `pin_took_effect`
   speaks for one job while `declared_pins` speaks for all, so job B with no `setup-python` read as pinned.
`CONTEXT.md` gained **structural line** and **soundness check**.

## Process facts
- `check-review-rounds.py` wants both halves per round; an alternating round needs a `REVIEW GAP:` line
  stating alternation (precedent `plan-m4-promote-schema-r3-claude.md:3`).
- ⚠ Not filed as of 2026-09-21: `check-docs.py` counts a backlog row's columns but cannot tell content is in
  the RIGHT column — an edit anchored on a cell-closing pipe landed #155 one column early, gate green.
- The rounds' own lesson: [[an-inference-stated-as-measured]].
