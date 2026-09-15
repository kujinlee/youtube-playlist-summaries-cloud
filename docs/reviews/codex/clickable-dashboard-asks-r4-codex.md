<!-- codex-review: model=gpt-5.5 -->

Low

`no emitted rule hides the chooser` still does not verify the CSS surface that actually merges. The case builds the raw dashboard fragment with `_B(...)` at `scripts/gen-dashboard.py:1797`, then scans only `<style>` bodies in that fragment at `scripts/gen-dashboard.py:1839`. Production does not ship that fragment directly: `main` writes it to a temp file and invokes `brief-compose.py` at `scripts/gen-dashboard.py:3503`-`scripts/gen-dashboard.py:3505`. The composer then injects `SHIM`, lifted tray CSS, and chrome CSS into the final `<style>` at `scripts/brief-compose.py:838`-`scripts/brief-compose.py:839`, and returns that final document at `scripts/brief-compose.py:841`-`scripts/brief-compose.py:844`. So a composer/lifted-tray rule that hides `.pick` can reach the delivered page without this guard seeing it. Same narrower-than-rendered-surface issue exists for inline chooser styles: the chooser is a string at `scripts/gen-dashboard.py:926` and is inserted into option rows at `scripts/gen-dashboard.py:959`-`scripts/gen-dashboard.py:971`, but `style=` attributes are outside the `<style>` scan at `scripts/gen-dashboard.py:1839`. Current committed chooser markup has no inline `style=`, so this is a guard gap, not a present hidden button.

No Blocking or High findings. CONVERGED.

Verification run:

`python3 scripts/gen-dashboard.py --self-test` passed: `325/325`.

`python3 scripts/check-plan-code.py --self-test` passed: `128/128`.

Mutation metadata checks passed: `EXPECTED_MUTATIONS["scripts/gen-dashboard.py"]` is 68 at `scripts/check-plan-code.py:572`; the declared sum case expects 633 at `scripts/check-plan-code.py:3146`; `scripts/mutations/gen-dashboard.json` has 68 entries.

The four added mutation entries are present at `scripts/mutations/gen-dashboard.json:762`, `scripts/mutations/gen-dashboard.json:776`, `scripts/mutations/gen-dashboard.json:789`, and `scripts/mutations/gen-dashboard.json:803`. I verified each edit anchor occurs exactly once in `scripts/gen-dashboard.py`, and each `expect` name exactly matches one live case, including the cases at `scripts/gen-dashboard.py:1803`, `scripts/gen-dashboard.py:1812`, `scripts/gen-dashboard.py:1814`, and `scripts/gen-dashboard.py:1864`.

Opacity/nesting notes: `opacity:0%` is caught because the regex captures `0`; `opacity:0.5e-9` captures only `0.5`; `opacity:var(--x)` and `opacity:calc(0)` do not match and therefore fail open at `scripts/gen-dashboard.py:1846`-`scripts/gen-dashboard.py:1850`. A lone `.` matches, raises `ValueError`, and is swallowed at `scripts/gen-dashboard.py:1847`-`scripts/gen-dashboard.py:1850`; that is acceptable for invalid CSS, but it is still fail-open for unparseable values. Simple media/layer-scoped `.pick` hides are caught by the current `([^{}]+){([^{}]*)}` walk at `scripts/gen-dashboard.py:1841`, but this is still a regex CSS scan, not a full cascade/rendered-page check.
