<!-- codex-review: model=gpt-6.1-sol -->

1. **MAJOR — forbidden source trees can enter staged packages.** `scripts/mkt_stage.py:80`, `:121`, `:135`  
   **Breaking input → wrong output:** declare a file beneath `.claude/plans/`, declare that directory as a skill, or place a symlink to it inside a declared skill → staging accepts the resolved source and copies its contents. `_real()` checks repository containment, but never excludes `.claude/plans/`; the `.agents/skills` restriction applies only to individual `files` declarations. Recursive traversal bypasses that restriction too.  
   **Fix:** enforce source exclusions on every resolved file and directory before traversal or copying. Permit `.agents/skills` only through the intended skill declarations. Test direct declarations and symlink aliases. I did not read `.claude/plans/`; this finding follows from the code.

2. **MAJOR — Python retains host-installed packages.** `scripts/mkt_isolate.py:140`, `:150`  
   **Breaking input → wrong output:** the caller’s Python has a dependency installed in its interpreter-level site-packages → the isolated command imports it successfully, although a stdlib-only stranger would fail. Fresh `HOME` and a replacement `sitecustomize` do not disable interpreter-level site-packages or `.pth` processing.  
   **Evidence:** an isolated Python retained `/usr/local/Cellar/python@3.14/3.14.4_1/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages`; distribution discovery returned `pip` and `wheel`. This contradicts `docs/marketplace/isolation-baseline.md:24`.  
   **Fix:** use a clean interpreter environment with system site-packages disabled, and verify its import paths and package population. Preserve the audit hook deliberately.

3. **MAJOR — system Git configuration can supply author-specific behavior and credentials.** `scripts/mkt_isolate.py:150`; `docs/marketplace/isolation-baseline.md:57`  
   **Breaking input → wrong output:** host system Git configuration supplies an authenticated URL rewrite or credential helper → a stranger-world clone succeeds using host configuration or credentials that a real stranger lacks. The baseline acknowledges system configuration inheritance, but “as a stranger’s git would” does not establish that the configurations are equivalent. A helper can also reach the current OS user’s keychain; changing `HOME` does not change that identity.  
   **Fix:** disable system Git configuration and explicitly select empty global configuration. Keep credentials out of the baseline; any authorized authentication must be supplied separately and recorded. Keychain-backed authentication needs an explicit isolation boundary, rather than an inference from fresh `HOME`. I did not access keychain credentials or the prohibited token.

4. **MAJOR — preflight validates environment key names, not isolation-critical values.** `scripts/mkt_isolate.py:182`  
   **Breaking input → wrong output:** after `build_world()`, set `world.env["HOME"]` to the author’s home or `world.env["PYTHONPATH"]` to an author directory → preflight returns no refusal and `run_isolated()` passes those values to the child. Preflight inspects `world.home`, which can differ from the actual `HOME` environment value.  
   **Evidence:** replacing both values with foreign temporary paths produced `preflight: []`.  
   **Fix:** require `HOME`, `TMPDIR`, and `PYTHONPATH` to equal their corresponding world directories, validate their resolved containment, and enforce validation at the execution boundary.

The spike’s rerun was a legitimate staging-defect correction under Task 4’s explicit missing-import-closure exception. Adding unchanged `regen-pages.py` corrected the payload; it did not repair the component or weaken the success conditions. The five scripts cover the recorded operations: help, status, start, index request, and stop. They do **not** establish closure for the complete skill or other server routes. A top-level import scan misses route-triggered `importlib` loads, function-local imports, subprocess targets, file reads, and dependencies expressed in skill prose. The recorded start message, matching listener PID, and sentinel response support the narrow packaging GO, subject to the isolation defects above.

Task 1’s numbers reproduce using newline counts from Git blobs:

| Measurement | Re-derived result |
|---|---:|
| Nine files at `cacbac17` | `158+193+156+95+243+482+1384+450+438 = 3,599` |
| Same nine at `a4f6d4b5` | `604+363+1,780+2,907+450+438 = 6,542` |
| Ratio | `6,542 / 3,599 = 1.817727…`, rounded **1.82×** |
| Six Python files | `1,780+2,907+450+438+3,546+1,252 = 10,373` |
| Four skills | `158+195+156+95 = 604` |
| Three shared contracts | `363+73+211 = 647` |
| Stated line total | `10,373+604+647 = 11,624` |
| Named components | `6+4+3+4 hooks = 17` |

The four hooks contain another **308 lines**, explicitly excluded by the corrected sentence. The figures reproduce the declared population, rather than proving exhaustive membership.

Requested checks all exited **0**:

- `mkt_isolate.py --self-test`: `49/49 self-test cases passed`
- `mkt_stage.py --self-test`: `63/63 self-test cases passed` — live Claude validation also passed.
- `check-docs.py`: `Documentation integrity OK` — warnings/advisories only.

`install()` does fail loudly on either Claude command’s nonzero exit and on a missing installed directory after exit zero. I found no deterministic output-directory escape in staging’s normalized destination construction.

VERDICT: NOT CONVERGED
