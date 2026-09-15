<!-- codex-review: model=gpt-5.5 -->

**Findings**
Blocking — `parse_header` still lets malformed findings become clean instrument findings and reach `STOP`.
`scripts/check-review-decision.py:164` promises malformed headers raise, but `_scalarise` silently skips malformed pairs at `scripts/check-review-decision.py:193-195`, `_block_findings` returns any nonempty partial dict at `scripts/check-review-decision.py:231-233`, and convergence only checks `severity` / `aim` with `.get()` at `scripts/check-review-decision.py:117-121`. I ran this fixture:

```yaml
findings:
  - id: H1
    severity High
    aim: instrument
    fix_induced: false
```

It parsed as `{'id': 'H1', 'aim': 'instrument', ...}` and `decide(..., "one-round", True)` returned `STOP`. This is the same fail-open class as r1 B1, one layer deeper: parity proves an item became a dict, not that the required fields are present and well-formed. `docs/round-header-template.md:47-50` explicitly says the machine checks fields are present and well-formed; it does not.

High — `scripts/` is still a broad contained allowlist, and it downgrades money/schema gates.
`scripts/check-review-decision.py:56-58` makes every `scripts/` path contained unless it also matches `RISK_PREFIXES`, but `RISK_PREFIXES` at `scripts/check-review-decision.py:65-73` has no risky `scripts/` entries. I ran `scope_for(["scripts/check-paid-caller-arrival.py"])` and got `one-round`. That file’s own contract says it protects the paid-attempt trigger: shipping a caller before the backlog decision “silently promotes a summary from 1 paid attempt to 5” at `scripts/check-paid-caller-arrival.py:13-16`, and its observed event includes `scripts/` production surface at `scripts/check-paid-caller-arrival.py:22-23`. I also ran `scope_for(["scripts/check-live-schema.py"])` and got `one-round`; that gate exists because other schema gates do not read the live database at `scripts/check-live-schema.py:10-14`. Treating all scripts as contained repeats the old allowlist mistake inside the inverted default.

Medium — the parity check refuses a legitimate YAML string with a bullet.
`docs/round-header-template.md:27` allows a `halves.<name>` value to be a `GAP:` string. YAML block scalars are strings, but `declared = re.findall(r"^\s*-\s", body)` at `scripts/check-review-decision.py:183` counts bullets anywhere in the header, not just under `findings:`. I ran a header with:

```yaml
halves:
  claude: |
    GAP: unavailable
    - connector disabled
findings:
  - {id: L1, severity: Low, aim: instrument, fix_induced: false, component: c, disposition: filed}
```

It raised `header declares 2 finding item(s) but 1 parsed`. This is a false CANNOT RUN, not a false STOP, so I’m not grading it Blocking.

**Checks**
`python3 scripts/check-review-decision.py --self-test` passed: `38/38 self-test cases passed`.

I re-derived the card citations by script: 13 occurrences, all unique, all resolve. The drifted citation is now correct: `docs/review-method.md:441` is “How to record the call.” The other card targets also resolve, including `:387`, `:394`, `:396`, and `:398`. I found the current `SUPERSEDED 2026-09-14` marker at `docs/review-method.md:387`; it did not shift the later `:441` target.

Mixed flow/block findings parsed correctly in my fixture, a following dedented key after `findings:` parsed correctly, and `round: 9` with empty `findings:` still returns zero findings. `middleware`’s no-slash prefix is loose but conservative: `middleware-helpers.ts` becomes `full-loop`. A deleted `app/api/...` path would still force `full-loop` because `git diff --name-only` supplies the path and `app/api/` is risky at `scripts/check-review-decision.py:67`.

**NOT CONVERGED** — 1 Blocking, 1 High, 1 Medium.
