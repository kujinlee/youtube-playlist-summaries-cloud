Reviewed head: 3863c11ad9fe1a9993b4f194dafe2f71e6953557

# answer-binds-file — round 1, Claude half (adversarial)

Subject: `git diff origin/master...HEAD` (one commit, `3863c11a`), backlog #544 — a `LOOSENING-CHECK <id>: not a
loosening` answer is bound to its flagged file's entry (mode + blob), not the whole reviewed tree. A deliberate,
owner-approved loosening (2026-11-08, card A). Accepted bound, not a finding: a change to a DIFFERENT file that alters
the flagged line's meaning keeps the answer (explainer §5).

## What I ran

| Check | Result |
|---|---|
| `python3 scripts/check-merge-ready.py --self-test` | 363/363, rc 0 |
| `python3 scripts/check-plan-code.py --self-test` | 418/418, rc 0 |
| Manifest mutation `if moved:` -> `if False:` (scratch clone, harness rule: rc 1 + `parse_fail_names`) | KILLED, rc 1, red = exactly its `expect` ("...but a ONE-BYTE edit to the flagged file voids it") |
| Manifest mutation `flag_binds` drops `via` | KILLED, rc 1, both `flag_binds` pure cases red |
| Hand mutation: `file_matches` ignores the `dirty` overlay | KILLED, rc 1 ("an uncommitted fix the reviewer SAW...") |
| Hand mutation: `gather` emits the symlink record's key as `via_` instead of `via` | **SURVIVES, rc 0, 0 red** — R1-F1 |
| End-to-end probe (scratch repo; `gather` -> `failure_path_flags` -> `flag_binds` -> `review_answers` through `git_reader`) | see below |

End-to-end probe results (each from the same reviewed commit, one verdict answering every flagged id):

| Change after the round | Result | Correct? |
|---|---|---|
| none | both ids cleared | yes |
| gate symlink `scripts/check-l.py -> ../lib/t.py`: TARGET `lib/t.py` edited | symlink's id HELD, note names `lib/t.py` | yes |
| `chmod +x` on the flagged file (same blob) | HELD, note names the file | yes |
| case-only rename `check-k.py` -> `Check-k.py` | new name `a -> b`, new id, HELD | yes |
| flagged file deleted after the round | all its ids bound None -> exact tree -> HELD | yes |
| ...then re-added byte-identical | cleared (same blob, same mode, same id) | yes — the reviewed bytes are back |
| new verdict whose `dirty` names HEAD's blob for the flagged file | cleared by that verdict; the older one's answer still noted as voided | yes (trust in `dirty` is the recorder's, unchanged) |
| `.gitattributes` adding `working-tree-encoding=UTF-16 eol=crlf` for the flagged path | answer KEPT | within the accepted bound — R1-F2 |

Refutation attempts that did NOT find a defect:

- **Answer moving to another line or file.** The id hashes `_name(f)` (both paths for a rename), the occurrence index
  and the text; `flag_binds` keys by the same `_name`. Base-side shifts (master changing the flagged file while the merge
  keeps the branch's bytes) can re-number identical-text removals, but the count of removals only grows, so an
  unanswered id appears and HOLDs; and that case passed the old exact-tree rule identically, so nothing new.
- **Unreachable head / failed `ls-tree`.** The reviewed-head `ls-tree` raises `PathsDisagree` inside the `try` -> note,
  record skipped (real-git case `k-r4-codex`). HEAD's `ls-tree` raises outside it -> `main()`'s `except` -> every line
  HELD. A malformed `dirty` value (a list) raises `AttributeError` in `_entry` -> same `except` -> HELD. Never a pass.
- **Same-half rule per id.** `standing_findings` now requires `i in ok2`; a later same-half round clears a finding only
  for an id whose answer IS bound to this tree. Pinned by the new case and its mutation.
- **Delete-then-re-add laundering.** A deleted file binds None (exact tree). Re-adding it makes it a modify bound to the
  path; the deletion-era reviewed tree has no entry there, so `file_matches` is False (`saw is not None`). It clears only
  when re-added to exactly the bytes AND mode of a tree the reviewer saw (probe row above) — no laundering. Mixed records
  of one name with one deletion bind None in either order (`continue` on a prior None, overwrite otherwise).
- **Rename pairing moved by another file.** `-M` pairing can change when another file is added, but the pair is part of
  `_name`, so the id changes and HOLDs.
- **Flipped cases.** All three now assert the NEW rule positively (rc 0 and no `failure path`), and the doc-merge case
  also asserts the commit is a real merge (3 parent tokens). The old "voids" direction is carried by the new one-byte,
  rename and deleted-file cases. The deleted-file case asserts the `is deleted on the branch` note, so it reads the
  failure-path hold rather than `scope_exits`' (which is rc 3 either way) — correctly reasoned in its comment.

## Findings

### R1-F1 — Medium — A gate symlink's target binding is untested through `gather`; renaming the `via` key survives the suite

`scripts/check-merge-ready.py:1308` (`gather` writes `"via": tgt`) and `:1055` (`flag_binds` reads `f.get("via")`).
The only cases for target binding (`:2203-2222`) hand-build the `fs` dicts with a literal `"via"` key; no real-git case
edits a symlink's target after the round. So the PRODUCER and the CONSUMER of `via` are tested separately and their
join is not — the `unit-coverage-does-not-compose` shape.

Repro (scratch clone, harness rule): replace `"status": "M", "via": tgt,` with `"status": "M", "via_": tgt,` at :1308,
run `--self-test` -> **rc 0, 363/363, `parse_fail_names` = []**. Under that mutant `flag_binds` binds a gate symlink's
flags to the LINK path only, so an edit to the target after the round — exactly what r7's symlink handling exists for —
keeps the answer: a loosening beyond the owner's accepted bound (the target IS the flagged file's code). Today's code is
correct (probe row 2 above); the defect is that nothing would notice it regress. The `.get("via")` in `flag_binds` also
silently tolerates a record without the key, so the regression is quiet.

Fix: add a real-git case in the `#544` block: a gate symlink `scripts/check-l.py -> ../lib/t.py` whose target the
branch rewrites (`return 1` -> `return 2`), answered at that commit (rc 0), then `lib/t.py` edited after the round ->
rc 3 with `answered <id> on a different lib/t.py`. Add the `"via"` -> `"via_"` mutation to the manifest with that case as
its `expect` (pin 163 -> 164).

