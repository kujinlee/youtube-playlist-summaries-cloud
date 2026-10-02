<!-- codex-review: model=gpt-5.5 -->

**Findings**

1. **High: H2 can still print a stale trigger when the live entry exists but lost its trigger/frontmatter.**  
   `live_trigger_for()` returns `None` both for “no corpus/unreadable” and “entry file has no `FIRES-WHEN:`” at `scripts/recall-llm.py:349-363`. `do_fire()` then falls back to `live_trigger or cached_trigger` at `scripts/recall-llm.py:929-934`, so a present entry rewritten without frontmatter still surfaces the cached old sentence. I reproduced `rc 0` with `FIRES-WHEN: THE CACHED OLD TRIGGER` while the live file contained only body text.  
   Proves wrong: an end-to-end `--fire` where the entry file exists but has no frontmatter either refuses stale cache or prints no cached trigger.

2. **High: invalid UTF-8 cache files are no longer tracebacks, but the hook still swallows them as rc=2 silence.**  
   The cache read goes through `read_or_refuse()` at `scripts/recall-llm.py:909`; that helper always raises bare `Refusal` at `scripts/recall-llm.py:307-312`, so an undecodable cache exits `2`, not `3`. The hook only forwards rc `0`, rc `3` with output, and rc `5`; rc `2` falls into silence at `.claude/hooks/surface-recall.sh:50-72`. I reproduced an invalid UTF-8 cache returning rc `2` with the “recall cache ... is not valid UTF-8” message. Direct CLI is named; hook observation is still silence.  
   Proves wrong: the same invalid UTF-8 cache produces rc `3`, or the hook forwards the cache-read refusal.

3. **Medium: `UNREADABLE_PLAN = 5` is only preserved through `--fire`, not every mode.**  
   `do_fire()` converts `plan_verdict()` failure into `UnreadablePlan` at `scripts/recall-llm.py:884-893`, so the hook’s `5)` arm at `.claude/hooks/surface-recall.sh:66-71` does fire. But `prepared_prompt()` raises bare `Refusal` for the same verdict at `scripts/recall-llm.py:841-851`, and `--print-prompt`/`--arm` reach that path via `scripts/recall-llm.py:1760-1763`. I reproduced the same unreadable armed plan returning rc `5` for `--fire` and rc `2` for `--print-prompt`.  
   Proves wrong: `--print-prompt` and `--arm` on an armed unreadable plan return rc `5`, not rc `2`.

4. **Medium: the H1(e) mutation does not measure the ordering it names.**  
   The mutation named “dedupe marker is written BEFORE the print again” edits `scripts/mutations/recall-llm.json:652-660`, but its replacement deletes `print(text)` rather than moving `marker_file.write_text()` before it. The expected case then fails because nothing prints, not because an unwritable marker write suppresses a valid match. The production code is print-then-best-effort-write at `scripts/recall-llm.py:949-965`, but this mutation is not a faithful guard for the regression named.  
   Proves wrong: a mutation that actually reorders marker write before print, plus a case where marker write fails and the valid match must still be printed.

**Verified**

`python3 scripts/recall-llm.py --self-test` passed: `164/164 self-test cases passed`.

`python3 scripts/check-plan-code.py --mutate .` passed: `55 file(s), 1119 mutation(s), 1119 killed, 1119 attributed, 0 survivor(s)`.

I also spot-checked B1’s three-way behavior: unreadable plan `--fire` returns `5`, finished plan returns `0`, no armed plan returns `2`.

**Could Not Establish**

I did not call `--arm`, per instruction, so I could not prove `claude -p` ignores user-level `$HOME` settings; I only verified `outside_repo()` handles symlink, relative, and prefix cases, and the code sets `cwd=sandbox` at `scripts/recall-llm.py:790-799`.

I did not manually prove all 164 cases and all 77 recall mutations non-vacuous; I checked the retargets most relevant to the round-1 fold and relied on the full mutation run for the rest.

I did not prove the new print-before-marker ordering under broken stdout or concurrent `--fire` calls. The current code favors “print first, marker best-effort,” but duplicate output under races remains plausible.
