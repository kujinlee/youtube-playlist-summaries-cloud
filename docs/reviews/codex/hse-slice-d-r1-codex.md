<!-- codex-review: model=gpt-6.1-sol -->

- **MAJOR — scripts/check-publishability.py:235:** Any supplied default suppresses a required configuration finding. On a scratch copy, appended `SCAN_TOKEN = os.getenv("SUPABASE_REVIEW_TOKEN", None)` followed by `if not SCAN_TOKEN: raise RuntimeError("SUPABASE_REVIEW_TOKEN required")` to `scripts/page_chrome.py`. The scan reported `page-chrome` as `scanned`, emitted only mentions, and produced no dependency finding for the required token.

- **MAJOR — scripts/check-publishability.py:376:** Python invocations of missing files disappear because detector 2 requires the target to exist; detector 6 also excludes the interpreter. Appended `subprocess.run(["python3", "scripts/missing-review-helper.py"], check=True)` to scratch `scripts/page_chrome.py`. The scan reported `scanned` with no finding for this invocation, although the helper is absent and cannot ship.

- **MAJOR — scripts/check-publishability.py:278:** Documented tool prerequisites using “Use” become mentions. Appended ``Use `TaskList` to enumerate tasks before proceeding.`` to scratch `brief/SKILL.md`. The scan emitted a detector-4 mention with no finding id; no detector reported the dependency.

- **MINOR — scripts/check-publishability.py:1447:** The unreadable-registration self-test passes before reaching its subject. Its fixture contains malformed `.claude/settings.json`, but `scan` receives the system temporary directory as its root. Observed error: `component 'b': file 'scripts/bare.py' does not exist`. On a scratch copy with registration reading removed (`hooks = set()`), this specific case still passed with `'RAISED CannotRun'`.

- **MINOR — docs/marketplace/scan-2026-11-17.json:15101:** The committed report does not match a fresh HEAD report: `measured_at` is `f8390575d87a507766e01a4e76f2bff33ea19a29`, versus fresh `c4861690cf9b5afdb88a23382c7ff5082ded4408`. Component results are identical. Required command final lines: `python3 scripts/check-publishability.py --self-test` → `97/97 self-test cases passed`; `python3 scripts/check-publishability.py --out /tmp/hse-d-fresh.json` → `45 component(s): 45 scanned, 0 CANNOT RUN`.

## Loosening answers
LOOSENING-CHECK 636d4531ad22: not a loosening
VERDICT: NOT CONVERGED
