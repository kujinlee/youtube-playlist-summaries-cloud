<!-- codex-review: model=gpt-5.5 -->

**Blocking**

`scripts/check-features.py:52` lets wrapped node prose hide status tokens when the continuation starts with `>` or `<!--`:

```python
if nodes and line.strip() and not line.startswith(("#", "<!--", ">")):
```

Concrete bypass:

```md
# Feature map
## PRODUCT
### summarise-a-video
state: built
for: Turns one video's transcript
> currently broken, see #322.
anchors: cloud-publishing
```

Observed via `parse_features()` + `check_nodes()`:

```text
parse problems: []
node problems: []
```

The hidden line contains both `currently` and `#322`, but because it is exempted as a blockquote/comment-looking line, it never reaches `purpose` and is never searched. This violates the “wrapped continuation must be refused, not silently merged/dropped” rule.

**High**

`scripts/check-features.py:62-66` silently overwrites duplicate fields:

```python
if key == "state": n.state = value
elif key == "for": n.purpose = value
elif key == "expected-because": n.expected_because = value
elif key == "areas": n.areas = [a.strip() for a in value.split(",") if a.strip()]
elif key == "anchors": n.anchors = [a.strip() for a in value.split(",") if a.strip()]
```

That allows earlier forbidden content to disappear before the checks run. Concrete bypasses I ran:

```md
# Feature map
## PRODUCT
### rate-limiting
state: absent
for: Stops one account exhausting spend.
anchors: cloud-publishing
anchors:
expected-because: standard for a hosted service.
```

Result:

```text
state absent ... anchors []
problems []
```

So an `absent` node can contain a fragment line and still pass if a later empty `anchors:` overwrites it.

Another bypass:

```md
# Feature map
## PRODUCT
### rate-limiting
state: absent
for: currently broken, see #322.
for: Stops one account exhausting spend.
expected-because: standard for a hosted service.
```

Result:

```text
problems []
```

The status-bearing prose is discarded by the second `for:`. A gate that owns the grammar should reject duplicate fields, not apply last-write-wins.

**Low**

`.claude/hooks/regen-features-page.sh:31-38` silently swallows malformed hook stdin:

```bash
FILE_PATH=$(cat | python3 -c "
...
except Exception:
    print(''); raise SystemExit
...
" 2>/dev/null) || exit 0
```

Concrete trigger:

```bash
printf 'not json' | bash .claude/hooks/regen-features-page.sh
```

Observed:

```text
rc=0
stdout/stderr empty
```

The exit code behavior is correct, but the malformed-input failure is invisible. The failing-generator path does make failure visible; I verified it exits `0` and prints the stale-page warning.

**Verification**

Ran:

```text
python3 scripts/check-features.py                         PASS
python3 scripts/check-features.py --self-test             PASS, 25/25
python3 scripts/gen-features-page.py --self-test          PASS, 8/8
python3 scripts/gen-features-page.py --fragment-only ...  PASS
python3 scripts/check-fixture-variation.py scripts/check-features.py scripts/gen-features-page.py  PASS
python3 scripts/check-selftest-counts.py                  PASS
python3 scripts/check-plan-code.py --self-test            PASS, 128/128
```

I also mechanically checked both new mutation manifests: every `edits` anchor occurred exactly once, every `expect` named a real self-test case, and each of the 17 + 10 mutations reddened its named case in targeted runs. Full `python3 scripts/check-plan-code.py --mutate .` was **NOT RUN to completion**; I interrupted it at mutation 293/764 after the feature-hub mutations had already passed in the targeted checks.
