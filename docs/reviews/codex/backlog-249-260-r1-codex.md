<!-- codex-review: model=gpt-6.1-sol -->

The branch’s closure claims do not hold at HEAD `31e2ba84`. I found one High, eight Medium, and two Low findings. No Blocking finding. The worktree is unchanged.

1. **High — `find-claim` confidently reports absence after skipping the subject.**  
   [search_files](/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/fdb027d3-253e-4489-98fc-63b857540d00/scratchpad/wt-backlog/scripts/find-claim.py:209) silently skips read and decoding failures. I searched a directory containing:
   - `control.md`: `known control`
   - `claim.md`: bytes `live claim\xff`

   Searching for `live claim` with control `known control` returned **rc=0**, “absent … so the search worked,” and “2 file(s) searched.” The claim file was never searched successfully. A control in another file cannot establish complete coverage. This directly defeats #258’s central assurance.

2. **Medium — withdrawal signatures cannot match common bolded figures, even in identical text.**  
   [signature_of](/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/fdb027d3-253e-4489-98fc-63b857540d00/scratchpad/wt-backlog/scripts/check-withdrawal.py:114) splits around the number and inserts whitespace at a non-word boundary:
   ```text
   source:    the sweep holds **1,414 anchors** today
   signature: holds ** 1,414 anchors** today
   ```
   The signature finds **zero matches in its own source line**. Driving `main --strict` with a correction to `1,416` and an identical surviving old sentence returned **rc=0**, “none … survives.” This is ordinary backlog formatting, beyond the documented limitation concerning reworded neighbors.

3. **Medium — every repeated withdrawal match receives the first occurrence’s history window.**  
   [The caller](/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/fdb027d3-253e-4489-98fc-63b857540d00/scratchpad/wt-backlog/scripts/check-withdrawal.py:496) uses `text.find(hit.text)` instead of this match’s offset. I placed an old claim beside `CORRECTED`, then repeated it after more than 500 characters of padding without any history marker. **`--strict` returned rc=0**: the live second occurrence inherited the first occurrence’s exemption.

4. **Medium — the replacement prong suppresses unrelated live claims.**  
   [is_history_context](/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/fdb027d3-253e-4489-98fc-63b857540d00/scratchpad/wt-backlog/scripts/check-withdrawal.py:177) treats mere proximity to a replacement number as a correction. This survivor passed `main --strict`:
   ```text
   the sweep holds 1,414 anchors today. Another suite holds 1,416 tests.
   ```
   The old count remains asserted; the second number measures something else. The seven-item calibration cannot justify this general exemption.

   Hunk pairing has another demonstrated blind spot: correcting `1,414` anchors while introducing an unrelated `1,414` samples in the same hunk removes the anchor correction from consideration entirely. That follows the documented hunk-wide policy, but limits what its green result establishes.

5. **Medium — diff coverage mistakes helper names for I/O and propagates nested I/O exemptions outward.**  
   [The heuristic](/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/fdb027d3-253e-4489-98fc-63b857540d00/scratchpad/wt-backlog/scripts/check-plan-code.py:1617) returned no uncovered functions for:
   ```python
   def rule(x):
       return stat(x) > 10
   ```
   Renaming the pure helper made `rule` appear as uncovered. Separately, putting an unused nested function containing `open("x")` inside a pure rule exempted the outer rule, because `ast.walk(ch)` includes nested bodies. Newly written decisions can disappear without any mutation covering them.

6. **Medium — binding validates multi-edit anchors against the wrong intermediate source.**  
   [binding_problems](/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/fdb027d3-253e-4489-98fc-63b857540d00/scratchpad/wt-backlog/scripts/check-plan-code.py:1541) checks every anchor against the original file. With original `return True` and edits:
   ```json
   [["return True", "return False"], ["True", "False"]]
   ```
   **Binding returned rc=0**, claiming both anchors resolve exactly once. The actual mutation runner returned **`anchor NOT FOUND`** for the second edit. Thus the eager pass can pass a mutation that cannot bind during execution.

   The manifest-filename disagreement attack was correctly rejected with **rc=2**. Existing multi-edit entries currently bind sequentially; this counterexample exposes an untested guarantee.

