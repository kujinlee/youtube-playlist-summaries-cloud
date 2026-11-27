# Round 1 — `node-tree-s3` — coordinator — NOT CONVERGED (Codex), CONVERGED (Claude); one fold

Both halves reviewed `git diff e316f96e bff26dbd`, the seven S3 commits (plan Tasks 12–16).

Neither half found a BLOCKER or MAJOR. Codex checked all 31 new mutations, and the Claude half checked 38 new or changed ones, each on a copy: every one killed the case it names. The pins equal their manifest lengths.

Findings:
- **C1 (Low; Codex MINOR).** `goal-tree.py` numbers requestless goals in `goal-threads.md` heading order instead of tree order. **Fixed** with a reverse-order heading case and a mutation.
- **C2 = F2 (Low; Codex MINOR + Claude MINOR).** `--snapshot` fingerprints the raw previous snapshot before resolving former slugs, so a rename alone appends a record. **Fixed:** both snapshots are resolved before they are compared. The plan's "resolve-before-diff" mutation now names the case it reddens.
- **F1 (Low; Claude MINOR).** `check-features.py` refuses a preamble prose line that begins with "PRIORITY". **Fixed.**
- **F3 (Low; Claude MINOR).** Two new goal-tree branches had no mutation: the `parse_threads` heading check, and `read_tree`'s "no node" CANNOT RUN. **Fixed:** mutations were added, each naming its case.
- **F4 (Low; Claude NIT).** A repeated slug was accepted in `also`, `--also` and PRIORITY. **Fixed.**
- **F5 (Low; Claude NIT).** Session-state's EXIT CODES docstring lacked rc 1. **Fixed.**
- **F6 (Low; Claude NIT).** `_check_features()` re-executes the module once per slug. **Declined:** it costs time only, and correctness is unaffected.
- **F7 (Low; Claude NIT).** `resolve_ledger` does not resolve an entry's `also`. **Filed** as backlog #743, which is S4 scope.

**Loosening answers (Codex):**
- `2b4665a6f4f6` is the shipping-set edge pin. It goes from 361 to 363 by design, for S3's two new tree loads.
- `5302c305c129`, `c096c086d34b` and `fcdfb41bb03e` stop requiring a goal heading to quote a request. The approved plan requires that change: a goal is a tree node, and its request is optional.
- The other six checked hashes are "not a loosening".

```yaml
round: 1
fixes_nontrivial: true
subject: node-tree-s3
halves:
  codex: ran
  claude: ran
findings:
  - {id: C1, severity: Low, aim: deliverable, fix_induced: false, component: goal-tree, disposition: fixed}
  - {id: C2, severity: Low, aim: deliverable, fix_induced: false, component: goal-tree, disposition: fixed}
  - {id: F1, severity: Low, aim: deliverable, fix_induced: false, component: check-features, disposition: fixed}
  - {id: F3, severity: Low, aim: deliverable, fix_induced: false, component: goal-tree, disposition: fixed}
  - {id: F4, severity: Low, aim: deliverable, fix_induced: false, component: session-state, disposition: fixed}
  - {id: F5, severity: Low, aim: deliverable, fix_induced: false, component: session-state, disposition: fixed}
  - {id: F6, severity: Low, aim: deliverable, fix_induced: false, component: session-state, disposition: declined}
  - {id: F7, severity: Low, aim: deliverable, fix_induced: false, component: goal-tree, disposition: filed}
```

Reviews: `docs/reviews/codex/node-tree-s3-r1-codex.md`, `docs/reviews/claude/node-tree-s3-r1-claude.md`.
