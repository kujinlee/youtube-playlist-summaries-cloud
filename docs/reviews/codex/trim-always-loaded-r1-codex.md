<!-- codex-review: model=gpt-6.1-sol -->

Reviewed head: 36a614b168d1516cc34425471460a2d5062c4154

The claim is refuted: the moves preserve the source text, but several actionable clauses no longer appear in the always-loaded spine. No finding below qualifies as a Q4c BLOCKER; none has a reproduced false green, data loss, corruption, or security hole.

| Severity / disposition | File:line | Concrete input and consequence | Fix-induced? |
|---|---|---|---|
| **Medium — FILE** | `docs/plugins.md:101` | Dispatch concurrent review agents with uncommitted coordinator edits. Master explicitly required **commit before spawning** and named the three serialisation hazards; the replacement only points elsewhere. A coordinator using the spine alone lacks the protective action. Restore a compact actionable constraint. | No; introduced by trimming |
| **Medium — FILE** | `docs/plugins.md:137` | A captured review contains a completion report but **no findings section**. Master explicitly classified this as a failed run; the spine now merely says to read the file. It also drops the instruction to prefer the reviewer reporting a finding until the code is traced. Reading alone does not specify the disposition. | No; introduced by trimming |
| **Medium — FILE** | `docs/dev-process.md:138` | A new clone pushes before its git hooks are installed. Master stated that the plan-leak gate must be enabled per clone through `scripts/install-git-hooks.sh`, that CI has no plans, and what the eight-word detector misses. The replacement names the gate without retaining its installation dependency or bound. The spine alone cannot establish that a push is protected. | No; introduced by trimming |
| **Medium — FILE** | `docs/plugins.md:113` | The frontier resolver refuses its candidates. Master required reading its message and verifying `codex exec -m <slug>` **inside a git worktree before recording a review gap**. The condensed line permits moving straight from a resolver refusal to fallback. Restore the diagnostic action. | No; introduced by trimming |
| **Low — FILE** | `docs/plugins.md:128` | The wrapper returns **3**, leaving a paid review at `--out`. The spine correctly prohibits fallback, but drops master's next action: **move the capture or rerun with `--allow-overwrite`**. The negative rule survives; the recovery procedure does not. | No; introduced by trimming |
| **Medium — FILE; known issue confirmed** | `docs/trim-floor-walkthrough.md:33`; `docs/dashboard-entries.md:18507` | Price 100 calls sharing one cached prefix as 550,000 saved full-price tokens. Using the supplied cache weights, the recurring saving is approximately **55,000 weighted tokens**, plus approximately **6,875 per fresh prefix write**. Both docs must distinguish the ~5,500 raw input-token reduction from **~550 weighted per cached call + ~6.9k per fresh prefix write**. | No; introduced by this PR |
| **Low — FILE** | `docs/process-checklists.md:1174` | Read the relocated handoff table independently. Its authority row says “the RULE box above” and “`CLAUDE.md` imports this file”; neither describes its new location. The payload is verbatim, but relocation makes those contextual references false. Point explicitly to `plugins.md`’s RULE box. | No; relocation-induced |

**Spine-alone audit of the removed material**

| Removed paragraph/block | Replacement | Coordinator still acts correctly? |
|---|---|---|
| Thrashing account | `dev-process.md:113–119` | **Yes:** consecutive fix-induced rounds, one component, four-round question, total-appearance ranking retained. |
| Mechanical-check table rows | `dev-process.md:138–166` | Core check descriptions retained. **Not fully:** plan-gate installation/bounds and schema-workflow-before-required-setting ordering are absent. |
| Spine history and eviction note | `dev-process.md:206–214` | **Yes:** script-first rule and budget enforcement remain. |
| Handoff history, layer table, falsifier, limitations, command note | `plugins.md:88–93` | Authority, leading gate, self-test and command re-authoring survive. The instruction-versus-outcome limitation is deferred. |
| Agent authorisation/topology paragraph | `plugins.md:97–106` | Authorisation, alternation and cap pointer survive; serialisation actions do not. |
| Frontier model account | `plugins.md:113–116` | Dynamic selection and hidden-model prohibition survive; refusal verification does not. |
| Fallback paragraph | `plugins.md:118–120` | **TIMEOUT exception survives exactly in substance:** double and retry once. Explicit retry bounds and full-file-access requirement are omitted. |
| Wrapper command and rc=3 box | `plugins.md:122–132` | Exit codes, scratch location and **no fallback on rc=3** survive; recovery action omitted. |
| Per-half output and filing boxes | `plugins.md:133–134` | **Yes:** Claude writes; Codex final message is review; writer subdirectory required. |
| Prompt-file/backtick paragraphs | `plugins.md:122–123`; existing `dev-process.md` Tools rule | **Yes.** |
| Wrapper success/self-test paragraph | `plugins.md:137–138` | **Partial:** read-file rule remains; wrapper self-test instruction is omitted. |
| Two-sandbox paragraph | `plugins.md:135–136` | **Yes for the operative gate:** inner sandbox and inability-to-run-suite failure retained. |
| Fail-open paragraph | `plugins.md:137–138` | **Partial:** specific failed-output and disagreement actions omitted. |
| Bounded-wait paragraph | `plugins.md:139` | **Yes for silence:** read output and wait through timeout; explicit immediate-fallback cases are deferred. |

**Move and pointer checks:** All five moved payloads match `origin/master` verbatim after allowing the three qualified backlog references and added introductory material. The unchanged review skill table remains in the spine. The new spine heading pointers resolve, including concurrency, topology, full review detail, handoff layers, full check rows, arming account, history, and §0 Q4c. Merge-when-READY/HOLD and the existing round-cap rules were preserved.

Sibling search: compared both changed spine files against master and checked all five destination blocks; the findings above include the related omissions found in that sweep.

`python3 scripts/check-docs.py` ran **in the foreground**, exited **0**, and reported **Documentation integrity OK**. It warned that `dev-process.md` has six lines of budget remaining.

VERDICT: NOT CONVERGED
