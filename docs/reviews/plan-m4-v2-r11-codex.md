<!-- codex-review: model=gpt-5.5 -->

**High**

`scripts/check-paid-caller-arrival.py:121` / `scripts/check-paid-caller-arrival.py:133`

```python
if c == "\\":
    i += 2
    continue
...
if c == "/" and i + 1 < n and src[i + 1] == "/":
```

The scanner still treats valid TypeScript regex syntax as comment syntax, so a real production caller can be filed as comment-only and return `DORMANT`.

Concrete proof I ran with the script imported against a temp tree:

```ts
const re = /\/\//; await sb.rpc('record_artifact', { p: 1 });
```

Observed output:

```text
production callers: 0   (comments, not callers: 1)
DORMANT
rc 0
```

That is a real `.rpc('record_artifact')` call outside a comment, but the scanner sees the final `//` inside the regex literal and blanks the rest of the line.

Same parser also false-fires on comments inside template interpolation because backticks are treated as an opaque string and `${...}` is never parsed as code:

```ts
const s = `${/* record_artifact */ value}`;
```

Observed:

```text
production callers: 1
FIRED
rc 1
```

What would prove me wrong: a scanner test showing the first fixture exits `1` with a production caller, and the second exits `0` with the mention counted as comment-only or ignored.

**Medium**

`docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh:151`

```bash
RAN=$(grep -cE 'NOTICE:.*\bok\b' <<<"$OUT")
```

The new floor counts every `NOTICE: ... ok ...` in the whole psql transcript, not assertion-owned notices. A future schema/spec source can emit enough unrelated ok-notices while `05_assert.sql` is gutted, and gate 1 will still meet the floor.

Concrete failure scenario:

```sql
do $$ begin
  for i in 1..120 loop
    raise notice 'ok compatibility migration %', i;
  end loop;
end $$;
```

plus a truncated `05_assert.sql` containing no real assertions. Inputs produce `ALL_STATEMENTS_OK`, `RAN=120`, exit `0`, even though zero behavioral assertions ran.

Current observation: today this is not firing accidentally; I checked `0027`, spec `0[134]*.sql`, and the seed for `raise notice`, and only `05_assert.sql` emits ok-notices. The defect is that the new guard does not preserve that boundary.

What would prove me wrong: the counted pattern is made assertion-specific, or the script counts only output attributable to `05_assert.sql` assertion blocks and a fixture with unrelated ok-notices plus gutted assertions fails.

**Verification Run**

Passed:

```text
python3 scripts/check-paid-caller-arrival.py --self-test  # 18/18
python3 scripts/check-paid-caller-arrival.py              # DORMANT today
./scripts/m4-base-db.sh --self-test                       # 10/10
./scripts/run-schema-assertions.sh --self-test            # 15/15
docs/.../verify-schema.sh                                 # 120 assertions ran
```

Not run: `M4_PHASE=post ./scripts/check-schema-gates.sh`, because it invokes the mutation harnesses and I could not establish reviewer exclusivity.

NOT CONVERGED
