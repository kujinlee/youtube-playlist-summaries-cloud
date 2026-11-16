<!-- codex-review: model=gpt-6.1-sol -->

1. **MAJOR** — `scripts/check-canonical-source.py:340` (also `:290`), compared with `scripts/check-plan-code.py:625–630`. The two rules still disagree:
   
   - `.claude/settings.json/` and `.claude/settings.json/foo` → canonical rejects; `_staged_root` returns `.claude/settings.json`.
   - `docs/../CONTEXT.md` → canonical rejects; `_staged_root` returns `docs`.
   - `docs` → canonical rejects; `_staged_root` returns `docs`.

   The new claim that `_staged_root` matches file entries exactly is false: its prefix arm applies to every root. Proposed fix: distinguish files from directories in `_staged_root`, define consistent traversal and directory-entry handling, and test both implementations against these inputs. `./` prefixes and case variants tested were rejected by both.

2. **MAJOR** — `scripts/check-canonical-source.py:663`. The identity comparison erases which set owns an entry. Breaking change: move `"supabase/"` from `STAGEABLE_PREFIXES` into `STAGEABLE_FILES` → identity passes and the entire suite still reports `33/33 passed`, while `supabase/migrations/x.sql` becomes wrongly unstageable. Proposed fix: compare prefixes and files separately against separately classified `HARNESS_TREE` entries, and add mutations moving entries between sets.

   Moving `.claude/settings.json` into prefixes also escapes identity, although the refusal case catches it. Dropping that file is caught by identity.

Verification: all 15 manifest mutations failed through their declared case, including all three new mutations; the pin matches.

Requested command result lines:

```text
33/33 passed
canonical sources OK — 3 mechanism(s) described once each (handoff-path, corpus-search, marketplace-inventory)
```

VERDICT: NOT CONVERGED
