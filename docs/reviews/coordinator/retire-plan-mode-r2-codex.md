<!-- provenance (coordinator note, NOT Codex's words): dispatched with --model gpt-5.5
     --timeout 1800, the configuration that worked in r1. SCOPE was r1's own FIXES
     (git diff 71f86f9a..6e5b2b78), not the original change. The intrusion line the wrapper
     printed names the coordinator's own stdout redirect target — a false positive of the
     harness setup, adjudicated per backlog #92. Below the rule is Codex's verbatim message. -->

<!-- codex-review: model=gpt-5.5 -->

**Findings**

High — `coverage_shortfall()` proves only equal counts, not the scanned corpus identity. In `6e5b2b78:scripts/check-plan-file-tags.py:134-136`, a wrong scan passes whenever the wrong tree has the same number of `*.md` files as `ROOT/docs`. Observation I ran against the committed file: intended `docs/` had `a.md` and `has-tag.md`; selected wrong root had `x.md` and `y.md`; `audit(selected)` returned `scanned=2`, intended total was `2`, and `coverage_shortfall(docs, 2)` returned `None`. That is a false green while the intended corpus, including a live retired tag, was not scanned. The right property needs path identity/set coverage, not cardinality.

Medium — unreadable Markdown is misreported as corpus narrowing and the accurate finding is suppressed. In `6e5b2b78:scripts/check-plan-file-tags.py:153-158` unreadable files produce findings but do not increment `scanned`; then `main()` calls `coverage_shortfall()` before printing findings at `:379-382`. Observation from a temp repo with `docs/ok.md` plus invalid UTF-8 `docs/bad.md`: `python3 scripts/check-plan-file-tags.py` exited `2`, stdout was empty, stderr said `read 1 of 2 ... The corpus was NARROWED`. That is fail-closed, but the recorded cause is false and the file-level “could not be read” finding never reaches the user.

Low — the new recorded measurement is already stale. `6e5b2b78:scripts/check-plan-file-tags.py:123-126` records `DOCS = ROOT/"docs"/"reviews"` as `896` docs and `220` unread docs. I measured the current head tree with `Path.rglob`: `docs` has `1117` Markdown files and `docs/reviews` has `897`. The delta is still `220`, but the quoted live-run output is no longer reproducible.

**Checked**

`python3 scripts/check-plan-file-tags.py --self-test` on committed `6e5b2b78` content: `33/33`.

`python3 scripts/check-plan-code.py --self-test`: `229/229`.

Mutation counts verified by running/parsing manifests: total `385`; `check-plan-file-tags` declared `11` and manifest has `11`; `check-plan-code` manifest has `44`.

Isolated `check-plan-file-tags` mutation run from a staged `6e5b2b78` tree: all `11` caught, no survivors.

Retargeted `check-plan-code` mutation: caught by the named case, with verdict row `fails=['plan mode refuses to print a tally it did not earn']`; it does exercise the retargeted `evidence()` line.

H1 splitter probe: using the real file-read path, CRLF, no trailing newline, empty file, and CR-before-fence behaved consistently with `check-plan-code.extract`. I did not find a regression there.

I did not run the full `python3 scripts/check-plan-code.py --mutate .` 15-minute suite.
