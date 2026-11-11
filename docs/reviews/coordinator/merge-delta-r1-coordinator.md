# Round 1 — `merge-delta` (PR #491, backlog #426) — coordinator — NOT CONVERGED (both halves); one High, three Mediums and two Lows FIXED

Codex half: `docs/reviews/codex/merge-delta-r1-codex.md`. Claude half: `docs/reviews/claude/merge-delta-r1-claude.md`. Both reviewed `f84fce2b`.

```yaml
round: 1
fixes_nontrivial: true
subject: merge-delta
halves:
  codex: ran
  claude: ran
findings:
  - {id: X-H1, severity: High, aim: deliverable, fix_induced: false, component: final-entries, disposition: fixed}
  - {id: X-M2, severity: Medium, aim: deliverable, fix_induced: false, component: master-side, disposition: fixed}
  - {id: C-M1, severity: Medium, aim: deliverable, fix_induced: false, component: master-side, disposition: fixed}
  - {id: C-M2, severity: Medium, aim: deliverable, fix_induced: false, component: main-onto, disposition: fixed}
  - {id: C-L1, severity: Low, aim: deliverable, fix_induced: false, component: master-side, disposition: fixed}
  - {id: C-L2, severity: Low, aim: deliverable, fix_induced: false, component: self-test, disposition: fixed}
```

**Both halves NOT CONVERGED.** Both ran the self-test (217/217). Codex ran the scoped mutation sweep (77/77 killed
and attributed). The Claude half's sweep was NOT RUN (no `node_modules` in its tree), and it built fixtures S1-S15 over
real repositories.

**X-H1 — FIXED.** `_final_entries` turned a failed HEAD `ls-tree` into `{}`, i.e. "every path absent". Since #426 an
absent path equals a deletion master made, so a branch's unreviewed re-add of a file master deleted was cleared. It
now raises `CANNOT RUN` (rc 2 from `main`). It also takes an injectable `git`, and the real-git fixture now calls it
instead of a copy. Cases: *a re-add of a file master deleted is charged* (control) and *a failed HEAD `ls-tree` is
CANNOT RUN, never 'all absent'*, the failure injected into that one call over a real repository. Two mutations name
the second case: `return {}` restored, and the check deleted.

**X-M2 = C-L1 (one defect) — FIXED.** The merged-tree `ls-tree` failure branch in `_master_side` had no case. Case:
*a failed `ls-tree` of the merged tree is None*. Two mutations name it: `return {}, frozenset()` and `if False:`.

**C-M1 — FIXED.** `merge-tree` applied merge drivers from attributes the branch controls. `merge_tree_argv` (pure)
now runs it with `--attr-source=<empty tree>`, `-c core.attributesFile=/dev/null` and `-c merge.default=text`.
Measured on git 2.49: `--attr-source` does NOT cover `$GIT_DIR/info/attributes`, so `_master_side` returns `None`
(the strict rule) while that file declares anything. A failed lookup of the empty tree or of the info path is `None`
too. git older than 2.42 rejects `--attr-source` with rc 129, which `parse_merge_tree` already reads as `None`.
An empty or failed `hash-object` answer is also refused explicitly. That check is a second lock: git 2.49 itself
rejects an empty `--attr-source=` (rc 128) once a content merge reads attributes. Its two mutations SURVIVED the
sweep for that reason, so they were dropped and the check carries a comment saying so. Real-git cases, one per source: a committed `docs/.gitattributes` (the reviewer's S15),
a worktree `.gitattributes`, `core.attributesFile`, a repository `merge.default`, and `info/attributes` (direct and
through the gatherer). Each is preceded by a control: the same union content typed by hand, with no attributes, is
charged. Pure cases cover `attributes_in_force` and the exact argv. There are six mutations: each of the three flags
dropped, the info check deleted, a comment line counted as an attribute, no file read as in force, and an
unresolvable info path.

**C-M2 — FIXED.** `main` computed `onto` itself, and the fixture had its own copy. Both now call `merge_onto(base,
git=)`. Mutations: `merge-base` → `rev-parse HEAD` is killed by *PR #487's shape: the genuine change is charged*, and
the rc check removed is killed by *an unresolvable base has no `onto`*. Bound: `main`'s argument `args.base` is still
reached by no case (`check-main-drivable.py` passes with the file in its pinned population, unchanged).

**C-L2 — FIXED.** The real-git trap-1 case was charged by content, not by the conflict exclusion. The reviewer
suggested M1's fixture as the closer, but after the M1 fix that fixture conflicts and its blob holds markers, so it is
charged by content too. The new case *HEAD EQUAL to a conflicted merge is still charged* commits the synthesised
conflicted blob itself, so HEAD's entry equals the master side's and only `p in conflicted` charges it. Measured: the
existing manifest mutant *a CONFLICTED path is explained like a clean one* reds it as well as its named pure case.

The Claude half's refuted hypotheses (S1-S14, shallow) and its stacked-PR note state no further finding.

Self-test 217 → 237 cases. Mutation manifest 77 → 90 entries (`EXPECTED_MUTATIONS` updated).
