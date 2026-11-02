# Round 2 — plan-leak-guard — claude

**Subject:** PR #443, branch `plan-leak-guard` (backlog #393), HEAD `821929e9`, reviewed as `git diff 95d08979..HEAD`.
**Verdict: NOT CONVERGED** — 1 Blocking, 1 High, 1 Medium, 5 Low.

**Method.** I worked in a temp repo, `scratchpad/r2-393/repo`, built from `git archive HEAD scripts .githooks .claude/hooks`, with a bare remote `r2-393/remote.git`. The hook was installed with `scripts/install-git-hooks.sh` in that repo only, and `--status` reported ACTIVE. Every trial was a real push. For trials after the first batch, the remote was rebuilt fresh before each one, so nothing could be counted public because an earlier trial had pushed it.

I used a SYNTHETIC plan, `.claude/plans/zz-plan.md`. My first plan reused words from the self-test's own fixtures. Those words are in the repo, so the public filter correctly passed them. I threw that run away and used words that appear nowhere in the repo. Nothing under the real `.claude/plans/` was read or printed. The plan-shape census below counts line shapes only.

## Required runs (foreground)

| Check | Result |
|---|---|
| `python3 scripts/check-plan-leak.py --self-test` | **105/105 passed** (36 s) |
| `python3 scripts/check-plan-code.py --mutate . --only scripts/check-plan-leak.py --allow-long-local` | **68 mutations, 68 killed, all 68 attributed to their named case, 0 survivors**, rc 0. ⚠ It started in the foreground. The tool's 600 s limit moved it to the background, and it ran to completion there (≈27 min). |
| `.claude/hooks/block-default-branch-push.sh --self-test` | 25/25 passed |
| False-block rate: `--base C^ --head C` over the last 40 first-parent commits of `origin/master` | **39 clean, 1 blocked**: `82fc68f1`, 2 lines: `docs/memory/push-is-mine-merging-is-theirs.md:59` and `:60`. I did not judge whether it is a real leak, because I may not read the plan. This matches the docstring's stated "1 false hit in 40" at 8 words. |

## What the bet survived (all real pushes, all blocked, and the remote verified to hold none of the phrase)

**Push forms**
- a new branch
- `--all`
- `--tags` (a lightweight tag on a leak commit)
- `--mirror`
- `HEAD:refs/heads/x`
- `<sha>:refs/heads/x`
- `refs/foo/x`
- `refs/notes/commits` (the note text)
- a delete and an add in one push
- `--force-with-lease` over a public branch
- a push from a subdirectory
- `git -C <dir>`
- a push from a second worktree
- a plan that exists ONLY in another worktree, pushed from the main one

**History shapes**
- added in one commit, removed in the next
- a merge that carries a side-branch leak
- an evil merge (content only in the merge commit)
- a rebase

**Metadata**
- commit message body
- added file NAME
- an annotated tag on a public commit
- a tag of a tag, with the inner tag deleted locally

**Failure paths**
- An unreadable plan file → CANNOT RUN, and the push is blocked.
- `ALLOW_PLAN_LEAK=1` passes and says so.

**SessionStart hook**
- `core.hooksPath` unset → installs, quietly.
- `core.hooksPath` pointing elsewhere → loud `systemMessage` and `additionalContext`, nothing changed.
- A live `.git/hooks/pre-commit` → install refused, loud warning.

None of the SessionStart messages carries plan words. The real clone has `core.hooksPath` unset and no live hooks, so the hook will install there after merge.

The public-at-base filter is not fed by the same push. `tips` holds only `ls-remote` shas plus the remote shas git puts on stdin, all of which are the remote's. A leak in an earlier commit of the same push was blocked in every multi-commit trial.

## Findings

### F1 — Blocking — `scripts/check-plan-leak.py:177-179` (`parse_log`) with `:368` (`pushed_log`)
- **fix_induced:** false. The `+++ b/` dependency predates this round (`95d08979:scripts/check-plan-leak.py:136`).
- **component:** diff-reader

