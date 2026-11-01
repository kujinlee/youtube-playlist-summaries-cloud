# review-round-cap — round 1 — Claude adversarial half (PR #457, backlog #434)

**Reviewed head `45858d37`** (`45858d37b9e58b1a472f2068d4de551ba0d85f4e`), `git diff origin/master...HEAD`,
in the branch worktree. The worktree was clean at review time (`git status --short` empty).

**Round cap, pre-committed (from the brief):** r1 both halves; r2–r3 one half each; from r4 findings are
FILED unless a BLOCKER.

**The claim to refute:** a Claude verdict cannot be credited to a tree its review did not see, so
`check-review-recorded` is no weaker than with Codex-only verdicts, and the docs state the cap once
without contradiction.

**Result: REFUTED.** The first half of the claim fails end to end (H1). Every finding below is new in
this PR. None is fix-induced, because this is round 1.

## Gates run (foreground)

| Check | Result |
|---|---|
| `python3 scripts/record-review-verdict.py --self-test` | 48/48 passed |
| `python3 scripts/check-review-recorded.py --self-test` | 195/195 passed |
| End-to-end repro, `scratchpad/r457/repro.py` (outside the repo) | **false green, exit 0** (H1) |

## Findings

### H1 · High · `scripts/record-review-verdict.py:129` (`dirty={}`), docstring `:41-44`. This reopens the r11 Blocking that `check-review-recorded.tail_candidates` exists to close

`claude_record` hard-codes `dirty={}` without observing anything. `codex-review.reviewed_state` says
what `{}` means: *"`{}` keeps its real meaning: the tree WAS clean."* This tool asserts that meaning
without measuring it. The docstring only argues the case where the reviewer's uncommitted fixes are
**committed** later. It says that case gives a false red, and that holds. The case it does not
consider is fixes that are **reverted**. That is the r11 Blocking verbatim: *"a file reviewed as
`GOOD`, reverted, merged as `BAD`, exit 0"*. `tail_candidates` unions in `reviewed`'s keys
specifically to catch it. With `dirty={}` the union is empty, so the reverted path is never compared.

**Concrete input, run end to end** (a fresh repo, the real `main()` and the real `round_tails` /
`tail_verdict`):

1. base `lib/a.ts = v1`. Commit `BAD` at h1.
2. Put `GOOD` in the working tree, uncommitted. This is Q4(b) answer 2, *"keep the last fixes
   uncommitted so the reviewer sees what ships — the documented way"*.
3. File a Claude review naming `h1[:8]` and stating `CONVERGED`. Run
   `record-review-verdict --review-id x-r1-claude --head h1`, which gives **rc 0**.
4. `git checkout -- lib/a.ts`, which discards the fix. Commit only the review and the verdict.
5. The gate returns `(0, 'the final tree was in the tree handed to x-r1-claude.verdict.json')`, and
   the merged file is `BAD`.

The same sequence under `codex-review.py` records `dirty: {"lib/a.ts": "<entry of GOOD>"}` and goes
red. So `check-review-recorded` **is** weaker with this producer than with Codex-only verdicts.

**Siblings.** The brief also asked about "a run in a dirty tree", and that is this same finding. The
other dirty-tree variant, fixes committed afterwards, gives the false red the docstring describes.

**Fix direction.** Call `_cx.reviewed_state(root)` and refuse unless its head equals the resolved
`--head`. Then record the overlay it observed (or refuse when the overlay is non-empty) instead of a
literal `{}`. A `None` overlay must stay `None`, which `classify_verdict` already treats as UNUSABLE.
This brief has the half run the tool from its own worktree, so that observation is available.
⚠ A bound remains and should be stated: the observation is taken at record time, not review time.

### M1 · Medium · `scripts/record-review-verdict.py:38-40, 94`. "The review must NAME that commit" is the coordinator's statement repeated, not independent evidence

The coordinator's brief tells the half which sha to write. This round's dispatch said *"Say in its
text that you reviewed head 45858d37"*, and `review-method.md` Q2 step 4 says *"the brief asks the
half to name that sha"*. So the check at `:94` verifies that the coordinator's own instruction was
obeyed. It does not verify that the reviewer's tree was at that commit. The docstring's defence
*"the coordinator cannot record a head the review document does not itself claim to have seen"*
holds only against recording a head **later** than the brief. It does nothing against a brief whose
sha was wrong in the first place, for example a worktree that was at another commit or was moved
mid-review.

The rule also accepts **any** hex token anywhere in the file. Here is a concrete input that is
accepted (`review_problem` returns `None`):

    > Brief: say you reviewed 45858d37. My tree was at 12f88183.
    The brief asks for CONVERGED or NOT CONVERGED.

