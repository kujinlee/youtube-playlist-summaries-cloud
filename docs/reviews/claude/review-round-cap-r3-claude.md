Reviewed head: e80a2c1e265b38d35e1e9b762e31019f45675047

# review-round-cap — round 3 — Claude half (adversarial)

Scope: `git diff 08597dfb..e80a2c1e` (the r2 fold: the Markdown parser replaced by fixed positions), read
against the r1/r2 coordinator documents and `docs/reviews/codex/review-round-cap-r2-codex.md`. Head verified
with `git rev-parse HEAD` in the worktree before this line was written, not copied from the brief.

Claim under attack: *no Claude verdict can be credited to a tree its review did not see (bound: #435); a
verdict word cannot be misread; the r1 guarantees (TREE MOVED, observed overlay, symlinks, no overwrite)
still hold; Q4c terminates.*

## What was run

- `python3 scripts/record-review-verdict.py --self-test` (foreground): **98/98 passed**.
- `python3 scripts/check-review-recorded.py --self-test` (foreground): **195/195 passed**.
- A probe script calling `declared_head`, `review_verdict` and `review_problem` directly with each hostile
  input below (outputs quoted).
- Case-name diff of the suite, `08597dfb` vs `e80a2c1e`; diff of `scripts/mutations/record-review-verdict.json`.
- Grep of `scripts/*.py` for any consumer of the record's `verdict` field.

## Probes — all fail CLOSED or read correctly

| Input | Observed |
|---|---|
| BOM (`U+FEFF`) before `Reviewed head:` | `head=None` → `HEAD NOT NAMED` |
| zero-width space after the sha | `HEAD NOT NAMED` |
| zero-width space inside `CONVERGED` | `NO VERDICT` |
| CRLF throughout | head and `CONVERGED` read; accepted (correct) |
| trailing NUL line / NUL on the verdict line | `NO VERDICT` (NUL is not whitespace to `str.strip`) |
| whitespace-only tail lines (`\t`, `\f`, `\v`, `\x1c`, `\x85`) after `VERDICT: NOT CONVERGED` | `NOT CONVERGED` (correct) |
| `VERDICT: NOT CONVERGED\rVERDICT: CONVERGED` (lone CR) | `NO VERDICT` — only a trailing `\r` is dropped |
| fullwidth colon | `NO VERDICT` |
| indented-code verdict line | `NO VERDICT` |
| tree/blob sha of the right shape on line 1 | cannot equal `--head`, which is resolved `^{commit}` → `HEAD MISMATCH` |
| 64-hex on line 1 in a SHA-1 repo | `HEAD MISMATCH` against the 40-hex head (and a 64-hex `--head` fails `resolve_head`) |

Sibling search: every Unicode separator Python's `splitlines` honours that `split("\n")` does not was tried in
the tail (`\x1c`, `\x85`, ` `); none moves the last line. TREE MOVED, the `dirty` overlay pass-through
(`None` stays `None`, consumed as UNUSABLE by `check-review-recorded.classify_verdict`), symlink refusal and
no-overwrite are untouched by this diff and their cases are still in the 98.

## Manifest and cases

19 → 21 mutations. The r1 entries were retargeted, not deleted: abbreviation (`MIN_HEX` → `{7,40}`), another
commit (`declared != head`), prefix/quote (`fullmatch` → `search`), any-line declaration, verdict prefix
(`fullmatch` → `match`), verdict anywhere. One r1 entry has no successor: *two Verdict headings that disagree*.
That rule has no subject now — only one line is read — so its retirement is honest. The 13 case names that
disappeared all name the deleted parser (fence state, bold line, heading-then-word, ambiguous resolver); each
property they defended is now defended by a position case (*the declaration form anywhere BUT the first line*,
*a head named only inside a QUOTED line*, *a verdict line ABOVE the last line*). No r1 guarantee lost a case.

## Findings

**F1 · Low · FILE · `scripts/record-review-verdict.py:117-122` (`review_verdict`).** An UNCLOSED construct at end
of file still hides the verdict from a human while the tool reads it: `...VERDICT: NOT CONVERGED\n<!--\nVERDICT:
CONVERGED\n` gives `review_verdict = CONVERGED`; the same with an unclosed `` ``` `` fence. Rendered, a reader
sees `NOT CONVERGED` (or the line in a code block). The r2 coordinator doc's *"a file ending in a fence or in an
HTML comment states no verdict"* is true only of a CLOSED one. **Why not a BLOCKER:** no consumer reads the
record's `verdict` field (grep of `scripts/*.py`: zero readers outside the producer; `check-review-recorded`
reads `gate_ran`/`head`/`dirty` only), so no gate goes green on it — test 1 of Q4c fails. It becomes live the
day a consumer reads `verdict`. Fix when it does: refuse a body with an odd count of `<!--`/`-->` or of fence
openers after the last visible verdict, or narrow the coordinator doc's sentence to "a closed fence or comment".

**F2 · Low · FILE · `scripts/record-review-verdict.py:46-48` (docstring, "the filed review must DECLARE that
commit") and `docs/review-method.md` Q2 step 4.** The brief now hands the reviewer the exact line to write,
full sha included (this round's brief did). So line 1 is an ECHO of the coordinator's own statement, and the
check `declared == --head` is a consistency check between two coordinator statements — it cannot show the
reviewer looked at that commit. The thing that does bind the verdict to a tree is TREE MOVED plus the observed
overlay at record time, which is exactly #435's bound. No false green follows (a mismatched echo still fails
`HEAD MISMATCH` or `TREE MOVED`), but the "NOT A RUBBER STAMP" list presents the declaration as independent
evidence. Fix: one sentence saying the declaration catches a wrong `--head` or a review filed for another
round, not what the reviewer read; or have the brief ask the reviewer to run `git rev-parse HEAD` and write
its output.

No BLOCKER. Nothing found refutes the claim within its stated bound: every positional misread I could build
fails closed for the head, and the only verdict misread (F1) reaches no gate. Q4c terminates: row 5 is the last
ordinary round and row 6+ is "never"; X-n1's HOLD makes an r5 BLOCKER stop rather than loop.

VERDICT: CONVERGED