`git log -p` honours `diff.noprefix`, `diff.srcPrefix` and `diff.dstPrefix` from any config level, repo or global. With any of them set, the `+++` header lacks `b/`. `path` stays `None`, and **every added content line is dropped**. The hook then prints `hits 0` and exits 0. That is a green verdict over nothing, the exact shape "cannot run is a failure, never a pass" forbids.

**Input:**
```
git config diff.noprefix true
echo "<8+ plan words>" > np.md && git commit -am x && git push origin np
```

**Evidence (run):**
- `diff.noprefix=true` (repo config): `plan-leak: … added runs 2 · hits 0`, `* [new branch] np -> np`. The remote's `np:np.md` holds the plan sentence.
- The same leak with `diff.noprefix` set in a GLOBAL `~/.gitconfig` (`HOME` pointed at a fake home): pushed.
- `diff.dstPrefix=Z/`: pushed.
- `diff.mnemonicPrefix=true` was blocked.

The suite cannot see this, because `fixture_git.isolated()` neutralises user config. The owner's global config does not set `diff.noprefix` today, so this is not live on this machine. It turns off with one config line, though, and gives no signal when it does.

**Fix:** pass `--src-prefix=a/ --dst-prefix=b/` to `pushed_log`. As a second layer, make an added line under a header whose path could not be read a CANNOT RUN, not a skip. Add a case that sets `diff.noprefix` inside the fixture, and a mutation for it.

### F2 — High — `scripts/check-plan-leak.py:118-120` (`words`)
- **fix_induced:** false
- **component:** matcher normalisation

`\w+` over raw text turns escape and markup syntax into WORDS inside the phrase, and that breaks the 8-word run. This repo commits exactly these formats:
- 97 tracked `docs/**/*.html` explainer pages, with entities such as `&mdash;`, `&#x27;` and `&quot;` (74 in one page);
- review verdict JSON written with `ensure_ascii`, where `\u20xx` escapes appear (14 in `docs/reviews/verdicts/guard-fail-open-batch-r2-codex.verdict.json`).

That is the same class as the incident that motivated #393: a review artifact quoting plan text.

**Inputs, all pushed through the hook to a fresh remote:**
- **Pushed:** the plan item rendered with entities. Words in the plan: `don't let the "orange" quokka — or its cousin — refuse …`. Pushed text: `don&#x27;t … &quot;orange&quot; quokka &mdash; or its cousin &mdash; refuse …`.
- **Pushed:** the same item as `json.dumps(...)`, which writes `—`. This yields the token `u2014`.
- **Pushed:** `repaint the zebra <em>carousel</em> using marmalade …`, where `em` is inserted twice.
- **Pushed:** `repaint the [zebra carousel](docs/x.md) using marmalade …`, where `docs x md` are inserted.
- **Pushed:** the plan step as a UTF-16 file. Every letter becomes its own word.
- **Blocked:** `html.escape(item)` and `<code>scripts/x.py</code> before …`. These were blocked only because a clean tail of 8 or more words happened to survive, not because the markup was understood.

**Fix:** normalise text before `words()`, in the matcher, in `public_in`, and in the plan side alike:
1. `html.unescape`;
2. strip `<[^>]*>`;
3. decode `\uXXXX`;
4. drop markdown link targets, `\]\([^)]*\)`.

Add one case per format.

### F3 — Medium — `.githooks/pre-push` + `install_hooks` (`scripts/check-plan-leak.py:483`, relative `core.hooksPath`)
- **fix_induced:** true. The redesign introduced the relative `core.hooksPath`.
- **component:** hook-install

git resolves a relative `core.hooksPath` against the directory hooks run in. With `--git-dir`, or `GIT_DIR` and no work tree, that directory is the caller's cwd. So no hook is found, and the push is silently unchecked.

**Input:**
```
cd / && git --git-dir=<repo>/.git push origin gd
```

**Evidence (run):** pushed, no `plan-leak:` line at all. The remote holds the sentence.

The docstring's BOUNDS name the old-branch-worktree hole but not this one.

