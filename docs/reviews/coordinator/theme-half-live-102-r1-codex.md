<!-- codex-review: model=gpt-5.5 -->

**Findings**

**Blocking** — [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:125)

Quoted code:

```python
def referenced_vars(css: str) -> set[str]:
    """Custom properties the CSS reads with NO inline fallback — `var(--x)`, not `var(--x, y)`."""
    return {m.group(1) for m in re.finditer(r"var\(\s*(--[\w-]+)\s*\)", css)}
```

and:

```python
read = referenced_vars(fragment_css + "\n" + also_read)
missing = sorted((shim_dark_tokens() & read) - light_palette_tokens(fragment_css))
```

Trigger:

```html
<title>x</title>
<style>
:root[data-theme="light"]{--ink:#111;--bg:#fff}
:root[data-theme="dark"]{--ink:#eee;--bg:#111}
.c{background:var(--card,#fff)}
</style>
<button id="chrome-theme" ...>...</button>
<script>/* real page_chrome.chrome_script() */</script>
<div class="c">x</div>
```

This composes. `referenced_vars()` returns no `--card` because the `var()` has a fallback. But the fallback is irrelevant here: the shim defines `--card` in OS-dark mode, so `var(--card,#fff)` reads the shim’s dark `--card`, not `#fff`.

Reader sees a live light-mode page whose `.c` background is still the dark shim card color. This is the original half-live failure through a slightly different CSS spelling. The self-test actively pins this bug:

```python
case("referenced_vars ignores names that carry an inline fallback",
     referenced_vars("a{color:var(--x)}b{color:var(--y, #fff)}") == {"--x"})
```

That expectation is valid for `assert_shimmed()`, but not for `assert_theme_complete()`.

**Blocking** — [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:302)

Quoted code:

```python
head, body = content.split("</style>", 1)
...
assert_theme_complete(head, live_control, css + "\n" + page_chrome.chrome_css())
...
styled = (head + SHIM + "\n/* ---- Ask tray, extracted verbatim ---- */\n" + css
          + "\n" + chrome_css + "\n</style>")
```

Trigger:

```html
<title>x</title>
<style>
:root[data-theme="light"]{--ink:#111;--bg:#fff}
:root[data-theme="dark"]{--ink:#eee;--bg:#111}
</style>
<style>
.c{background:var(--card)}
</style>
<button id="chrome-theme" ...>...</button>
<script>/* real page_chrome.chrome_script() */</script>
<div class="c">x</div>
```

This composes. The second `<style>` survives in `body` and the browser applies it, but `assert_theme_complete()` only scans `head`, meaning only the text before the first `</style>`.

Same fail-open for inline style:

```html
<div style="background:var(--card)">x</div>
```

Reader sees the composed page with a working theme control; in OS-dark plus page-light, the body or inline element reads the shim’s dark `--card` because no light value exists. The guard checked a smaller CSS set than the browser actually received.

**High** — [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:158)

Quoted code:

```python
for m in re.finditer(r':root(\[data-theme="light"\])?\s*\{([^}]*)\}', fragment_css):
    out |= {n for n in re.findall(r"(--[\w-]+)\s*:", m.group(2))}
```

Trigger:

```html
<style>
:root[data-theme="light"]{--ink:#111;--bg:#fff}
:root[data-theme="dark"]{--ink:#eee;--bg:#111}
@media (prefers-color-scheme: light){:root{--card:#fff}}
.c{background:var(--card)}
</style>
<button id="chrome-theme" ...>...</button>
<script>/* real page_chrome.chrome_script() */</script>
```

This composes. `light_palette_tokens()` counts `--card` because it sees `:root{--card:#fff}` without understanding that it is inside `@media (prefers-color-scheme: light)`. On the measured failure path, OS is dark and the page is toggled to light, so that media block does not apply. The shim’s OS-dark `html { --card: ... }` still supplies the value.

Reader sees a live light-mode toggle with `.c` still painted from the dark shim card token.

**Medium** — [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:308), [scripts/page_chrome.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/page_chrome.py:73)

Quoted code:

```python
live_control = page_chrome.has_control(content) or not page_chrome.missing_palettes(
    content + page_chrome.theme_control())
```

and:

```python
def has_control(page: str) -> bool:
    ...
    return 'id="chrome-theme"' in page
```

Trigger:

```html
<title>x</title>
<style>
:root[data-theme="light"]{--ink:#111;--bg:#fff}
.c{background:var(--card)}
/* id="chrome-theme" */
</style>
<div>no button</div>
```

This is checked as a live control because `has_control()` is a substring search. There is no rendered button and no live control. The new guard raises:

```text
brief-compose: this page has a WORKING theme toggle...
```

Reader/author sees a compose refusal for a page with no theme button at all. A later `chrome_for()` path may also be confused by the same predicate, but the new code specifically emits the wrong half-live diagnosis first.

**Low** — [scripts/brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/brief-compose.py:141)

Quoted code:

```python
m = re.search(r"@media \(prefers-color-scheme: dark\)\s*\{\s*html\s*\{(.*?)\}", src, re.S)
```

Trigger against the parser:

```css
@media (prefers-color-scheme: dark) {
  html { /* } */ --bg:#000; --ink:#fff; }
}
```

`shim_dark_tokens()` returns an empty set instead of `{"--bg", "--ink"}`. The non-greedy `(.*?)\}` stops at the brace in the comment. Because the regex found a match, it does not take the fail-loud `if not m:` path.

Reader sees nothing immediately with today’s exact `SHIM`, but the “read from the shim itself” invariant is brittle: a harmless comment or future nested syntax can make the half-live guard silently compare against an empty or truncated token set.

Verdict: **NOT CONVERGED**.
