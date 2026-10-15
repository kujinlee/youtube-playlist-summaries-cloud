<!-- codex-review: model=gpt-6.1-sol -->

## Blocking

None established against the **exact 1,400-shape measurement**. Its corpus was unavailable for replay; that verification failed, as recorded under CANNOT RUN. The broader inference that the predicate now fails only noisily is refuted below.

## High

**H1 — Spaced nested quotes hide a live figure.**

`scripts/check-withdrawal.py`, `QUOTE_LINE` and `paragraph_ends_between`:

```python
QUOTE_LINE = re.compile(r"[ \t]{0,3}(>+)")
```

```python
if BLANK_OR_BLOCK.match(nxt[nq.end():].lstrip(" \t")):
    return True
```

Input:

```markdown
> > the count was `wrong:
> > ---
> > holds 1,414 anchors today`
```

Both GFM parsers render a nested blockquote containing a heading followed by a separate paragraph, with **no code span**. The predicate removes only the first spaced quote marker, fails to recognize the inner setext boundary, and returns `False`.

`mask_inline_code` produces:

```text
> > the count was `wrong:x>x>x---x>x>xholdsx1,414xanchorsxtoday`
```

`history_marker(..., figure_at=text.index("1,414"), masked=...)` returns **`'was '`**, incorrectly exempting the separate live claim.

**Ran:** Python 3.12.9 from `/tmp/cmvenv/bin/python`, importing the shipped functions and rendering this exact input through `cmarkgfm.github_flavored_markdown_to_html` and `MarkdownIt("gfm-like").disable("linkify").render`.

**H2 — The new table lookahead is unreachable inside a quote.**

`scripts/check-withdrawal.py`, `paragraph_ends_between`:

```python
if nq:
```

followed by the mutually exclusive:

```python
elif "|" in nxt and nxt_end != -1:
```

Input:

```markdown
> the count was `wrong:
> plain
> | h |
> |---|
> holds 1,414 anchors today`
```

Both GFM oracles render a paragraph followed by a table, with **no code span**. Every quoted line enters `if nq`, so the table lookahead never examines its header and delimiter. The mask replaces the intervening whitespace and `history_marker` returns **`'was '`**, suppressing the table’s live figure.

**Ran:** The same Python 3.12 two-oracle harness, including direct mask and history-marker calls on this exact five-line input.

**H3 — Quote state disappears after one lazy-continuation line.**

`scripts/check-withdrawal.py`, `paragraph_ends_between`:

```python
pq, nq = QUOTE_LINE.match(prev), QUOTE_LINE.match(nxt)
```

```python
elif pq:
    if ANY_BLOCK_ISH.match(nxt):
        return True
```

Input:

```markdown
> the count was `wrong:
plain
* 
holds 1,414 anchors today`
```

Both parsers render a blockquote, an empty list item, and a separate final paragraph, with **no code span**. After `plain`, the immediately preceding line has no quote marker. The empty `* ` therefore reaches the fresh-paragraph classifier, which permits it, rather than the quote-continuation classifier, which rejects it.

The mask crosses the actual block boundary, and `history_marker` returns **`'was '`** instead of `''`.

**Ran:** The same Python 3.12 two-oracle harness on this exact four-line input.

Across an additional **130 generated shapes**, both oracles agreed on every input: **88 lenient disagreements, 42 agreements, zero noisy disagreements**. The corpus comprised LF/CRLF variants of:

- Spaced quote depths 2–5 × seven block markers: **56 lenient**.
- One–five lazy prose lines × five following markers: **20 lenient, 30 agreements**.
- Four quote/list prefixes × zero–two intervening prose lines × table triples: **12 lenient, 12 agreements**.

These figures describe this new corpus, not a recomputation of the original 1,400.

## Medium

None established.

## Low

None newly established.

## Checked and found SOUND

- **Scope and cleanliness:** HEAD was `3b49db97`; `git status --short` was empty. `git diff --shortstat 54625c75..3b49db97 -- scripts/` reproduced **3 files, 349 insertions, 29 deletions**.
- **Manifest arithmetic:** Python 3.12 AST extraction of `EXPECTED_MUTATIONS` and independent JSON enumeration reproduced **62 manifests / 1,538 entries / declared sum 1,538**, with **no per-file mismatches**.
- **Requested suites:** Executed every `--self-test` under `python3.12`; all returned **0**:

  | Script | Result |
  |---|---:|
  | `find-claim.py` | 86/86 |
  | `check-withdrawal.py` | 139/139 |
  | `check-provenance.py` | 155/155 |
  | `check-plan-code.py` | 237/237 |
  | `codex-frontier-model.py` | 51/51 |

- **Binding:** `python3.12 scripts/check-plan-code.py --binding` returned **0**, reporting **1,546 anchors / 1,538 entries**.
- **New mutations:** Applied the seven added manifest entries only in a temporary scripts copy. Every mutation changed its target, passed `ast.parse`, returned **1**, and emitted its expected canonical `[FAIL] …: got … want …` line without a traceback. Initial isolated-file attempts crashed because dependencies were absent; those attempts were discarded as invalid evidence.
- **Oracle controls:** Both parsers recognized a genuine multiline code span, rejected a span across `***`, and retained a span across inline `<span>` where the conservative predicate declined it. This checked agreement, lenient detection, and noisy detection.
- **CRLF boundaries:** Direct history-marker probes exercised all five `SENTENCE_SPLIT` alternatives—punctuation, paragraph break, colon, hard break, and block start—and returned `''` as expected.
- **Table edge probes:** Tested bare `---`, `|-|`, and header-at-EOF inputs. No crash or lenient disagreement occurred in those probes.
- **Index-derived lambdas:** Examined both replacements; their bounds derive from the actual fixture’s first backtick pair.
- **CI arithmetic:** `gh run list` and `gh run view 37806242477 --json jobs` confirmed all **eight mutation shards plus `mutation-sweep-complete` succeeded** at `bbdb3204`. The overall CI run failed separately at “Review rounds have both halves”; it was not globally green.
- **Backlog #267 amendment:** Read `docs/backlog.md:282`. It honestly acknowledges the previous measurement failure. However, **“SO THE DESIGN QUESTION IS NOW ASKED FROM THE RIGHT PLACE”** still argues beyond the sampled evidence. H1–H3 satisfy its restated failure condition. The exact finite-corpus zero remains unverified, rather than disproved by different inputs.

## CANNOT RUN

**FAILURE — exact 1,400-shape replay.** No executable generator or complete corpus specifying the original marker, indentation, and table populations was located in the reviewed tree or inspected temporary Python files. Consequently, **0 lenient / 132 noisy / 14 oracle exclusions**, and the historical **196 → 12 → 0** progression, were not independently reproduced.

The installed parsers worked. The limitation was the missing measurement corpus, not parser availability.
