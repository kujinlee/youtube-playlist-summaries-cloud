Reviewed head: f547bcee524479b9d873e5fc29bd9cb7f535176c

# answer-binds-file — round 2, Claude half (adversarial; Codex half skipped by alternation)

Subject: the r1 fold `f547bcee` (one real-git case, one manifest mutation, pin 163 -> 164, the `.gitattributes`
sentence), then the whole `git diff origin/master...HEAD`. Accepted bound, not a finding: an answer is tied to its
flagged file's blob, and changes to OTHER files keep it (owner, 2026-11-08 11:33 PST, card A).

## What I ran

| Check | Result |
|---|---|
| `python3 scripts/check-merge-ready.py --self-test` | 364/364, rc 0 |
| `python3 scripts/check-plan-code.py --self-test` | 418/418, rc 0 |
| The new manifest entry (`"via": tgt` -> `"via_": tgt`), applied verbatim in a `git archive HEAD` copy. The anchor occurs exactly once | **KILLED**: rc 1, 363/364. `parse_fail_names` = exactly the entry's `expect` ("⭐ #544 r1 Claude F1 real git: ..."), with got `(0, True, 0, False, 0, ...)`, so the answer was kept after the target edit |
| `flag_binds` + `file_matches`, pure, for a gate symlink whose target the branch deletes | see R2-F1 |

## The fold, refuted

- **Does the new case fail without the target binding?** Yes. Under the `via_` mutant, `flag_binds` binds the link
  only. The link's blob, `../tools/t.py`, is unchanged after the round, so the answer is kept and the final `_rc` is 0,
  not 3. The case can tell this apart from other wrong bindings. If the ids fell to None (the exact-tree rule), `_rc`
  would still be 3, but the note would read "reviewed a different tree", not `answered <id> on a different
  tools/t.py`. Its `all(...)` clause requires the latter, and `len(_idsl) > 0` stops it passing vacuously. Moving
  `origin/master` to the commit that adds the link makes the target the only thing the branch changes. So the ids come
  only from the `via` record (`tools/` is not a gate root, and the mutant surviving r1 shows its own record flags
  nothing).
- **Is the mutation sound by the harness's rule?** Yes. The anchor is unique, rc is 1 (not 2), and the only red is
  the named `expect`.
- **Did the fold change binding behaviour or any other case?** No. Outside the self-test body, the code diff of
  `f547bcee` is comment lines and the case-count docstring. The new case comes after the deleted-file case and inside
  the same `try`/`finally`. It restores `origin/master` to `_base8l` before its `check`. It rebinds `_rc0`/`_o0` and
  `_rc`/`_o` only after the previous case has consumed them. All 363 earlier cases still pass.
- **The `.gitattributes` sentence** says a `filter=` line "alters the bytes a fresh checkout writes". That holds only
  where the filter driver is configured locally, which the repository cannot ship (r1 F2 measured this). The sentence
  overstates the effect, but in the safe direction, so this is not a finding.

## Findings

None at Blocking, High or Medium.

### R2-F1 — Low — A gate symlink whose TARGET the branch deletes can never have its answers clear, not even on the exact reviewed tree

`scripts/check-merge-ready.py:1043-1058` (`flag_binds`) and `:1033-1040` (`file_matches`).

`gather` (`:1306-1311`) emits a `via` record whenever the target is in `changed`, and that includes a target the branch
deletes. `flag_binds` sends a file to the exact-tree rule (None) only when the record's own `new` is empty. It never
looks at whether the `via` target exists. So the id binds `(link, target)`, and `file_matches(..., target)` is False
whenever the target is absent from both trees (`saw is None`).

Repro (pure, at this head):
`flag_binds([("i","scripts/check-l.py","x")], [{... "new": "scripts/check-l.py", "via": "tools/t.py"}])` returns
`('scripts/check-l.py', 'tools/t.py')`. Then, with `R` = a tree holding only the link,
`[file_matches(R, {}, R, q) for q in that]` returns `[True, False]`, while `tree_matches(R, {}, R)` is True.

So the answers are voided on the very tree they were given on. Master's exact-tree rule would clear them. This fails
CLOSED: a permanent HOLD that sends the merge to a human. It is not a loosening, and a dangling gate symlink is rare.
It does contradict the design's own sentence, "a file the branch DELETES has no blob to bind to; its answers keep the
EXACT-tree rule".

Fix: in `flag_binds`, bind None when the `via` target is absent from the merging tree (pass `new_t`, or have `gather`
omit `via` and emit `"via": None` plus a deleted marker). Alternatively, state the bound in the `flag_binds`
docstring. Add a pure case either way.

## Notes (not findings)

- The flagged-line locations (`:1060`, `:1061`, `:2128`, `:3301-3305`) are BASE-file line numbers (`flagged_block`
  names the base side, r1 m5). They are the same 7 ids that r1 answered, and nothing in the fold touches them.
- Four of the seven flagged lines carry the owner-approved loosening itself, so they are answered `finding:` below.
  That is card A's deliberate change, not an R2 finding, and it does not affect the verdict. The coordinator verifies
  them at merge time against the 2026-11-08 11:33 PST approval.

## Loosening answers
LOOSENING-CHECK f420a0304250: finding: an answer from a verdict on a different tree now clears its line when only the flagged file's entry matches (owner-approved, backlog #544 card A)
LOOSENING-CHECK 6f2121cd3021: finding: the docstring's whole-tree rule is replaced by the per-file binding, which keeps answers across edits to other files (owner-approved, backlog #544 card A)
LOOSENING-CHECK 10f587a01725: not a loosening
LOOSENING-CHECK 1d9326b385a7: not a loosening
LOOSENING-CHECK 766bf98f8fce: not a loosening
LOOSENING-CHECK 7895f28f4d34: finding: a doc edit after the round no longer voids the answer; the case now asserts rc 0 (owner-approved, backlog #544 card A)
LOOSENING-CHECK 78c781c7b7fc: finding: the assertion that a later doc edit gives rc 3 and "different tree" is gone, flipped to rc 0 (owner-approved, backlog #544 card A)

VERDICT: CONVERGED
