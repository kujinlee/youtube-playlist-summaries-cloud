<!-- codex-review: model=gpt-5.5 -->

## Verdict
FINDINGS

## Findings

### [Blocking] Dead-server restart command abandons the worktree branch
**Where:** scripts/page_chrome.py:120, scripts/page_chrome.py:122, scripts/page_chrome.py:129, scripts/page_chrome.py:132, scripts/page_chrome.py:145  
**What:**  
`scripts/page_chrome.py:120`:
```python
here = pathlib.Path(__file__).resolve().parent.parent
```
`scripts/page_chrome.py:122`:
```python
r = subprocess.run(["git", "-C", str(here), "rev-parse",
```
`scripts/page_chrome.py:129`:
```python
common = pathlib.Path(r.stdout.strip())
```
`scripts/page_chrome.py:132`:
```python
main = common.parent
```
`scripts/page_chrome.py:145`:
```python
return f"cd {root}\npython3 scripts/explainer-serve.py --restart"
```

**Why it matters:** From this checked-out worktree, `repo_root()` returns `/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud`, while the reviewed branch is in `/Users/kujinlee/.claude-tmp/.../scratchpad/wt`. Measured here: main checkout is branch `file-parse-header-redesign` at `995d8b2f`; this PR worktree is `explainer-src-root-self-configures` at `3d2728c6`.

So the fallback command embedded for a DEAD server is:
```sh
cd /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
python3 scripts/explainer-serve.py --restart
```
That restarts a different checkout/branch than the page and reviewed code came from. After that, `/src/` fallback serves the wrong repo.

**Suggested fix:** Hypothesis, not verified: embed the actual worktree root for branch-correctness, or include both commands explicitly: “current worktree” first, “durable main checkout” only as a labelled fallback. If durability is required, copy or resolve to a branch-correct durable path rather than `--git-common-dir`’s parent.

### [High] Pasteable shell commands are not shell-quoted
**Where:** scripts/page_chrome.py:145, scripts/explainer-serve.py:470, scripts/explainer-serve.py:471  
**What:**  
`scripts/page_chrome.py:145`:
```python
return f"cd {root}\npython3 scripts/explainer-serve.py --restart"
```
`scripts/explainer-serve.py:470`:
```python
stop = f"python3 {repo}/scripts/explainer-serve.py --stop"
```
`scripts/explainer-serve.py:471`:
```python
start = f"python3 {repo}/scripts/explainer-serve.py"
```

**Why it matters:** HTML escaping is not shell escaping. For `root = pathlib.Path("/tmp/some repo")`, `restart_commands(root)` produces:
```sh
cd /tmp/some repo
python3 scripts/explainer-serve.py --restart
```
That does not run verbatim: `cd` receives two arguments. For `/tmp/it's here`, the pasted command has an unmatched quote. For `/tmp/x; echo PWNED`, the shell executes a second command.

The 404 remedy has the same defect. For `repo = pathlib.Path("/tmp/some repo")`, it emits:
```sh
python3 /tmp/some repo/scripts/explainer-serve.py --stop
unset EXPLAINER_DOCS_ROOT
python3 /tmp/some repo/scripts/explainer-serve.py
```
That also fails verbatim.

**Suggested fix:** Hypothesis, not verified: use `shlex.quote(str(root))` for `cd -- ...`, and quote the full script path in `src_root_help`, e.g. `python3 {shlex.quote(str(repo / "scripts" / "explainer-serve.py"))} --stop`.

### [Low] One 404 remedy arm still contains an unfilled placeholder
**Where:** scripts/explainer-serve.py:482, scripts/explainer-serve.py:485  
**What:**  
`scripts/explainer-serve.py:482`:
```python
return (f"no source root — {SRC_ROOT_ENV} is unset and the fallback {repo} is not a "
```
`scripts/explainer-serve.py:485`:
```python
f"  {SRC_ROOT_ENV}=<an-existing-checkout> {start}\n")
```

**Why it matters:** The branch claim is that the 404 changed from an unfilled `<dir>` placeholder into a pasteable remedy. In the unset-env/no-fallback path, the body still emits `<an-existing-checkout>`, which is not pasteable. Trigger is unusual but real: server process still running after its repo/worktree directory was moved or deleted.

**Suggested fix:** Hypothesis, not verified: make that arm explicit that no pasteable command can be generated because no existing checkout is known, or omit the placeholder command and tell the reader to rerun from a real checkout.
