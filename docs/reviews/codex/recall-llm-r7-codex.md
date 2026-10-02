<!-- codex-review: model=gpt-5.5 -->

**Findings**

BLOCKING 1: R2 still misses real dead arms when `_PROBE` is the wrong payload.

Evidence:
- [scripts/check-rc-contract.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-rc-contract.py:421): `def dead_arms(hook_src: str, defined: set[int], probe_max: int = 255) -> list[int]:`
- [scripts/check-rc-contract.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-rc-contract.py:443): `codes = [rc for rc in range(probe_max + 1) if rc not in defined]`
- [scripts/check-rc-contract.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-rc-contract.py:450): `for rc, payload in zip(codes, pool.map(lambda c: observe(hook_src, c, _PROBE), codes)):`

Reproduction I ran with a temp-only synthetic hook containing an undefined arm:

```bash
7) [ -z "$OUT" ] && PAYLOAD="dead empty-output arm" ;;
```

Observed output:

```text
observe rc7 with _PROBE: ''
observe rc7 with empty: 'dead empty-output arm\n'
dead_arms: []
```

That violates R2 as stated at [scripts/check-rc-contract.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-rc-contract.py:421): `codes the hook acts on that the matcher cannot emit`. The hook acts on rc 7; `dead_arms` reports clean because `_PROBE` decided the branch.

I also reproduced the residual crash/silence variant you suspected:

```bash
7) PAYLOAD="$(jqq -r . <<<"$OUT")" ;;
```

Observed:

```text
observe rc7: ''
dead arms: []
handled: {0, 3, 5, 6}
undeclared: []
verdict: []
```

Observation that would refute this finding: `dead_arms` returns `[7]`, or raises `CannotRun`, for an undefined arm that acts with empty output or dies inside command substitution instead of forwarding.

BLOCKING 2: the equality is not closed; `observe` can approve a hook that renders #201 in the real repo.

Evidence:
- [scripts/check-rc-contract.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-rc-contract.py:325): `root = Path(td)`
- [scripts/check-rc-contract.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-rc-contract.py:326): `(root / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)`
- [scripts/check-rc-contract.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-rc-contract.py:327): `(root / "scripts").mkdir(parents=True, exist_ok=True)`
- [scripts/check-rc-contract.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-rc-contract.py:329): `hook.write_text(hook_src, encoding="utf-8")`
- [scripts/check-rc-contract.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-rc-contract.py:334): `stub.write_text(`
- [.claude/settings.json](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/settings.json:57): `"command": "bash .claude/hooks/surface-recall.sh",`

`_stub_tree` stages only the hook and matcher. It does not stage `.claude/settings.json`, which exists in the real repo. I tested this twelfth arm:

```bash
5) if [ -f "$REPO_ROOT/.claude/settings.json" ]; then
     PAYLOAD="unreadable. Detail: $OUT"
   else
     PAYLOAD="unreadable."
   fi ;;
```

With the normal observer:

```text
undeclared_render minimal observer: []
```

With the same staged tree plus `.claude/settings.json` present:

```text
fuller-tree context: unreadable. Detail:
```

So `undeclared_render` can return clean while the real hook presents the exact reader-visible #201 defect. The remaining surface is not only shell execution; it is the fidelity of the staged repo.

Observation that would refute this finding: the observer either stages the same repo files the hook may read, or refuses hooks that read undeclared repo dependencies, and the reproduction above reports rc 5 as undeclared.

**Retirement / Closure**

I did not find a defined-code input that old `dangling_detail` would reject and the new equality would accept. The pinned corpus has 11 arms, derived by AST from `_CORPUS`, and `--self-test` reports all 74/74 passing. The known-positive corpus check is meaningful for defined codes.

But the equality is not closed. The `.claude/settings.json` reproduction above is a twelfth arm: clean under `undeclared_render`, broken in a repo-shaped execution.

For `silent_codes`, I could not independently quote the deleted function from immediate `HEAD`; `git show HEAD:scripts/check-rc-contract.py` contains `dangling_detail` at old lines 274-291, but no `silent_codes` symbol. So I am not claiming a specific `silent_codes` retirement loss.

**Numbers Derived**

- Corpus arms: 11, computed by parsing `_CORPUS`.
- Mutation entries: 20, computed by loading `scripts/mutations/check-rc-contract.json`.
- Self-test: `74/74 self-test cases passed`.
- Live run: `6 code(s) defined, 4 handled by an arm, 2 declared unhandled, 6 reader sentence(s) declared`.

**Could Not Establish**

- I did not establish that the six declared sentences are semantically wrong.
- I did not establish that the current shipped hook has the #201 defect.
- I did not establish a ratchet fall among the 7 retired mutation entries; I only verified the manifest now has 20 entries and the documented 25 -> 20 claim is repeated in `check-plan-code.py`.
- I could not quote a pre-replacement `silent_codes` implementation from immediate `HEAD`.

NOT CONVERGED
