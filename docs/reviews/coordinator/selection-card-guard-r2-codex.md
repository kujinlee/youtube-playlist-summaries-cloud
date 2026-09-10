# Codex adversarial review — the selection-card guard, round 2

**Subject:** commit `71f449a8` — the r1 fold of the guard. **Reviewer:** `codex exec` via
`scripts/codex-review.py`, model `gpt-5.5`. **Verdict file:**
`docs/reviews/verdicts/selection-card-guard-r2-codex.verdict.json` (`gate_ran=true`).

**1 Blocking, 2 High, 2 Medium, 2 Low, plus three surviving mutations. All taken.**

Its Blocking is a class worth naming: **the shell mutated the evidence before the checker saw it.**
`INPUT=$(cat)` strips NUL bytes, so a payload the checker correctly calls CANNOT RUN arrived as
valid JSON — measured `direct=2 hook=0`. Its High is the same root cause: the detector reported
through stdout, so a `python3` that prints a banner made the skip test fail and the hook rendered
the §19 refusal panel over a *Bash* payload. Both are closed by one repair — the payload never
enters a shell variable, and the verdict travels by exit code.

It also caught `MAX_OPTIONS` shaping the advice while enforcing nothing (a five-option card passed
this guard and then failed the tool's own schema), and two stale counts I had embedded in prose an
hour earlier.

Everything below the rule is the reviewer's final message verbatim.

---

<!-- codex-review: model=gpt-5.5 -->

**Proof Of Subject**

`git show --stat HEAD`:

```text
commit 71f449a824828d23557aac3f16b8451c1a99b7c4
Author: Kujin Lee <kujinlee@gmail.com>
Date:   Thu Sep 10 13:24:09 2026 -0700

    Fold r1 on the selection-card guard: two Blockings, one from each half

 .claude/hooks/enforce-selection-card.sh            |  36 +-
 docs/portable-practices.md                         |   5 +
 docs/process-rationale.md                          |   8 +-
 .../claude/selection-card-guard-r1-claude.md       | 446 +++++++++++++++++++++
 .../coordinator/selection-card-guard-r1-codex.md   | 137 +++++++
 .../selection-card-guard-r1-codex.verdict.json     |  16 +
 scripts/check-plan-code.py                         |   7 +-
 scripts/check-selection-card.py                    | 173 +++++++-
 scripts/mutations/check-selection-card.json        |  30 +-
 9 files changed, 827 insertions(+), 31 deletions(-)
```

`python3 scripts/check-selection-card.py --self-test | tail -2`:

```text

42/42 passed
```

`grep -n "MAX_OPTIONS\|MIN_DESCRIPTION_DENSE\|RECOMMENDED = " scripts/check-selection-card.py`:

```text
76:RECOMMENDED = re.compile(r"\(\s*recommended\b[^)]*\)[\s*_`]*$", re.I)
84:MIN_DESCRIPTION_DENSE = 15
87:MAX_OPTIONS = 4
153:                   if len(labels) < MAX_OPTIONS else
156:                   f"accepts {MAX_OPTIONS} options at most, so the exit costs you a choice")
169:            floor = MIN_DESCRIPTION if len(desc.split()) > 1 else MIN_DESCRIPTION_DENSE
```

Two exact r1-only lines:

```python
MIN_DESCRIPTION_DENSE = 15
                   f"accepts {MAX_OPTIONS} options at most, so the exit costs you a choice")
```

I also ran:

```text
python3 scripts/check-plan-code.py --mutate .
OK — delivered scripts mutated: 37 file(s), 407 mutation(s), 0 survivor(s)

