# Round 2 — `held-pins-head` (PR #541, backlog #538) — coordinator — NOT CONVERGED; the fold removes the class (out-of-process read)

REVIEW GAP: claude — alternation

```yaml
round: 2
fixes_nontrivial: true
subject: held-pins-head
halves:
  codex: ran
  claude: gap
findings:
  - {id: X-F1, severity: High, aim: deliverable, fix_induced: true, component: isolation, disposition: fixed}
  - {id: X-F2, severity: Medium, aim: deliverable, fix_induced: true, component: isolation, disposition: fixed}
  - {id: X-F3, severity: Low, aim: deliverable, fix_induced: true, component: isolation, disposition: fixed}
```

Codex (`docs/reviews/codex/held-pins-head-r2-codex.md`) reviewed `8775b82d`, the merge of master (PR #543) into the
branch. It found the merge kept both sides, and it answered 13 of the 14 flagged ids `not a loosening`.

**All three findings come from ONE design: importing HEAD's harness INSIDE the gate's own process and isolating that
import by hand.**
- **X-F1 (High).** A committed unchecked-hash `__pycache__/*.pyc` replaces the blob-verified `.py`. This was measured
  as a pin fall that read READY. Master refused it, which is why id `c47564441466` was answered `finding:`.
- **X-F2 (Medium).** `_lib_roots` trusts everything under the interpreter prefixes, so a project inside a virtual
  environment leaks working-tree modules through the isolation.
- **X-F3 (Low).** The first call's lazy imports escape the snapshot.

Round 1 had already found two leaks of the same kind (X-F2 and C-F2: fileless modules, an untested restore). Each fold
can close the route the last round used, and an in-process import offers another one: `sys.modules`, `sys.path`,
path hooks, bytecode, `.pth` files. **Can a redesign remove the class? Yes.** Read HEAD's pins and displays in a
CHILD process that shares no module state with the gate:

- Materialise ONLY regular `*.py` files from HEAD's `scripts/`, from raw blobs as now. Refuse (CANNOT RUN) any
  `__pycache__/`, `*.pyc` or other bytecode in that subtree, rather than skipping it silently.
- Run `python3 -I -B -S` (isolated mode, no bytecode writing, no `site`) with the temp dir as cwd, and
  `PYTHONDONTWRITEBYTECODE` set. A tiny driver passed with `-c` puts ONLY the materialised `scripts/` dir in front of
  the stdlib on `sys.path`, imports `check-plan-code` from it, and prints JSON: `held`, the base display and the HEAD
  display (pass the two pins-file texts in on stdin).
- Any non-zero exit, a timeout, or JSON that does not parse or does not match the schema is CANNOT RUN, never READY.
- DELETE `_isolated_import`, `_lib_roots` and the compile memo, and the cases and mutations that pin them. The
  mechanism they guard no longer exists. Their subjects (a dirty working tree, a stale module, a hidden module, a
  restore) become cases against the child read.
- The pin falls by the retired count: state each one, with the reason, in `expected_mutations.py`.
- Keep the self-test cost in check. One child per `pin_pair` adds about 0.15 s; measure the suite before and after.
