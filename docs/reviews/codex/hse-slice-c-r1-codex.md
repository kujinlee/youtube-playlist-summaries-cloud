<!-- codex-review: model=gpt-6.1-sol -->

- **MAJOR — scripts/check-shipping-sets.py:367:** Closure derives its entry points from the declaration being checked, so deleting an entry point deletes its verification. Concrete input: remove `skills/brief/SKILL.md` from the real declaration’s `installed_files` and component files, lowering `expected_count`. Observed: `--closure` returns rc 0, `0 gaps`. This violates Task 7’s FAILS IF.

- **MAJOR — scripts/check-shipping-sets.py:92:** Interpreter options hide executable dependencies from both checks. Concrete input: a mapped skill containing `Run ` followed by backticked `python3 -u scripts/secret.py`, with `secret.py` present in the repository but unmapped and undeclared. Observed: both map and closure return rc 0, `0 gaps`.

- **MAJOR — scripts/check-shipping-sets.py:348:** Read instructions spanning lines lose their dependencies. Concrete input: `Read the following file:\n\n` followed by backticked `../shared/secret.md`; that file exists in the source tree but is omitted from the declaration. Observed: closure returns rc 0, `0 gaps`, with zero external reads.

- **MAJOR — scripts/check-shipping-sets.py:433:** Invalid channels silently bypass closure. Concrete input: `{"packages":{"p":{"channel":"plguin","installed_files":["absent.py"]}}}`. Observed: rc 0, `p: SKIPPED — reusable-workflow channel, no installed tree`, then `0 gaps`; the nonexistent file is never checked.

- **MAJOR — scripts/check-shipping-sets.py:436:** Empty plugin declarations pass instead of reporting CANNOT RUN. Concrete input: package `p` with `channel: "plugin"`, `installed_files: []`, and component `x` containing `files: []`, `expected_count: 0`. Observed: rc 0, `0 gaps`, despite the plan explicitly requiring empty file sets to fail.

- **MAJOR — scripts/check-shipping-sets.py:179:** Missing tracked candidates are silently discarded. Concrete input: track two skill files, delete one from disk, and map only the surviving skill. Observed: `--map` returns rc 0, `0 gaps`; the unreachable tracked input produces neither a gap nor CANNOT RUN.

- **MAJOR — scripts/mkt_stage.py:477:** Installed-tree enumeration suppresses directory permission errors. Concrete input: component directory `skills/a/` containing readable `SKILL.md` and `hidden/secret.md`, with `hidden/` chmod 000. Observed: `declare()` succeeds, omits `secret.md`, and derives `expected_count: 1` instead of reporting CANNOT RUN. Both requested self-tests nevertheless passed: `79/79 self-test cases passed` and `118/118 self-test cases passed`.

VERDICT: NOT CONVERGED