### R1-F2 — Low — A `.gitattributes` change after the round that re-encodes the flagged file's checkout keeps the answer

`scripts/check-merge-ready.py:1031-1038` (`file_matches` compares the blob only). Repro (probe row 8): after the
answered round, commit `.gitattributes` with `scripts/check-k.py working-tree-encoding=UTF-16 eol=crlf` -> the answer is
kept. The blob is unchanged but the bytes a fresh CI checkout writes for that path are not. This is a DIFFERENT file, so
it is within the letter of the accepted bound, and I could not turn it into a loosening (UTF-16 makes the Python gate
fail to parse, i.e. louder; an existing checkout does not rewrite an unchanged blob; a `filter=` driver needs local
config the repo cannot ship). Recorded because the mandate asked about filters/CRLF on the flagged file and the answer
is: they are not bound. Fix, if wanted: also bind every `.gitattributes` on the flagged path's ancestor directories
(root included) — cheap, no new voids for docs merges. Otherwise, name it in the bound's prose (the comment at
`:934-945` lists what now passes; `.gitattributes` is not in it).

## Notes (not findings)

- The explainer's §6 (main checkout, not in this diff) says "the flagged file renamed or deleted in either tree does
  not count"; the code keeps the exact-tree rule for a DELETED file, so such an answer can count on the exact tree. The
  code and its comments (`:942`) agree with each other; only the explainer's sentence is stale.
- The per-id note for a deleted file repeats once per answered id; cosmetic.
- `--flagged-block` at this head flags 7 lines. Four of them carry the owner-approved loosening itself (the
  `review_answers` signature and docstring, and the old "ANY edit voids" case), so they are answered as `finding:`
  below, truthfully. That is the DELIBERATE loosening of card A, not a defect: it is not an R1-Fn finding and does not
  affect the verdict. The HOLD it leaves is the owner's approved one. The other three are fixture lines whose
  behaviour is kept (the doc edit still happens, now through a real merge; `V` maps the old bool onto the new set
  exactly).

## Loosening answers
LOOSENING-CHECK f420a0304250: finding: an answer from a verdict on a different tree now clears its line when only the flagged file's entry matches (owner-approved, backlog #544 card A)
LOOSENING-CHECK 6f2121cd3021: finding: the docstring's whole-tree rule is replaced by the per-file binding, which keeps answers across edits to other files (owner-approved, backlog #544 card A)
LOOSENING-CHECK 10f587a01725: not a loosening
LOOSENING-CHECK 1d9326b385a7: not a loosening
LOOSENING-CHECK 766bf98f8fce: not a loosening
LOOSENING-CHECK 7895f28f4d34: finding: a doc edit after the round no longer voids the answer; the case now asserts rc 0 (owner-approved, backlog #544 card A)
LOOSENING-CHECK 78c781c7b7fc: finding: the assertion that a later doc edit gives rc 3 and "different tree" is gone, flipped to rc 0 (owner-approved, backlog #544 card A)


VERDICT: CONVERGED
