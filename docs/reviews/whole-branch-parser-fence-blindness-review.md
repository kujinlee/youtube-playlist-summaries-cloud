# Parser fence blindness — review round 1 (branch `fix-parser-fence-blindness`, 05f63ae6)

**ROUND VERDICT: NOT CONVERGED at dispatch — 1 High, fixed and re-verified. 0 Blocking.**

## Half 1 — Codex (`gpt-5.5`, gate_ran=true)

It ran both suites, parsed the real store, AND ran a fence-blind mutation against the live
store. Its High was found by CONSTRUCTING an input, not by reading — reproduced here before
fixing.

<!-- codex-review: model=gpt-5.5 -->

**Findings**

High: [scripts/check-dashboard-entry.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-dashboard-entry.py:127)

```py
FENCE = re.compile(r"^(?P<ind> {0,3})(?P<ch>`{3,}|~{3,})")
```

and [scripts/check-dashboard-entry.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-dashboard-entry.py:220)

```py
m = FENCE.match(line)
...
if same_char and long_enough:
    fence = None
```

A closing fence with trailing text is accepted as closed. CommonMark only permits spaces after a closing fence. This reproduces the same class of bug: a valid fenced code block can still mint a phantom entry.

Repro I ran:

```md
## 2026-08-28
Title.
```
``` not a CommonMark closing fence
## 2026-08-29
still code
```
After.
```

`parse_entries` returns:

```text
len 2
ids ['2026-08-28/1', '2026-08-29/1']
errors [None, None]
```

That should be one entry. Fix concretely: keep accepting info strings on openers, but when already inside a fence, require the matched fence line’s remaining text to be whitespace only before closing. If you want to unify safely, extract a helper that returns parsed fence marker plus rest; let `_inert_lines` keep its existing comment-first priority and call the helper only after the comment branch.

No Blocking findings. I did not find real-store meaning changed by this branch.

**Attack Answers**

1. Leaving three implementations is defensible only because the consumers answer different questions. `_inert_lines` really does need comment priority above fence state. The unification I would accept is a small fence-token helper used by all three, not precomputed `fenced_lines` reused by `_inert_lines`.

2. Required `_FENCED_LINES = _GATE.fenced_lines` is justified. Optional `_inert_lines` degrades ask rendering; missing `fenced_lines` corrupts entry identity.

3. Edge cases: 0-3 space indentation works; opener info strings mostly work; blockquoted `> ##` does not matter for `BLOCK` because it is not column-0. Closing fence with trailing text is wrong and does matter.

4. The `_inert_lines` vs `fenced_lines` distinction is load-bearing. With `_FENCED_LINES = _GATE._inert_lines`, the prose `<!--` trap returns one entry instead of two. The new parser tests are not vacuous against the two relevant mutations.

5. `same_char` / `long_enough` split is acceptable. It is not a readability win by itself, but it is small and makes two independent rules falsifiable.

**Verification**

Ran:

```text
python3 scripts/gen-dashboard.py --self-test
307/307 passed

python3 scripts/check-dashboard-entry.py --self-test
120/120 passed
13/13 cannot-run cases passed
```

Real store parse:

```text
entries 48
errors 0
last id 2026-09-01/17
```

Fence-blind mutation on the current live store produced the same 48 ids/plain text, because the live store currently has no column-0 `##` inside fenced code.

## Half 2 — Claude

⛔ **REVIEW GAP: claude — author self-review, NOT an independent half.** Same constraint as the
previous round: session instructions forbid spawning a reviewer unless the user asks. Recorded,
not hidden.

**Adjudicating Cx-High (accepted, and it is the strongest finding of the session).** Reproduced
before fixing rather than taking it on trust:

    entries: 2 ids: ['2026-08-28/1', '2026-08-29/1'] errors: [None, None]

The branch's OWN defect survived one shape over. `fenced_lines` closed a fence on any line whose
marker matched, so an annotated inner fence — ```` ``` not a CommonMark closing fence ```` — read
as a closer, the following lines stopped being code, and a phantom entry with a real id appeared
again. That shape is not exotic: it is how anyone quotes markdown inside markdown, which is exactly
what the dashboard skill teaches people to do, and `exemption_reason` already carries a comment
saying so about the fence-LENGTH rule. I ported two of that function's three hard-won rules and
missed the third.

FIXED as `no_trailing_text`, a THIRD separately-anchored decision, with three cases (trailing text
does not close; trailing SPACES do; an opener may carry an info string) and its own mutation.

**Finding C1 (Medium, ACCEPTED AS DEBT, not fixed).** Cx answer 1 is right that three fence-aware
implementations now exist (`exemption_reason`, `_inert_lines`, `fenced_lines`) and that unifying
them needs a fence-TOKEN helper called after `_inert_lines`' comment branch, not a precomputed set.
NOT done here: it changes two heavily-tested functions whose escapes were each paid for in
production, and this branch is already carrying a High fix. ⚠ The honest cost: this branch reduces
the duplication from "two copies, one of them about to become three" to "three copies, one of them
canonical and documented". That is an improvement, not a resolution, and stating it as a resolution
would be the same overclaim the previous PR corrected.

**Finding C2 (process).** The Cx-High is the SECOND time this session that my measurement was
sound and my CORPUS was not. First: a probe over blockquote/indent/fence with no HTML comment,
which shipped an over-rejection that deleted a live entry. Second: fence cases covering character
and length but not trailing text. Both times the code did what I measured; both times I measured
the wrong set. The generalisable form — *enumerate the rule's dimensions from the rule, not from
the examples that came to mind* — is worth more than either fix.

**Cx answers 2, 4, 5 accepted as confirmations**, all three independently checked: the
required/optional asymmetry is justified; the `_inert_lines`-vs-`fenced_lines` mutation is
load-bearing (with `_FENCED_LINES = _GATE._inert_lines` the prose-`<!--` trap returns 1 entry, not
2); the `same_char`/`long_enough` split is small and makes two rules independently falsifiable —
now three.

## Dispositions

| # | Sev | Finding | Disposition |
|---|---|---|---|
| Cx-H | High | a closing fence with trailing text closes the block; phantom entry still minted | **FIXED** — `no_trailing_text`, 3 cases + 1 mutation. Repro now yields 1 entry |
| C1 | Medium | three fence-aware implementations remain | **DEBT, stated not hidden.** Needs a fence-token helper called after the comment branch; touches two functions whose escapes were paid for in production |
| C2 | process | measurement sound, corpus wrong — twice | RECORDED |
| Cx-2/4/5 | — | required/optional asymmetry; mutation load-bearing; split decisions | CONFIRMED, each re-checked independently |

**Re-verification after fixes:** gate 120 -> **123** + 13/13; renderer **307**; store 48
entries / 0 errors / last `2026-09-01/17`; `--mutate .` 7 files, **162 mutations, 0 survivors**.
