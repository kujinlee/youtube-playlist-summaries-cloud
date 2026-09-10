<!-- codex-review: model=gpt-5.5 -->

Reviewed SHA: `e4d88eb086738951976a0fc1f09edc5d423c7db2` from an extracted `git archive` at `/tmp/r3-e4d88eb0-review`. `brief-compose.py --self-test` passed `72/72`; `gen-backlog-page.py --self-test` passed `86/86`.

**Findings**

Blocking — [scripts/brief-compose.py](/tmp/r3-e4d88eb0-review/scripts/brief-compose.py:193)

Quote: `while i < n and css[i] != quote:`

Exact input:
```css
.bad{content:"unterminated
}.c{background:var(--structure-bg)}
```

Observed: `strip_css_comments()` returned `.bad{content:"                                                `, `vars_read_anywhere()` returned `set()`, and a composed live-toggle page using that CSS was accepted.

Expected: a newline inside an unterminated CSS string is a bad-string recovery point; the later `.c{background:var(--structure-bg)}` rule is real CSS and should remain visible to the guard. The composed page should be refused for missing `--structure-bg`.

Blocking — [scripts/brief-compose.py](/tmp/r3-e4d88eb0-review/scripts/brief-compose.py:151)

Quote:
```python
out += re.findall(r'\sstyle\s*=\s*"([^"]*)"', document, re.I)
out += re.findall(r"\sstyle\s*=\s*'([^']*)'", document, re.I)
```

Exact input:
```html
<title>x</title><style>:root[data-theme="dark"]{--ink:#eee;--bg:#111}:root[data-theme="light"]{--bg:#fff;--card:#fff;--defect:#fff;--good:#fff;--ink:#fff;--ink-faint:#fff;--ink-soft:#fff;--rule:#fff;--structure:#fff;--structure-br:#fff;}</style><div style=background:var(--structure-bg)>x</div>
```
with the commit’s real `page_chrome.theme_control()` and `chrome_script()` appended.

Observed: `css_of()` returned `""` for the unquoted inline style, and `compose()` accepted.

Expected: HTML accepts the unquoted `style` attribute; verified with `HTMLParser`, which parsed `('style', 'background:var(--structure-bg)')`. The browser-applied `var(--structure-bg)` read should be counted and the live-toggle page refused.

High — [scripts/brief-compose.py](/tmp/r3-e4d88eb0-review/scripts/brief-compose.py:150)

Quote: `out = re.findall(r"<style[^>]*>(.*?)</style>", document, re.S | re.I)`

Exact inputs:
```html
<div data-example='<style>.c{background:var(--structure-bg)}</style>'>x</div>
```
```html
<script>const x = "<style>.c{background:var(--structure-bg)}</style>";</script>
```

Observed: `css_of()` extracted `.c{background:var(--structure-bg)}` from both non-CSS contexts, and `compose()` refused with missing `--structure-bg`.

Expected: neither attribute text nor script raw text is a stylesheet. Verified with `HTMLParser`: the attribute case produced only a `div` tag; the script case produced only a `script` tag. The page should compose because no real CSS reads `--structure-bg`.

Medium — [scripts/brief-compose.py](/tmp/r3-e4d88eb0-review/scripts/brief-compose.py:222)

Quote:
```python
if css[j] == "{":
    depth += 1
elif css[j] == "}":
    depth -= 1
```

Exact input:
```css
@media (prefers-color-scheme: light){[data-x="{"]{color:red}}:root[data-theme="light"]{--structure-bg:#fff}
```

Observed: `strip_scheme_media(strip_css_comments(input))` returned `""`; `light_palette_tokens(input)` returned `set()`. A composed page with that real later light declaration plus `.c{background:var(--structure-bg)}` was refused.

Expected: the `{` inside the preserved attribute-selector string is selector text, not a block opener. The media block should be stripped without consuming the following real `:root[data-theme="light"]{--structure-bg:#fff}` declaration.

`gen-backlog-page.py` token check: no finding. The four new tokens `--bg`, `--rule`, `--structure`, `--defect` are present and consistently mapped in `:root`, system-dark `:root`, explicit dark, and explicit light blocks.

NOT CONVERGED.
