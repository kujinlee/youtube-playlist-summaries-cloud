<!-- codex-review: model=gpt-5.5 -->

**Findings**

1. **High: trigger text staleness is still unguarded.**  
   `cache_document` stores the picked trigger text in the cache at `scripts/recall-llm.py:429-443`, but `--fire` only checks that the entry file still exists via `cached_entry_verdict` at `scripts/recall-llm.py:502-532`, then renders the cached trigger at `scripts/recall-llm.py:711`. I reproduced a cache armed with `OLD trigger text` while the live corpus entry said `NEW trigger text`; `do_fire(again=True)` exited `0` and surfaced `OLD trigger text`.  
   This is wrong if changing a trigger’s text under the same filename should force re-arm. It would be wrong as a finding only if cached trigger text is intentionally historical and live trigger edits are explicitly non-invalidating.

2. **High: `parse_response` silently accepts duplicate JSON keys.**  
   `parse_response` uses plain `json.loads` at `scripts/recall-llm.py:379-401`, so `{"2":"running-codex", "2":"NONE"}` becomes `{2: "NONE"}`. I ran that exact input and it accepted the last value. That is “guessing” rather than rejecting: the model supplied two answers for one step and one was silently dropped.  
   This is wrong only if duplicate keys are considered impossible or acceptable model packaging. They are valid enough for Python’s parser to collapse.

3. **High: rc contract has real exit-1 paths.**  
   `main` catches only `Refusal` at `scripts/recall-llm.py:1291-1296`. I reproduced two unhandled exceptions:
   `read_armed_plan` reads a plan as UTF-8 at `scripts/recall-llm.py:630`; invalid UTF-8 raises `UnicodeDecodeError` and exits `1`.  
   `do_fire` writes `.last-surfaced` at `scripts/recall-llm.py:719-720`; an unwritable cache directory raises `PermissionError` and exits `1`.  
   The hook then treats unrecognized matcher rc values as silence at `.claude/hooks/surface-recall.sh:40-45`, so this can collapse “could not look” into “nothing surfaced.”  
   This is wrong only if invalid/unwritable local files are outside the supported operating envelope.

4. **Medium: cache validity ignores the recorded model and corpus size.**  
   The cache records `corpus_size` and `model` at `scripts/recall-llm.py:439-440`, but `cache_verdict` checks only the plan fingerprint at `scripts/recall-llm.py:447-464`. I changed a valid cache to `"model": "not-opus"` and `"corpus_size": 999999`; `do_fire(again=True)` still exited `0` and surfaced the entry.  
   This is wrong only if those fields are purely diagnostic and not part of the cache contract. If the model changes behavior or the corpus-size claim matters, this is stale cache served as valid.

5. **Low: measurement record has a fourth arithmetic/detail error.**  
   The review says “Eight of the twenty correct entries rank at 66, 82, 94, 95, 106, 107 and 108” at `docs/reviews/claude/semantic-recall-replication-2026-09-29.md:170-173`, but that list has seven ranks. The fixture repeats the same mismatch: `_ranks_of_the_eight_that_sank` contains seven values at `scripts/fixtures/recall-replication-2026-09-29.json:837-845`.  
   This does not refute recall@10 = `12/20`; it refutes the “eight ranks listed” supporting detail.

**Verified**

`python3 scripts/recall-llm.py --self-test` passed: `128/128`.  
`python3 scripts/check-selftest-counts.py` passed.  
`python3 scripts/check-fixture-variation.py` passed.  
`python3 scripts/check-plan-code.py --mutate .` passed: `1087 mutation(s), 1087 killed, 1087 attributed, 0 survivor(s)`.  
I also counted `scripts/mutations/recall-llm.json`: 53 entries, no duplicate names, no duplicate edit anchors.

**Could Not Establish**

I did not find hook JSON malformation: the wrapper uses `json.dumps` at `.claude/hooks/surface-recall.sh:50`, and quotes/newlines/braces in a stale-cache payload encoded cleanly. I also did not prove a hang in the hook path; direct hook execution returned `0`. I did not manually prove every one of the 53 mutation entries non-vacuous beyond the full mutation run and duplicate-anchor/name scan.
