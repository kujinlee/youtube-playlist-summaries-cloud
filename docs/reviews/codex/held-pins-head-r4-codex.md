<!-- codex-review: model=gpt-6.1-sol -->

No findings, including **no BLOCKING findings**, at `31aac2aa67fa61aad57de6cb6fa1fb9c91179b03`.

Reviewed the round 3 fold, full branch diff, and required history.

- `xml/` and its subpackages are refused by their top-level name. Case variants did not shadow on this filesystem. `.pth` files are omitted; `-S` disables site processing. Nested modules resolve through their parent package. Parent and child use the same Python executable, keeping the stdlib-name check consistent across 3.12 and 3.14.
- Post-kill waits are bounded. Pipe and temporary-directory failures cannot produce READY; `main()` converts collection exceptions to CANNOT RUN.
- All six mutations—M1, M1b, M1c, M2, M3, M4—failed through their declared named cases. The manifest contains **187 unique entries**, matching the pin.
- Backlog #578 correctly identifies pre-existing exposure. Independently confirmed that master’s actual script invocation executes `scripts/importlib/__init__.py` on both Python versions. Also reproduced that startup shadow hiding a pin fall through `builtins.sorted`. The five disputed r3 answers therefore do not establish a loosening.

Required tests passed: merge-ready **400/400**; plan-code **418/418**. Worktree unchanged.

## Loosening answers
LOOSENING-CHECK d2d3b8498823: not a loosening
LOOSENING-CHECK a3675a17d265: not a loosening
LOOSENING-CHECK c65bf04c5a84: not a loosening
LOOSENING-CHECK 7987d773f208: not a loosening
LOOSENING-CHECK aeac2f13505f: not a loosening
LOOSENING-CHECK 46da71649200: not a loosening
LOOSENING-CHECK ed1d0f2f0938: not a loosening
LOOSENING-CHECK 1ae2b3e74a4b: not a loosening
LOOSENING-CHECK e36f8dfa2eb5: not a loosening
LOOSENING-CHECK bb9bf96e21f2: not a loosening
LOOSENING-CHECK 3e8b51e50547: not a loosening
LOOSENING-CHECK be450713bce4: not a loosening
LOOSENING-CHECK c47564441466: not a loosening
LOOSENING-CHECK 7514eca741d1: not a loosening
LOOSENING-CHECK 90f61d5b450f: not a loosening
VERDICT: CONVERGED
