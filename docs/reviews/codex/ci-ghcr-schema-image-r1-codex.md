<!-- codex-review: model=gpt-6.1-sol -->

1. **HIGH — `.github/workflows/schema-gates.yml:191` — mirror remains inaccessible anonymously.**  
   **Input:** configured GHCR digest, with no credentials.  
   **Observed:** manifest request returned `"anonymous manifest HTTP 401"`; anonymous token request returned `{"errors":[{"code":"UNAUTHORIZED","message":"authentication required"}]}`. Fresh runners cannot obtain the image, so the required check remains blocked. No images were pulled.  
   **Fix:** make the package public and verify anonymous access to the exact digest before landing.

2. **LOW — `.github/workflows/schema-gates.yml:308` — production client lacks the promised CANNOT RUN classification.**  
   **Input:** private, deleted, or unavailable image on a fresh runner.  
   **What happens:** the unguarded `docker run` fails and GitHub’s shell stops the step. This fails closed, but does **not** explicitly return `2` or print `CANNOT RUN`. Actual Docker failure output: **UNVERIFIED**; no pull/run performed. This handling predates the change.  
   **Fix:** wrap client startup with an explicit diagnostic and `exit 2`.

3. **LOW — `docs/dashboard-entries.md:17273`, `.github/workflows/schema-gates.yml:187`, `docs/backlog.md:296` — completion claims precede the prerequisite.**  
   **Input:** current private package.  
   **What happens:** documentation says `"Package is public"` and `"both are fixed"`, contradicted by the anonymous-access results above. Closing #310 **as a duplicate** is accurate; claiming the remedy is operational is premature.  
   **Fix:** describe public visibility and successful anonymous verification as pending, or complete them before retaining these claims.

Other mandate results:

- Read the whole startup script. Every image argument is quoted; no tag parsing exists. Digest references pass intact through inspect, pull, run, and diagnostics. The self-test does not exercise image acquisition.
- A read-only shell-function simulation of denied acquisition produced `"CANNOT RUN — could not obtain ghcr.io/kujinlee/supabase-postgres@sha256:… after 1 attempt(s)."` and `"exit=2"`. No container startup was reached.
- Workflow-level env reaches both shell steps; no conflicting override or services block exists. This matches [GitHub’s env scoping rules](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax). Remaining ECR references are the intentional local default and comments.
- Self-tests passed: Python pin **111/111**, guard coverage **37/37**, storage independence **50/50**, CI watched **82/82**, startup script **23/23**. Normal runs passed for the first three; Python reported its local **3.14 versus CI 3.12** advisory. CI watched without arguments returned **2**, printing usage. A separate simulated CI pin verdict correctly recognized both workflow jobs. No top-level-env parsing regression found.
- Other literal `schema-gates.yml` references occur in merge-ready, review-recorded, and plan-code. Their complete suites were **UNVERIFIED**.
- Digest pinning improves content integrity over a mutable ECR tag. A package compromise can deny access or delete content; it cannot substitute different bytes under the pinned digest, assuming digest verification holds. It cannot thereby inject a malicious psql client to steal production credentials. Pinning freezes upstream updates, including security fixes, until explicitly updated. See [Docker’s digest-pull documentation](https://docs.docker.com/reference/cli/docker/image/pull/). Mirror/original digest equality was supplied evidence, not independently reverified.

No repository files were intentionally written; final `git status --short` was clean.

VERDICT: NOT CONVERGED