The text names the head only to dispute it, and it states no verdict of its own. The H1 fix, which
observes HEAD at record time, is the remedy for the first half of this finding. The second half
(M1b) is separate: `VERDICT_WORD` matches `CONVERGED` inside "NOT CONVERGED", inside a quoted brief,
and inside prose. An input like *"I could not tell whether it CONVERGED"* passes as a verdict.
Anchoring to a `## Verdict` heading, or to a final line, would make that check mean what
`:49-51` says.

### M2 · Medium · `docs/review-method.md` Q4c, BLOCKER definition. It is not decidable as written, and round 4+ has no terminal bound

*"Wrong in a way **nothing else catches** — not CI, not another gate."* At round 4+ every finding
the reviewer raised is, by construction, one that CI and the gates did not catch on the reviewed
tree. If they had caught it, the branch would already be red. So the test the coordinator must apply
is a prediction about a gate that has not run, and it passes almost everything. "Ordinary edit or
defect" adds nothing a coordinator can check.

The table says round 4+ runs *"only to re-check a BLOCKER's fix"*. Each re-check may raise a new
BLOCKER, which is folded and then re-checked. Nothing bounds that chain, so the endless folding the
cap exists to stop is reopened through the exception.

**Fix direction.** Make the test observable. One option: "it reproduces as a wrong result on an input
this PR's own suite and CI do not exercise, **and** the reviewer supplies that input". Then bound the
exception, for example "at most one BLOCKER re-check round; a BLOCKER found in it goes to the human".

### M3 · Medium · `docs/review-method.md` Q4c ("Tree identity (b) still applies to the round-3 fold: its cheaper answers 1–3 come before a round 4"). This interacts with H1

Answer 2 is to keep fixes uncommitted for the final reviewer. Under the cap, round 3 is **one** half.
When that half is Claude, `dirty={}` makes answer 2 structurally unavailable. Committing the held
fixes always reads as UNSEEN, which is a false red. Reverting them is the H1 false green. So the cap
sends the round-3 fold to answer 2, and the new producer cannot honour it. Fixing H1 (recording the
observed overlay) resolves this too. Until then Q4c should say that answer 2 needs a Codex final
half.

### L1 · Low · docs that still state an unbounded loop

- `docs/dev-process.md:23` says *"dual adversarial review to convergence is the quality gate"*, and
  the Phase table two screens down now says "to convergence or the round cap".
- `docs/process-checklists.md:18` says *"iterate to convergence"*.
- `:26` says *"the plan gate is **convergence**"*.

None of these points to Q4c.

**How I searched:** grep over `docs/*.md`, `.claude/skills`, `.agents/skills` and `.claude/commands`
for `convergence|converge\b|repeat until|keep going until|another round is mandatory`. These three
are the only unqualified hits outside history documents (`roadmap-to-launch.md`,
`process-rationale.md`). The skills directories had none.

### L2 · Low · `docs/plugins.md:119`. The inserted clause moved the existing "because"

The text now reads *"…from round 4 findings are FILED unless a BLOCKER (…), because a concurrent pair
never reviews the FIXES"*. The "because" justified alternation and now seems to justify the cap. Move
the cap clause after the sentence.

### L3 · Low · `scripts/record-review-verdict.py:159-178`. Symlinks are followed on both paths

`rpath` is opened through a symlink, so a `docs/reviews/claude/<id>.md` link to any file that names
the head is accepted. `vpath`'s existence test is `os.path.exists`, which is False for a **dangling**
symlink. `write_verdict` then writes through the link, outside `docs/reviews/verdicts/`. Both need a
deliberate act, and Codex's `write_verdict` has the same property. `os.path.lexists` together with
an `islink` refusal would close both.

## Probes that did NOT break it

- **Ambiguous 7-character prefix.** `rev-parse --verify` refuses an ambiguous short sha, so nothing is
  written. The text-side rule compares tokens against the FULL resolved sha, so it cannot match two
  objects.
- **Moving a verdict forward to a later commit.** This is refused unless the review text names the
  later sha. Your own case at `:365-369` covers it, and an M1-style text is needed to defeat it.
- **Review-id in another subject's namespace.** Ids are a single segment (`segment_problem`), and an
  existing verdict is never overwritten. An old subject's head is an ancestor of the base, so every
  branch path reads as changed after it: a false red, never a false green.
- **A head off the branch.** `round_tails` skips a head that is not an ancestor of HEAD and counts it
  as unusable.
- **A Codex half and a Claude half in the same round.** Each produces its own verdict file, and the
  gate takes any clean tail. Neither weakens the other.
- **Review edited after the fact.** Nothing ties the verdict to the review's bytes, but the same is
  true of a Codex verdict, and the docstring states this bound (`:55-57`). Not filed.
- **`dirty: {}` as read by `check-review-recorded`.** It is classified USABLE and read as an empty
  overlay, exactly as the docstring says. The defect is what the empty value **asserts** (H1), not
  how the checker reads it.

## Verdict

NOT CONVERGED. H1 is a reproduced false green that reopens a previously fixed Blocking. M1–M3 should
be settled in the same fold, because the H1 fix changes all three.
