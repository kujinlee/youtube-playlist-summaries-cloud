<!-- codex-review: model=gpt-5.5 -->

NOT CONVERGED

**Blocking**
[scripts/gen-dashboard.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-dashboard.py:156): `_close_orphan_markup` disagrees with `_inline_scan` when truncation leaves an open code span containing `**`.

Property break: a truncated title can still render a bare delimiter, and HEAD adds delimiter text the author did not type. Positive: simple open `**...` and `` `... `` cases are closed; negative: `` `code ** ...`` is treated as nested bold by `_close_orphan_markup`, but `_inline_scan` treats code as literal.

REPRODUCED:

```text
raw: xxxxx... `code ** tail that is long enough to be truncated here...
head title: xxxxx... `code ** tail that is long enough to**`…
head html:  xxxxx... <code>code ** tail that is long enough to**</code>…
head text:  xxxxx... code ** tail that is long enough to**…
```

The relevant code is:

```python
if s.startswith("**", i):
    stack.pop() if stack and stack[-1] == "**" else stack.append("**")
...
if s[i] == "`":
    stack.pop() if stack and stack[-1] == "`" else stack.append("`")
```

After finding it, I checked the real store for truncated titles containing both delimiters; none currently match this class.

**High**
[scripts/gen-dashboard.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-dashboard.py:177): `ENTITY_TAIL` does not match hex numeric entities, so `_trim_url_tail` still severs `&#x27;`.

Property break: entity-aware trimming handles `&amp;` and `&#39;`, but not the `&#x27;` form produced by `html.escape(..., quote=True)` for apostrophes.

REPRODUCED:

```text
RAW  https://x.ee/a'**bold**
HTML <a href="https://x.ee/a&#x27">https://x.ee/a&#x27</a>;<strong>bold</strong>
```

The regex is:

```python
ENTITY_TAIL = re.compile(r"&(?:#[0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]*);$")
```

It needs the numeric hex form, e.g. `&#x27;` / `&#X27;`.

**Medium**
[scripts/gen-dashboard.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-dashboard.py:2234): the “every `--out` / `--fragment-only` path is ABSOLUTE” guard only sees double-quoted immediate string literals.

Positive: it catches the manifest’s double-quoted mutant. Negative: it misses an equivalent relative path written with single quotes.

REPRODUCED by changing, in a temp copy only:

```python
main(["--fragment-only", str(_frag), "--window", "14"])
```

to:

```python
main(['--fragment-only', 'frag.html', "--window", "14"])
```

Output:

```text
rc 0
206/206 passed
```

**Checked And Could Not Fault**
`python3 scripts/gen-dashboard.py --self-test` passed `206/206`.

`python3 scripts/check-plan-code.py --self-test` passed `136/136`.

`HOME=$(mktemp -d) python3 scripts/check-plan-code.py --mutate .` passed with `67 mutation(s), 0 survivor(s)`.

The 8 new `scripts/mutations/gen-dashboard.json` entries each went red through their named expected case when run individually in temp copies.

Live dashboard checksum stayed unchanged before and after mutation work:

```text
d8891c655150419f27eeabb4cb1fe295f62f3feb2d0f3d2328b01e3c7d772f47
```

I did not find round-3 content loss versus round-2 truncation; the reproduced `_close_orphan_markup` issue is content addition plus bare delimiter rendering, not dropped displayed text.
