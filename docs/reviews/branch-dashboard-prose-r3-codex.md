<!-- codex-review: model=gpt-5.5 -->

NOT CONVERGED

**Medium**
[scripts/gen-dashboard.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-dashboard.py:217)

The new URL cut trims valid URL characters when a delimiter follows the URL. Code in force:

```python
cut = min((p for p in (url.find("**"), url.find("`")) if p != -1),
          default=-1)
if cut != -1:
    url = url[:cut].rstrip(".,;:)]")
if INLINE_URL.fullmatch(url):
    out.append(f'<a href="{url}">{url}</a>')
    i += len(url)
```

REPRODUCED:

```bash
python3 - <<'PY'
import importlib.util
spec=importlib.util.spec_from_file_location('gd','scripts/gen-dashboard.py')
gd=importlib.util.module_from_spec(spec); spec.loader.exec_module(gd)
for s in ['https://x.ee/z(foo)**bold**', 'https://x.ee/z(foo)`code`']:
    print('INPUT:', s)
    print('OUTPUT:', gd._inline(s))
PY
```

Output:

```text
INPUT: https://x.ee/z(foo)**bold**
OUTPUT: <a href="https://x.ee/z(foo">https://x.ee/z(foo</a>)<strong>bold</strong>
INPUT: https://x.ee/z(foo)`code`
OUTPUT: <a href="https://x.ee/z(foo">https://x.ee/z(foo</a>)<code>code</code>
```

What breaks: the markup after the URL survives, but the linked URL is wrong. The closing `)` is part of the intended URL span before the markup delimiter, but `rstrip(".,;:)]")` drops it after cutting. This is exactly in the new `cut` / `rstrip` / `fullmatch` logic.

After finding the class, I grepped `docs/dashboard-entries.md`:

```bash
rg -n 'https?://' docs/dashboard-entries.md
rg -n '`[^`]*https?://|https?://[^[:space:]]*(\*\*|`)' docs/dashboard-entries.md
```

I found current URL mentions at lines 15, 87, and 560. I did not find a current dashboard entry with a closing `)`, `]`, comma, semicolon, colon, or period immediately before abutting markup, so this does not appear to corrupt today’s rendered store content.

**Checked And Could Not Fault**
Baseline:

```text
python3 scripts/gen-dashboard.py --self-test        -> 198/198 passed
python3 scripts/check-plan-code.py --self-test      -> 136/136 passed
scratch copy: python3 scripts/check-plan-code.py --mutate . -> OK — delivered scripts mutated: 2 file(s), 59 mutation(s), 0 survivor(s)
```

Live page checksum before and after remained:

```text
d2f8a54bb865953ab12d94a11d010c22ecb46c4f5a131312696998cb0f2ad467
```

I did not run `--mutate .` against the working repo; I ran it against a scratch copy.

The new manifest entries do discriminate via their named cases. I reproduced the added mutations individually; each exited `1` and included the expected `[FAIL]` case.

Sandbox/real-file audit: `run_suite` executes copied scripts with `cwd=d`, fake-`HOME` self-test produced no files under the fake home, and scratch mutation did not change the live dashboard checksum. I did not find a manifest entry that can still write to the real dashboard, `STORE_DEFAULT`, or a relative path resolved against the real repo cwd.

The `strong=False` equivalent-mutant argument is sound for the recursive call as written: `close = s.find("**", i + 2)` chooses the first closing delimiter, so the recursive `body` cannot contain `**`. I tried representative bodies and found no output difference between `strong=True` and `strong=False` for the recursive body.

H1/main wiring: deleting the outer `with _write_sandbox()` in `main()` was caught in a scratch copy. It failed both `the suite never writes to the REAL dashboard path` and `...and it restores the value IN FORCE, not a copy of the real path`.
