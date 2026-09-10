<!-- codex-review: model=gpt-5.5 -->

Verified SHA: `d4b54cfa7a34a9d9c3954b56c2f700c88164dde1`, extracted with `git archive` into scratch. `python3 scripts/brief-compose.py --self-test` passes `62/62`.

Findings:

1. **Blocking** — `scripts/brief-compose.py:378`
   
   Code:
   ```py
   declares_light = bool(light_palette_tokens(content))
   live_control = declares_light and not page_chrome.missing_palettes(
       content + page_chrome.theme_control())
   ```
   
   Exact input:
   ```html
   <title>x</title><style>:root[data-theme="dark"]{--ink:#eee}:root[data-theme="light"]{}.c{background:var(--card)}</style><div class="c">card</div><button id="chrome-theme" type="button" class="chrome-btn" aria-pressed="false" title="Switch between light and dark"><span class="chrome-ico" aria-hidden="true">◐</span><span class="chrome-lbl">Theme</span></button><script>/* page_chrome.chrome_script() */</script>
   ```
   
   Run result:
   ```text
   declares_light= False
   missing_palettes= []
   COMPOSED 5783 has control True has yps mark True
   ```
   
   What the reader sees: the page ships with a real theme button, but after switching to light under OS-dark, `.c { background: var(--card) }` still reads the shim’s dark `--card` because the light palette is empty. This is the counterexample to deleting the `has_control` arm.

2. **Blocking** — `scripts/brief-compose.py:187`
   
   Code:
   ```py
   css = re.sub(r"@media[^{]*prefers-color-scheme[^{]*\{(?:[^{}]|\{[^{}]*\})*\}", " ", css, flags=re.S)
   ```
   
   Exact input:
   ```html
   <title>x</title><style>:root[data-theme="dark"]{--ink:#eee;--bg:#111}:root[data-theme="light"]{--bg:#fff;--card:#fff;--defect:#fff;--good:#fff;--ink:#fff;--ink-faint:#fff;--ink-soft:#fff;--rule:#fff;--structure:#fff;--structure-br:#fff}@media (prefers-color-scheme: light){@supports (display:grid){:root{--structure-bg:#fff}}}.c{background:var(--structure-bg)}</style><div class="c">x</div><button id="chrome-theme" type="button" class="chrome-btn" aria-pressed="false" title="Switch between light and dark"><span class="chrome-ico" aria-hidden="true">◐</span><span class="chrome-lbl">Theme</span></button><script>/* page_chrome.chrome_script() */</script>
   ```
   
   Run result:
   ```text
   light tokens has target? True
   COMPOSED
   ```
   
   Control run without the nested `@supports` refused `--structure-bg`. What the reader sees: the page composes even though the only `--structure-bg` light value is inside `@media (prefers-color-scheme: light)`, which does not apply in OS-dark plus manually toggled light.

3. **High** — `scripts/brief-compose.py:210`
   
   Code:
   ```py
   return {m.group(1) for m in re.finditer(r"var\(\s*(--[\w-]+)", strip_css_comments(css))}
   ```
   
   Exact input:
   ```html
   <title>x</title><style>:root[data-theme="dark"]{--ink:#eee;--bg:#111}:root[data-theme="light"]{--bg:#fff;--card:#fff;--defect:#fff;--good:#fff;--ink:#fff;--ink-faint:#fff;--ink-soft:#fff;--rule:#fff;--structure:#fff;--structure-br:#fff}</style><p>This doc says var(--structure-bg) in prose.</p><button id="chrome-theme" type="button" class="chrome-btn" aria-pressed="false" title="Switch between light and dark"><span class="chrome-ico" aria-hidden="true">◐</span><span class="chrome-lbl">Theme</span></button><script>/* page_chrome.chrome_script() */</script>
   ```
   
   Run result:
   ```text
   baseline_no_fake_read
   COMPOSED

   body_prose_var
   brief-compose: this page has a WORKING theme toggle, but its light palette does not cover every token the OS-dark shim supplies:
     --structure-bg
   ```
   
   Same false refusal also reproduced with:
   ```css
   .note::before{content:"var(--structure-bg)"}
   .i{background-image:url("data:image/svg+xml,<svg>var(--structure-bg)</svg>")}
   ```
   
   What the reader sees: compose refuses a page because body prose, a CSS string, or a data URI contains text shaped like `var(--structure-bg)`. No browser reads that as a custom property.

4. **High** — `scripts/brief-compose.py:186`
   
   Code:
   ```py
   css = strip_css_comments(fragment_css)
   for m in re.finditer(r':root(\[data-theme="light"\])?\s*\{([^}]*)\}', css):
   ```
   
   Exact input:
   ```html
   <title>x</title><style>.c{background:var(--card)}</style><pre>:root{--ink:#111;--bg:#fff}
   :root[data-theme="light"]{}
   :root[data-theme="dark"]{}</pre>
   ```
   
   Run result:
   ```text
   fake_palette_sample: REFUSED: brief-compose: this page has a WORKING theme toggle, but its light palette does not cover every token the OS-dark shim supplies:
     --card, --good, --ink-faint, --ink-soft, --rule, --structure
   ```
   
   What the reader sees: a page with no real declared palette and no real theme control is refused with a “WORKING theme toggle” diagnosis because code-sample text is counted as CSS.

5. **Medium** — `scripts/brief-compose.py:141`
   
   Code:
   ```py
   return re.sub(r"/\*.*?\*/", " ", css, flags=re.S)
   ```
   
   Exact input:
   ```html
   <title>x</title><style>:root[data-theme="dark"]{--ink:#eee;--bg:#111}:root[data-theme="light"]{--open:"/*";--structure-bg:#fff;--close:"*/";--bg:#fff;--card:#fff;--defect:#fff;--good:#fff;--ink:#fff;--ink-faint:#fff;--ink-soft:#fff;--rule:#fff;--structure:#fff;--structure-br:#fff}.c{background:var(--structure-bg);}</style><div class="c">x</div><button id="chrome-theme" type="button" class="chrome-btn" aria-pressed="false" title="Switch between light and dark"><span class="chrome-ico" aria-hidden="true">◐</span><span class="chrome-lbl">Theme</span></button><script>/* page_chrome.chrome_script() */</script>
   ```
   
   Run result:
   ```text
   stripped: :root[data-theme="dark"]{--ink:#eee;--bg:#111}:root[data-theme="light"]{--open:" ";--bg:#fff;--card:#fff;--defect:#fff;--good:#fff;--ink:#fff;--ink-faint:#fff;--ink-soft:#fff;--rule:#fff;--structure:#fff;--structure-br:#fff;}.c{background:var(--structure-bg);}
   target in light tokens? False
   REFUSED:
     --structure-bg
   ```
   
   What the reader sees: a valid light declaration is erased because `/*` and `*/` occurred inside CSS strings, so compose falsely refuses the page.

NOT CONVERGED.