python3 scripts/check-selftest-counts.py
self-test counts: 33 script(s) declare a count, every one verified by running it
```

**Blocking**

[.claude/hooks/enforce-selection-card.sh](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/hooks/enforce-selection-card.sh:29) loses NUL bytes before both detection and verdict, so the hook can return 0 on stdin the checker itself correctly treats as CANNOT RUN.

Quoted code:

```bash
INPUT=$(cat)
```

```bash
DETECT=$(printf '%s' "$INPUT" | python3 -c '
```

```bash
VERDICT_OUT=$(printf '%s' "$INPUT" | python3 "$REPO_ROOT/scripts/check-selection-card.py" 2>&1)
```

Concrete failing input: a valid good card with a raw NUL inserted after `"questions"` before `:`. Measured:

```text
direct=2 hook=0
direct: CANNOT RUN — Expecting ':' delimiter: line 1 column 13 (char 12). Treat this as NOT CHECKED, never as a pass.
hook:
```

So the hook did not check the bytes it was given; Bash command substitution stripped the NUL, turning unreadable input into valid JSON.

Change: do not store stdin in a shell variable. Write stdin to a temp file, run detector and checker from that same file, and clean it up with `trap`.

**High**

[.claude/hooks/enforce-selection-card.sh](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/hooks/enforce-selection-card.sh:45) blocks a positively identified different tool if `python3` emits stdout before the detector result.

Quoted code:

```bash
print("other" if (name is not None and name != "AskUserQuestion") else "card")
```

```bash
[[ "$DETECT" == "other" ]] && exit 0
```

Concrete failing input:

```json
{"tool_name":"OtherTool","tool_input":{"anything":true}}
```

Measured with a shim `python3` that prints `Python banner` then execs real Python:

```text
Python banner
CANNOT RUN — no `questions` list in the payload. Treat this as NOT CHECKED, never as a pass.
rc=2
```

That should be `rc=0` because `tool_name` is positively another tool.

Change: move hook-mode detection into `check-selection-card.py`, or make the detector emit a machine sentinel and parse only that sentinel line. Bare string equality on all stdout is too brittle.

**High**

[scripts/check-selection-card.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-selection-card.py:102) has a minimum option count but no maximum, even though r1 introduced `MAX_OPTIONS = 4`.

Quoted code:

```python
if len(options) < 3:
```

```python
MAX_OPTIONS = 4
```

Concrete failing input: five options, lettered A-E, one recommendation, final question exit.

Observed:

```text
rc=0
```

But r1’s own premise says `AskUserQuestion` accepts 2-4 options. The guard passes a card the tool schema rejects, so the user gets a schema failure instead of the §19 repair.

Change: add `if len(options) > MAX_OPTIONS:` before the lower-bound check, with a message saying to merge or replace choices because the exit consumes one of four slots.

**Medium**

[scripts/check-selection-card.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-selection-card.py:169) uses whitespace token count as the dense-script detector.

Quoted code:

```python
floor = MIN_DESCRIPTION if len(desc.split()) > 1 else MIN_DESCRIPTION_DENSE
```

Concrete wrong accept:

```text
description: Fast;costs-review.
rc=0 len=18 split=1
```

That is English, not dense CJK; it gets the 15-character floor.

Concrete wrong refuse:

```text
description: 今すぐ出荷する。巻き戻せる がレビューを一回失う。
rc=2 len=25 split=2
```

That is CJK with one ordinary space; it gets the 40-character English floor.

Change: lower the floor only when the description actually contains dense-script characters, e.g. CJK ranges, not merely when `split()` returns one token.

**Medium**

[scripts/check-selection-card.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-selection-card.py:76) both over-accepts and over-refuses anchored recommendation labels.

Quoted code:

```python
RECOMMENDED = re.compile(r"\(\s*recommended\b[^)]*\)[\s*_`]*$", re.I)
```

Wrong refuse:

```text
A — Keep payload_of() (Recommended — preserves payload_of(raw))
rc=2
```

Wrong accept:

```text
A — Delete branch (Recommended against by CI)
rc=0
```

Change: make the suffix grammar explicit: accept `(Recommended)` or `(Recommended — reason)` / `(Recommended: reason)`, allow nested parentheses in the reason, and refuse `Recommended against`.

**Low**

[scripts/check-selection-card.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-selection-card.py:102) gives no concrete exit-option arithmetic for two-option cards because it `continue`s before the exit advice.

Quoted code:

```python
if len(options) < 3:
```

```python
continue
```

Concrete input:

```json
{"questions":[{"header":"H","options":[
  {"label":"A — Ship it (Recommended)","description":"This states why it helps, and what it gives up clearly enough."},
  {"label":"B — Wait","description":"This states why it helps, and what it gives up clearly enough."}
]}]}
```

It reports the “one real choice” problem, but not the exact repair: add `C — I have a question about these`.

Change: include the exit repair in the `<3` branch when there are two options.

**Low**

[docs/portable-practices.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/portable-practices.md:820) is stale after r1.

Quoted code:

```text
(`scripts/check-selection-card.py` + `.claude/hooks/enforce-selection-card.sh`, 24 cases,
6 mutations).
```

The proved tree is `42/42` and manifest 8 entries / 407 delivered mutations.

Change: update §19 to `42 cases, 8 selection-card mutations`, or avoid embedding counts that drift.

**Mutation Survivors I Tried**

Delivered manifest: `407 mutation(s), 0 survivor(s)`.

Extra manual survivors:

```text
SURVIVED: question exit any label rc=0
SURVIVED: letter accepts lowercase rc=0
SURVIVED: recommended dotstar nested rc=0
```

The first is a real coverage gap: replacing the last-option check with “any option contains the question exit” survives because no self-test has the exit in the middle. The lowercase one means `[A-Z]` is not pinned. The dotstar one shows the nested-parentheses behavior is not pinned either.

**Other Branches Checked**

Embedded newlines: valid pretty JSON with newline-containing descriptions passed silently, `rc=0`.

Huge payload: 5 MB valid card passed, `rc=0`, around `0.65s`.

Malformed JSON, empty stdin, JSON array, bare bad card, and broken interpreter behaved as r1 intended:

```text
bare_bad=2
other=0
malformed=2
empty=2
array=2
broken_py=1
```

VERDICT: NOT CONVERGED.