7. **Medium — provenance accepts substrings that are not refs and drops genuine numerical claims.**  
   [PROVENANCE_RE and the cap](/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/fdb027d3-253e-4489-98fc-63b857540d00/scratchpad/wt-backlog/scripts/check-provenance.py:76) accepted:
   ```text
   | 999 | **42 failures**; source notorigin/fiction |
   ```
   `origin/\w+` matches inside another token. It also accepts a prefix of a hyphenated branch name, so the captured “ref” need not identify the stated branch.

   The 80-character cap drops the real row #17 claim **“Five dual adversarial rounds produced 26 Blocking findings and NONE was in the predicate”**. Length does not establish that its count is incidental.

   The bold regex also mispairs delimiters: `**DONE** after 99 checks **42 failures**` produces the supposed bold figure `** after 99 checks **`, losing the actual bolded measurement. Bare dates were correctly rejected, and `` `path.py:84` `` was accepted.

8. **Medium — the “31 of 31” measurement used to justify #250’s scope does not reproduce.**  
   [The claim](/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/fdb027d3-253e-4489-98fc-63b857540d00/scratchpad/wt-backlog/scripts/check-backlog-closure.py:199) says every uppercase `FILED` commit in the last 400 files no rows. Applying its own `claims_filing` and `new_row_ids` functions:
   - At `74a44551`: **31** claiming commits; **9**, not 31, add no new rows.
   - At HEAD: **32** claiming commits; **10** add no new rows.

   Counterexamples include `d17beb92` adding five rows and `1aedd2b1` adding seven. The measured premise for weakening the check is false for these reproducible populations. Lowercase `filed` appeared in **121 commits at `74a44551`**, versus the claimed 142; the original counting method is not supplied.

9. **Medium — the closing evidence mixes incompatible snapshots and contradicts executable results.**  
   [Closing cells](/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/fdb027d3-253e-4489-98fc-63b857540d00/scratchpad/wt-backlog/docs/backlog.md:271):
   - #251 says **zero findings**. HEAD reports **two**: `changed_lines_by_path()` and `owner()`.
   - #252 attributes **1,448 anchors** to `74a44551`. That commit contains **1,416**. The 1,448 count belongs to `0b963e22`.
   - #256 says **74** grandfathered findings. The shipped algorithm reports **77 at `74a44551`**, **75 at HEAD**. Its live branch run also warns on four rows being closed here.
   - The provenance calibration’s **231 rows / 1,368 figures** is not the shipped extractor’s population: that extractor yields **163 rows / 461 figures at `74a44551`**. No committed calibration extractor establishes the alternative population.

   These are evidence defects in the very closures intended to enforce numerical provenance.

10. **Low — #254 adds another implementation of the model eligibility rule.**  
    [failed_requirements](/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/fdb027d3-253e-4489-98fc-63b857540d00/scratchpad/wt-backlog/scripts/codex-frontier-model.py:112) repeats the slug, API support, numeric non-boolean priority, and visibility predicates already owned by `usable_models`; `near` repeats several again. They agree today, but changing the resolver independently can make its explanation contradict its eligibility decision.

11. **Low — case-insensitive prose matching can establish the wrong claim.**  
    Searching for `us is unavailable` with `--expect present` against `The US is unavailable` returned **rc=0**. Country and pronoun meanings differ despite capitalization being their only textual distinction. The documented `--case-sensitive` escape limits severity; the default still cannot establish semantic claim identity.

Execution evidence:

| Check | Result |
|---|---|
| All nine affected scripts’ self-tests | Green: 42, 48, 48, 205, 85, 29, 196, 30, 67 cases |
| Targeted changed/new mutations | **46/46 killed and attributed**; no ambiguous anchor or unattributed crash |
| `--binding` | **1,461 anchors**, 1,453 entries, 62 manifests; 67 warnings |
| `--diff-coverage` | **Two findings**, rc=0 |
| `check-docs.py` | Passed |
| `check-explainer-delivery.py` | Passed |

The golden assertion’s three appended-sentence witnesses reproduced **3, 1, and 1 failing cases**, consistent with the closing cell. The older **1,435 entries / 709 lists / 726 strings / 1,554 expects / 1,443 anchors** figures reproduce at `18abcf8c`; they are historical measurements. Current totals are **1,453 / 727 / 726 / 1,572 / 1,461**. Binding including warning analysis took approximately **870–910 ms** here; the claimed 66 ms did not reproduce.

I found no production caller of `--clear` in the repository, so no demonstrated rc=2 caller regression. The repaired race mutation is attributed to its named case. I did not run the full 1,453-entry sweep, and the seven-survivor classification, earlier coverage calibration, and external-session timing claims remain unverified historical evidence.
