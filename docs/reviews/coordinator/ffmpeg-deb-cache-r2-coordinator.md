# Round 2 — `ffmpeg-deb-cache` — coordinator — ⟳ NOT CONVERGED (bet half LOST); SPLIT

```yaml
round: 2
fixes_nontrivial: true
subject: ffmpeg-deb-cache
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XP1, severity: Medium, aim: deliverable, fix_induced: true, component: cache-steps, disposition: fixed}
  - {id: XP2, severity: Low, aim: deliverable, fix_induced: true, component: cache-steps, disposition: fixed}
```

REVIEW GAP: claude — round 2 alternates to the Codex half on the final tree (`review-method.md`, *The
protocol*, step 4; backlog #339).

`X` = Codex, tree `88f18c6d`, in disposable `ubuntu:26.04` containers. **The integrity half of the bet HELD**: a
same-size forgery was rejected, a missing file downloaded, an unlisted file never reached apt's archive; `:`, `+`, `~`
in filenames survived the parse; a manifest entry with no SHA256 disables the cache. **The availability half was
LOST** — by the round-1 fold:

- **XP1 (fold-induced, fixed by SPLIT):** the save-preparation copy ran INSIDE the required install step, so a failed
  `cp` (a read-only restored file) aborted the install under `-e`. Cache preparation is now its own
  `continue-on-error`, bounded step, and the one cache piece left in the install — the verified copy — runs in a
  subshell whose failure only warns. Container: with every copy forced to fail, the step still reached the install.
- **XP2 (fold-induced, fixed):** the save directory kept unlisted extras from a partial restore. The staging step
  rebuilds it from scratch with exactly the manifest's files, each re-hashed; the save runs only if all were staged.
  Container: 194 of 194 staged, the injected extra gone, none failing its SHA256.

Budget per path restated (28.3 / 28.0 of 30). Route: SPLIT (decision-log row written before the change). Round 3 is
the last, a confirmation round.
