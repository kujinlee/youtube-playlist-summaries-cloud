<!-- codex-review: model=gpt-5.5 -->

REVIEW GAP: claude — not run; the user judged the change simple and authorised skipping the
round (2026-08-31). One Codex pass ran in place of a full round, and it returned 2 High and
2 Medium, all real. The coordinator did run probes and found a third defect independently,
but no separate Claude adversarial half was written, so this round is HALF a round by
decision, not by accident.

⚠ Weigh accordingly: this repo has a scar for a PR that shipped unreviewed and produced six
defects in the two rounds that followed.
**Blocking**
None found.

**High**
[scripts/gen-dashboard.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-dashboard.py:281): `_ask_block` matches live decisions by question text only, then consumes `live[0]`. If inert indented text appears before the real ask with the same question, the card renders the real options under the inert text and leaves the real ask flattened.

Executed probe:

```html
<div class="ask"><p class="ask-q"><strong>Decide:</strong> Same</p><ul class="opts"><li>real a</li><li>real b</li></ul></div><p class="body"><strong>Decide:</strong> Same
- real a
- real b</p>
```

Gate result for the same full text was one real decision only: `Same -> real a, real b`. Smallest fix: preserve source line/index from `decisions()` or derive inert-aware decision spans once, then render only the paragraph containing that exact opener. Question text is not a stable identity.

[scripts/gen-dashboard.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-dashboard.py:267): two valid `**Decide:**` blocks in one paragraph render only the first in the card. The tray renders both because it loops all `decisions()` at [scripts/gen-dashboard.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-dashboard.py:864), but the card emits one block and drops the rest of the paragraph.

Executed counts: tray `One=1`, tray `Two=1`, card `One=1`, card `Two=0`. Smallest fix: split/render multiple decision blocks from the same paragraph, or make the gate reject multiple openers in one paragraph if that shape is unsupported.

**Medium**
[scripts/gen-dashboard.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-dashboard.py:1021): `settled=_b == "resolved"` is entry-level, not ask-level. Since `badge_of` marks the whole entry resolved when its id is cleared at [scripts/gen-dashboard.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-dashboard.py:528), an entry with two asks and one intended resolution renders both as historical:

```html
<strong>Was decided:</strong> First ask
...
<strong>Was decided:</strong> Second ask
```

The tray shows no asks because `unresolved()` also clears by entry id. Smallest fix: either forbid multiple asks per entry, or introduce per-decision ids/resolution. Without that, the page can claim a live unanswered ask “was decided.”

[scripts/gen-dashboard.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-dashboard.py:287): card option rendering omits the tray’s PR links and live PR-state notes from [scripts/gen-dashboard.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-dashboard.py:870). For live asks, that is a defect: the card says `Decide:` and shows actionable choices, while the tray may say the same `merge PR #N` is stale, missing, or unchecked. Smallest fix: share an option renderer for live card asks and the tray. Historical settled cards can stay simpler if they are clearly non-actionable.

**Low**
[scripts/mutations/gen-dashboard.json](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/mutations/gen-dashboard.json:393): stale mutation anchor. The manifest still looks for `prose = _prose(e["plain"], drop_headline=True)`, but the code now has `settled=_b == "resolved"` at [scripts/gen-dashboard.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-dashboard.py:1021). Executed `python3 scripts/check-plan-code.py --mutate .`; it failed with `anchor NOT FOUND`.

[scripts/gen-dashboard.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/gen-dashboard.py:1899): the settled “does NOT mark a chosen option” test is vacuous. It asserts absence of `"chosen"` and `"you picked"`, strings this renderer never had a path to emit. Add a positive anti-claim check tied to actual option markup if this property matters.

Verified: `python3 scripts/gen-dashboard.py --self-test` passed `285/285`. Mutation run failed: `125 mutation(s), 1 survivor(s)` plus the stale anchor above.

NOT CONVERGED.
