<!-- codex-review: model=gpt-6.1-sol -->

### R2-F1 — High — Committed bytecode can replace the verified harness source

**Location:** `scripts/check-merge-ready.py:1495`

**Scenario:** Blob verification proves the materialised bytes match HEAD, but `_import_sibling` uses Python’s normal loader. A committed unchecked-hash `.pyc` can execute different code from the verified `.py` source. The self-test’s fake HEAD silently excludes `__pycache__`, leaving this route untested.

**Repro:** In a temporary real repository, commit a display containing pin 5, harness source holding 4, and `scripts/__pycache__/check-plan-code.cpython-314.pyc` holding 5. Generate the cache with `_code_to_hash_pyc(..., checked=False)`. Remove that cache from the working tree without committing.

Measured:

```text
working-tree source held: 4
branch pin_pair: ({'scripts/a.py': 5}, {'scripts/a.py': 5})
branch pin_falls: []
master: PinsUnreadable — held 4, displayed 5
```

Thus the rewritten held-side import accepts a mismatch master refused.

**Fix:** Reject committed bytecode caches during materialisation, or force source-only loading for the harness and its repository imports. Add this case without filtering its cache from the fake HEAD.

### R2-F2 — Medium — Interpreter prefixes can admit working-tree sibling modules

**Location:** `scripts/check-merge-ready.py:1504`, `scripts/check-merge-ready.py:1533`

**Scenario:** `_lib_roots` trusts everything recursively beneath `sys.prefix` and the other interpreter prefixes. A repository beneath a virtual environment’s prefix is consequently treated as interpreter code. Its paths and cached modules survive isolation.

**Repro:** Created a real virtual environment with a project at `<venv>/project`. HEAD’s `_redir.py` held pin 4; a preloaded working-tree `_redir.py` held 5. HEAD’s materialised harness imported `_redir`.

Measured:

```text
HEAD _redir held: 4
cached working-tree _redir held: 5
branch pin_pair: ({'scripts/a.py': 5}, {'scripts/a.py': 5})
branch pin_falls: []
```

An untracked module in that working-tree directory also remained importable when HEAD lacked it.

**Fix:** Restrict trusted origins and search paths to interpreter library locations, excluding project and third-party origins. Ensure repository sibling imports cannot reuse cached external modules.

### R2-F3 — Low — The first isolation call does not restore the entry module mapping

**Location:** `scripts/check-merge-ready.py:1525`, `scripts/check-merge-ready.py:1535`

**Scenario:** `_lib_roots()` runs before the snapshot. Its lazy imports become part of the saved mapping and survive restoration. Existing restore cases run after this initialization has already occurred.

**Repro:** In a fresh Python process, import the gate, snapshot `sys.modules`, then execute an empty `_isolated_import()` block. On this worktree’s interpreter, it leaves these additional entries:

```text
_osx_support
_sysconfigdata__darwin_darwin
```

The mapping is therefore not restored exactly, even for an empty successful block.

**Fix:** Snapshot before initialization and cover initialization with the restore’s `try/finally`. Add a first-call restore case.

Validation completed:

- Both requested self-tests passed: **384/384** and **418/418**.
- All **14 new mutations and six changed entries** failed exactly their declared `expect` sets in temporary staged trees with a green control. No widened expectation concealed an unexpected failure.
- The merge preserved master’s answer-binding implementation and mutation entries. The merged manifest has **184 unique entries**.
- Truncated streams, hash mismatches, empty listings, oversized length fields and injected timeouts raised `PinsUnreadable` and removed temporary directories.
- Builtin/frozen-name replacements restored mapping identity on successful and failing exits. The compile memo distinguished changed content and restored the normal compiler afterward; its scope remains self-test-only.
- Both displays’ text comes from their respective revisions and is parsed by the one HEAD module. No additional base-display defect was demonstrated.
- Real Git calls remain without configured time or memory bounds, as on master; injected timeout handling does not establish bounded execution for a huge tree.

The worktree remains unchanged.

## Loosening answers
LOOSENING-CHECK d2d3b8498823: not a loosening
LOOSENING-CHECK a3675a17d265: not a loosening
LOOSENING-CHECK 46da71649200: not a loosening
LOOSENING-CHECK e36f8dfa2eb5: not a loosening
LOOSENING-CHECK bb9bf96e21f2: not a loosening
LOOSENING-CHECK 3e8b51e50547: not a loosening
LOOSENING-CHECK be450713bce4: not a loosening
LOOSENING-CHECK a6bd50cab65e: not a loosening
LOOSENING-CHECK c47564441466: finding: the branch accepts committed unchecked-hash bytecode holding pin 5 while HEAD's harness source holds 4; with that cache removed from the working tree, master reads source and refuses the held/display mismatch.
LOOSENING-CHECK db3eea4bbfbd: not a loosening
LOOSENING-CHECK e6423f648a1d: not a loosening
LOOSENING-CHECK 1249da34105f: not a loosening
LOOSENING-CHECK 4f118205f0ba: not a loosening
LOOSENING-CHECK f32c87427819: not a loosening
VERDICT: NOT CONVERGED
