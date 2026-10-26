<!-- codex-review: model=gpt-6.1-sol -->

1. **P1 — Restored packages bypass the claimed signed-index hash verification.** `.github/workflows/ci.yml:228`  
   **Executed:** In an isolated Ubuntu 24.04 container, apt 2.8.3 accepted a fabricated `hello` package placed in the archive cache under the expected filename and padded to the indexed size. Both `--download-only` and `--no-download` succeeded; its replacement post-install script executed. Its SHA256 differed from the repository package. Apt’s [archive acquisition code](https://raw.githubusercontent.com/Debian/apt/main/apt-pkg/acquire-item.cc) accepts an existing archive by size.  
   Thus a poisoned cache can install bytes the signed index never named. The key authenticates neither archive contents nor cache provenance. Validate restored files against current signed-index SHA256 values before copying them into apt’s cache. The verification claims at workflow lines 152–155, in the PR body, and at `docs/dashboard-entries.md:17647–17649` are false.

2. **P1 — A failed optional key step can skip the required install.** `.github/workflows/ci.yml:160–171`  
   **Reasoned:** Only `apt-get update` has a process timeout. `--print-uris` is unbounded; if it hangs until the four-minute step timeout, GitHub marks the step failed. `set +e` cannot intercept that timeout. The install has the implicit `success()` condition and is skipped. An unhandled restore failure likewise skips it; the [restore implementation](https://raw.githubusercontent.com/actions/cache/v4/src/restoreImpl.ts) calls `core.setFailed` for escaping errors. Make cache failures nonfatal and ensure the install remains eligible after them.

3. **P2 — The key is not the complete SHA256 package manifest advertised.** `.github/workflows/ci.yml:171–177`  
   **Executed:** Apt 2.8.3 printed `MD5Sum:…`, not SHA256. After an archive was present, `--print-uris` omitted that package although it remained uninstalled. Different required package sets can therefore produce identical printed lists when their differences are already cached. This is a manifest omission, independent of cryptographic collisions.  
   **Executed with stubbed apt under Bash:** A process printing one URI and exiting 100 still produced a nonempty key and step exit 0. The pipeline’s status is never checked.  
   **Reasoned:** The install also refreshes indexes again at line 240, allowing packages downloaded under a newer index to be saved under the earlier key. Check command success, obtain explicit strong hashes for the complete archive set, and reconcile the second update.

4. **P2 — The claimed 29-minute worst case omits cache operations.** `.github/workflows/ci.yml:143–145,178–184,273–278`  
   **Reasoned:** `20 + 4 + ~5 = ~29` excludes restore and save, neither of which has a step timeout. The cache action documents a [ten-minute default download-segment timeout](https://github.com/actions/cache/blob/v4/README.md). A slow restore can exhaust the job’s remaining budget before the required checks finish. Bound and budget both cache operations; update the PR body and `docs/dashboard-entries.md:17649`.

Other requested checks:

- An empty URI list—including an already-installed, current ffmpeg—returns success without a key; that path preserves install execution.
- The archive-copy glob saves **all** top-level `.deb`s, including unrelated packages; “exactly what this run downloaded” at line 261 is inaccurate. An empty glob is harmless because `|| true` suppresses the copy failure. These conclusions are reasoned from Bash semantics.
- `actions/cache/save` runs on successful `pull_request` executions with a nonempty key and a miss. Its ordinary caught errors produce warnings. PR-created caches are scoped to `refs/pull/.../merge` and cannot be restored by other PRs or the base branch; PRs can restore eligible base-branch caches. [GitHub cache scope documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching).
- Read PR #407 and backlog #358 from PR #406’s branch. The backlog’s falsifier requires **20 consecutive runs without ffmpeg CANNOT RUN**; the PR’s miss/rerun check is narrower. The dashboard’s “slow package mirror stops failing pull requests” is unsupported: cold PR caches still download, and every hit still requires an index update.

No repository edits; experiments used a temporary copy and disposable containers. CI was not run.

VERDICT: NOT CONVERGED