**Fix:** state the bound. Alternatively, set `core.hooksPath` to the ABSOLUTE `<main checkout>/.githooks`. That also closes the stated bound, because every worktree would then run the main checkout's hook. The script already reads every checkout's plans, and the object store is shared. Its cost is that the main checkout must hold the hook.

### F4 — Low — `scripts/check-plan-leak.py:322-325` (`_git`)
- **fix_induced:** false
- **component:** diff-reader

`git log`, `ls-tree` and `cat-file` honour `refs/replace`, but the push sends the ORIGINAL objects.

**Input:**
```
git replace <leak commit> <clean commit> && git push origin rp
```

**Evidence (run):** `hits 0`, and the remote holds the leak.

Only a deliberate act triggers this, but the fix is one variable: set `GIT_NO_REPLACE_OBJECTS=1` in `_git`'s env, after the `GIT_*` strip.

### F5 — Low — `scripts/check-plan-leak.py:291-293` (`_where`)
- **fix_induced:** true, from the file-name security fold
- **component:** output-channel

For a hit in a file NAME, the HIT line prints the path, and the path IS the matched words.

**Evidence (run):**
```
HIT repaint-the-zebra-carousel-using-marmalade-before-the-comet-reaches-Gdansk.md (its file NAME) in f78ec402f4
```
This went to stderr, which the model sees. The docstring's claim, "never the matched words, in EVERY channel", is false for this case.

**Fix:** print the parent directory plus `<file name, N chars>`, or the commit and the index of the added path.

### F6 — Low — `.claude/hooks/block-default-branch-push.sh` RULE 2 (pre-existing, `--no-verify([[:space:]=]|$)`)
- **fix_induced:** false
- **component:** agent-hook

git accepts abbreviated long options, so `git push --no-veri` skips the pre-push hook. The agent hook allows it.

**Evidence (run):**
- The probe `git push --no-veri origin feat/x` → allow. `--no-v` → allow.
- A real `--no-veri` push of a leak to a fresh remote → pushed.

The checker's docstring (`:47-48`) and the checklist both lean on "the agent push hook refuses it". These are deliberate forms, so this is defence in depth only.

**Fix:** match `--no-ver[a-z]*`, or `--no-v` followed by `[a-z]*`.

### F7 — Low — `scripts/check-plan-leak.py:96` (`LIST_ITEM`)
- **fix_induced:** false
- **component:** plan-discovery

Numbered items (`1. …`) and table rows are not plan text, and BOUNDS names only "headings and paragraphs".

**Evidence (run):**
- An 8+-word numbered item, pushed.
- An 8+-word table row, pushed.
- Census of the 139 real plans, counted by shape only: 1,996 dash items, **0 numbered**, 14 table rows (5 of them with 8 or more words), 657 prose lines with 8 or more words.

So the practical gap is small, but it is undocumented.

**Fix:** add `\d+[.)]` to `LIST_ITEM`, or name both shapes in BOUNDS.

### F8 — Low — `parse_updates` (`:301-313`)
- **fix_induced:** false
- **component:** metadata

Ref NAMES are pushed text and are not scanned.

**Evidence (run):** `git push origin HEAD:refs/heads/<8 plan words joined by ->` → pushed.

This is unusual, and the fix is cheap: scan `parts[2]` of each stdin line as a run.

## Outside the bet (not a push; noted, not counted)

`gh pr create --body-file`, PR and issue comments, and `gh api` content writes publish text without any `git push`. The original #393 incident class, review prose that quotes a plan, is just as likely in a PR body. Whether that belongs in #393 or a new row is the coordinator's call.

## Counts

- 8 findings: Blocking 1 (F1), High 1 (F2), Medium 1 (F3), Low 5 (F4–F8).
- Fix-induced: F3 and F5.
- Components: diff-reader ×2 (F1, F4), matcher normalisation, hook-install, output-channel, agent-hook, plan-discovery, metadata.

**NOT CONVERGED** — F1 refutes the bet. With `diff.noprefix` or `diff.dstPrefix` set, an 8-word plan run is published while the hook reports `hits 0`. F2 refutes it for HTML entities and tags, JSON `\u` escapes, markdown links and UTF-16. Both are formats this repo commits.
