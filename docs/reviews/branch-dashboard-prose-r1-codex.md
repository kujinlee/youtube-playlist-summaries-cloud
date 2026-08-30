# Branch review — dashboard prose + chart key (PR #178), round 1, Codex half

**Subject:** `a41e045` on `feat/dashboard-prose-readability`.
**Claude half:** [`branch-dashboard-prose-r1-claude.md`](branch-dashboard-prose-r1-claude.md).

**Gate provenance.** `scripts/codex-review.py`, `WRAPPER_RC=0`, via **`gpt-5.5`** after
`gpt-5.6-sol/-terra/-luna` returned HTTP 400. `--out` pointed OUTSIDE the repository and was
promoted here only on success (backlog #68). The reader's live `~/explainers/dashboard.html` was
checksummed before and after the run and is **unchanged** — the reviewer independently confirmed
that `--mutate .` no longer clobbers it, which is this branch's own fix being tested by someone
other than its author.

Everything below the rule is the reviewer's verbatim final message.

---

<!-- codex-review: model=gpt-5.5 -->

**Findings**

**Medium — `scripts/gen-dashboard.py:99` / `scripts/gen-dashboard.py:151` — abbreviations can become the headline and then get cut out of the lede. REPRODUCED.**

Quoted code:

```python
for part in SENTENCE_END.split(text):
    out = f"{out} {part}".strip() if out else part
    if len(out) >= TITLE_FLOOR:
        break
```

and:

```python
head = _first_sentence(first, cap=len(first))
rest = first[len(head):].lstrip() if head else first
if rest:
    paras[0] = rest
```

Input:

```text
Met with Dr. Smith about the release. The rest follows.
```

Observed:

```text
_first_sentence(...) -> "Met with Dr."
_prose(..., drop_headline=True) -> <p class="lede">Smith about the release. The rest follows.</p>
```

Same failure with `Checked e.g. examples in docs...` -> title `Checked e.g.` and lede starts `examples...`. The `TITLE_FLOOR = 12` guard does not protect common abbreviations once the fragment reaches exactly 12 chars.

**Medium — `scripts/gen-dashboard.py:302` / `scripts/gen-dashboard.py:151` — drop-headline removes more than the displayed headline when the first paragraph has no sentence terminator. REPRODUCED.**

Quoted code:

```python
entry["title"] = _first_sentence(" ".join(_first_para))
```

and:

```python
head = _first_sentence(first, cap=len(first))
...
elif len(paras) > 1:
    paras.pop(0)
```

Scenario: first paragraph is long, has no `.?!`, and is followed by another paragraph. `parse_entries` displays a capped title at 110 chars, but `_prose` recomputes with `cap=len(first)` and treats the entire first paragraph as the headline. The fold then drops the whole paragraph, including text the reader never saw in the title.

Observed with a repeated long no-terminator paragraph:

```text
TITLE This opening paragraph has no terminator and keeps explaining the dashboard change in detail This opening…
PROSE <p class="lede">Second paragraph survives.</p>
```

That is not just deduping the visible headline; it deletes hidden prose from the reader’s “What this means” fold.

**Medium — `scripts/gen-dashboard.py:119` / `scripts/check-plan-code.py:302` — the security boundary around allowed URL schemes is not mutation-pinned. REPRODUCED on a temp copy.**

Quoted code:

```python
s = re.sub(r"(https?://[^\s<]+[^\s<.,;:)\]])", r'<a href="\1">\1</a>', s)
```

and:

```python
EXPECTED_MUTATIONS = {
    "scripts/gen-dashboard.py": 32,
```

I changed the autolink regex in a scratch copy to allow `javascript:` as well as `http(s):`. The full `gen-dashboard.py --self-test` still passed `161/161`.

Concrete surviving one-line change:

```python
(https?://...)
```

to:

```python
((?:https?|javascript):...)
```

This branch added high-risk stored-XSS rendering code, but the manifest stayed at 32 existing `gen-dashboard` mutations. The current direct tests prove today’s regex does not autolink `javascript:` / `data:`, but they do not keep that property from regressing.

**Low — `scripts/gen-dashboard.py:117` / `scripts/gen-dashboard.py:118` — overlapping bold/code markup emits invalid nested HTML. REPRODUCED.**

Quoted code:

```python
s = re.sub(r"\*\*(\S(?:[^*]*\S)?)\*\*", r"<strong>\1</strong>", s)
s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
```

Input:

```text
**bold `code** tail`
```

Observed output:

```html
<strong>bold <code>code</strong> tail</code>
```

I did not get script execution or attribute breakout from this, but malformed nesting can make emphasis/code styling leak unpredictably through the fold after a contributor typo.

**Checks Run**

`gen-dashboard.py --self-test`: `161/161 passed`.

`check-plan-code.py --mutate .`: completed with `44 mutation(s), 0 survivor(s)`.

Live dashboard checksum before and after mutation run: unchanged.

Temp-built dashboard fragment: paragraphs, `<strong>`, four prose colour tokens, and legend were present. I did observe one repeated headline in the shipped content, but it is the explicit “keep it when there is nothing else” case for an entry whose plain text is only one paragraph before technical detail.

**Verdict: NOT CONVERGED**
