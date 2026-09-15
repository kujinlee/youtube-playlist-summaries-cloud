# Adversarial review — round 1 — Claude half — branch `arm-prod-drift-cron` (PR #308)

## Verdict

**FINDINGS — no Blocking, no High.**

The change itself is correct: the YAML parses with `schedule` as a sibling of the other three
events, the job gating does what it claims, and every failure path I could construct ends in a red,
never in a green-over-nothing. I reproduce all of Codex's checks and dispute none of them; two I can
strengthen with facts it did not cite.

What the change does not do is make the alarm **observable**. Four Low/Medium findings below, the
first of which blocks the merge right now for a reason unrelated to the design.

---

## Findings

### [Medium] PR #308 is CONFLICTING with `origin/master` — merge-readiness, not a defect in the change

**Where:** `docs/dashboard-entries.md` (branch appends at `:9115`); `origin/master` is now `1c15f4e2`

**What:**

```
$ gh pr view 308 --json mergeable   →  {"mergeable":"CONFLICTING"}
$ git merge-base origin/master HEAD →  83affe1c
$ git diff --name-only 83affe1c..origin/master
docs/backlog.md
docs/dashboard-entries.md
```

`origin/master` advanced to `1c15f4e2` ("File #124 … (#307)") after this branch was cut, and #307
appended to the same tail of `docs/dashboard-entries.md` that this branch appends to.

**Why it matters:** it is the known *parallel branches append to ONE log* shape — the first same-day
PR merges clean and the rest conflict. It cannot be discovered by reading the diff, only by asking
GitHub, which is why I am filing it rather than assuming the coordinator has seen it. Nothing about
the workflow change needs to move; only the entry's position in the log.

**Suggested fix (hypothesis):** rebase onto `origin/master` and re-place the `## 2026-09-15` entry
after #307's. Duplicate date headings are already normal in this file (`## 2026-09-15` appears three
times on master today), so no heading surgery is needed.

---

### [Low] The repository is PUBLIC, so GitHub can disarm this schedule on its own — and nothing here would notice

**Where:** `.github/workflows/schema-gates.yml:106-127`

**What:** `gh repo view --json visibility` → `{"visibility":"PUBLIC"}`. GitHub's documented rule:

> "In a public repository, scheduled workflows are automatically disabled when no repository
> activity has occurred in 60 days."

The armed comment block asserts armed-ness as a settled property — *"✅ ARMED 2026-09-15"* — and says
nothing about the platform's ability to un-arm it.

**Why it matters:** this is the repo's own favourite failure shape one layer out. A disabled schedule
does not fail; it produces **nothing**, and a gate that silently stops running is indistinguishable
from a gate that runs and finds nothing wrong. The same class covers the cheaper case GitHub also
documents: scheduled runs can be delayed or dropped under load, so a missed night is invisible too.

Probability today is genuinely low — this repo pushes daily, so the 60-day counter never approaches
its limit. I am filing it because the *only* thing standing between this gate and a silent disarm is
that habit, and the file records the opposite impression.

**Suggested fix (hypothesis):** one sentence in the comment block naming the condition
("a public repo's schedule is auto-disabled after 60 days without repository activity; if this ever
goes quiet, the check is off, not clean"). A mechanism — something that notices the *absence* of a
nightly run — is a bigger piece of work and is not obviously worth it at this project's size; the
honest sentence is.

---

### [Low] Who sees a red is never stated — I verified the channel exists, but it is implicit and transfers silently

**Where:** `.github/workflows/schema-gates.yml:106-130` (nothing in the block addresses this);
`docs/dashboard-entries.md` `<!--tech-->` section likewise

**What:** GitHub's documented routing for this case:

> "Notifications for scheduled workflows are sent to the user who last modified the cron syntax in
> the workflow file."

I chased whether that resolves to a real account here, because the branch's commit looked wrong:

```
$ git log -1 --format='%an <%ae>' 88fdb81a   →  t <t@example.com>
$ git log --format='%ae' -30 master | sort | uniq -c
      30 kujinlee@users.noreply.github.com
```

The arming commit is authored by a placeholder identity that appears on **none** of master's last 30
commits. That looked like a High — the one gate nobody watches also having no notification recipient.
**It is not**, and I am recording the refutation rather than the suspicion: squash-merges land on
master re-authored, verified on the most recent merge —

```
$ gh api .../commits/430b2fc1 --jq '{email:.commit.author.email, gh_author:.author.login}'
{"email":"kujinlee@users.noreply.github.com","gh_author":"kujinlee"}
```

so after merge the cron's last modifier is the repo owner, and a nightly red does email someone.

**Why it matters (what survives):** the channel is real but undocumented and *transferable* — the
next person to touch the cron line silently inherits the alerts, and nobody would observe the
handover. And unlike every other gate here, a scheduled failure attaches to no PR's check list, so
the email is the whole of it. The workflow's comment argues at length about not training people to
ignore reds, and omits the one fact that decides whether a red is seen at all.

**Suggested fix (hypothesis):** add the routing to the comment block as a fact with its source
("a scheduled failure notifies whoever last edited the cron line — currently the repo owner — and
appears on no PR"). That also makes the transfer visible at the moment someone edits the line.

---

### [Low] A red can mean "production has not been deployed yet" rather than "production drifted", and the block does not name that window

**Where:** `scripts/check-live-schema.py:489` — `return manifest <= live and not unexpected(live, manifest, accepted)`

**What:** the nightly compares live production against `docs/superpowers/specs/m4/live-manifest.txt`
**as it exists on master**. The addition direction has an escape hatch (`accepted-additions.txt`,
consulted by `unexpected`); the `manifest <= live` direction has none short of editing the manifest.

**Why it matters:** any change that moves master's expectation ahead of what is deployed puts the
nightly red every night until someone deploys — which is precisely *"a gate that cries wolf nightly
is one people learn to scroll past"*, the sentence this block quotes as its own guiding principle.
The comment's *WHAT THIS DOES NOT PROVE* paragraph covers the credential going missing and stops
there.

I want to be accurate about how narrow this is, so: the manifest is pinned to M4's object set,
derived by `gen-m4-manifest.py` from `build-m4-schema.py`'s output, not from "all migrations". A
future unrelated table is not in it, and an added column on an M4-owned relation is absorbable via
the accept-list. The window I can actually construct requires a migration that *alters or removes* an
M4-owned object. That is real but rare, and the label on this finding reflects it.
**Labelled a hypothesis: I did not execute this scenario.**

**Suggested fix (hypothesis):** a clause in the *DOES NOT PROVE* paragraph — "a red can also mean the
repo is ahead of production, i.e. a migration merged but not applied; the check has no way to tell
that from drift, so read the named objects before believing either."

---

## Codex's claims — verified independently

| Claim | Verdict | How I checked |
|---|---|---|
| `schedule` correctly a sibling under `on:` | ✅ reproduced | parsed the file with `js-yaml`: `on` keys = `pull_request, push, schedule, workflow_dispatch`; `schedule` → `[{"cron":"0 9 * * *"}]`; indentation audit of `:59-130` shows `schedule:` at indent 2, matching `push:`/`pull_request:` |
| schedule runs only `prod-drift`; `schema-gates` excluded | ✅ reproduced | `:149` `if: github.event_name != 'schedule'`, `:195` `if: github.event_name == 'schedule' \|\| github.event_name == 'workflow_dispatch'`, both read back out of the parsed YAML rather than the text |
| push/PR runs never touch production | ✅ reproduced, and stronger than stated | `:195` excludes both. Two facts Codex did not cite that close the remaining holes: **scheduled runs execute only on the default branch** ("Scheduled workflows run on the latest commit on the default branch"), so there is no way to get a scheduled production read from a feature branch; and **path filters do not apply to `schedule`**, so the two `paths:` lists at `:62-105` neither suppress nor mis-fire the nightly. I also confirmed the two lists are still byte-identical (13 entries each) — unchanged by this branch |
| concurrency key includes `github.event_name` | ✅ reproduced | `:138` `group: schema-gates-${{ github.workflow }}-${{ github.event_name }}-${{ github.ref }}`; a push to master and the cron differ in `event_name`, so 08:59 and 09:00 land in different groups. `cancel-in-progress` can then only cancel a run of the *same* event, which for a daily cron means nothing to cancel |
| missing secret → rc=2 before any schema claim | ✅ reproduced | `:208-219`, `exit 2` on empty, before `setup-python` and before the check step |
| rotated-but-nonempty credential → CANNOT RUN, rc=2 | ✅ reproduced | `m4_catalog.py:522-527` raises `RuntimeError` on any nonzero psql exit; `check-live-schema.py:887-889` catches it and prints `CANNOT RUN — … Treat this as NOT RUN`, `return 2` |
| no path reports success having checked nothing | ✅ reproduced, plus two guards Codex did not name | `:489` `manifest <= live` means an empty or partial catalog **fails** under `--expect-present` — the empty-set pass is impossible in this polarity. On top of that `:903-908` refuses (rc=2) if the manifest names no owned relation, and `load_manifest` refuses an empty manifest one level up |
| cost bounded; cleanup unconditional | ✅ reproduced | `:197` `timeout-minutes: 10`; `:248-250` `if: always()` with `docker rm -f … \|\| true`. The proven run took **21 seconds** of job time (18:38:01→18:38:24) |
| the comment does not overclaim | ✅ reproduced, checked claim by claim | see below |

### The comment's factual claims, each measured

- *"This block spent two days saying the schedule was deliberately NOT armed"* — ✅ the unarmed text
  landed in `3168f028` (2026-09-13) and is removed in `88fdb81a` (2026-09-15).
- *"run 35008676617, **prod-drift: success**"* — ✅ `gh run view 35008676617`: `event: workflow_dispatch`,
  `headBranch: master`, job `prod-drift` `conclusion: success`, step *"Has production drifted from the
  manifest?"* success.
- *"the first time that job has ever run to a verdict"* — ✅ and this one is genuinely checkable: every
  earlier run of this workflow (`gh run list --workflow=schema-gates.yml`) is `pull_request` or `push`,
  on which `:195` excludes `prod-drift`. No earlier verdict was possible.
- *"it still refuses loudly (rc=2 …) if the credential goes missing"* — ✅ two independent paths, the
  workflow step and the script's own `read_only_url()` refusal at `check-live-schema.py:870-873`.

### Dashboard entry

No measurably false statement found. *"sitting unarmed for two days"* ✓, *"all 161 objects"* ✓ matches
the manifest size the proven run printed, *"the concurrency key already includes `github.event_name`,
so the 09:00 cron and a push to master cannot cancel each other"* ✓.

### Credential exposure on a public repo — checked, nothing new

Actions logs on a public repository are world-readable, and this job now touches a production
credential nightly. I checked the obvious leak and it is already closed by design:
`m4_catalog.py:506-512` deliberately passes `-e PGU` with **no `=value`** so the URL never enters
argv, with the measurement recorded in the docstring (`ps` showed the full URL including the
password in the earlier form). The verdict line prints `user@host/db`, and the production project ref
is already committed in the workflow comment and is public in the app's own URLs — so the nightly log
exposes nothing the repository does not already publish. Not a finding.

---

## The decision itself: is arming a nightly production read right when nobody may be watching?

**Yes, and I looked for the argument that it is not.**

The strongest case against is not about this diff. It is that the change asserts a property it does
not measure. "This is checked nightly" is now true of the config and unobserved in practice: a
failure's entire routing is one email to one person, a green produces no signal at all, and the two
ways the check can stop happening — a delayed or dropped scheduled run, and the 60-day public-repo
auto-disable — both look exactly like a quiet night. By this repo's own standard ("cannot run" is a
failure, never a pass), *did not run* deserves the same treatment as *ran and refused*, and only the
second one is handled here. There is a version of this change that ships with an acknowledgment loop,
and it is better.

The case for arming still wins, for three reasons I can point at rather than assert. Production drift
is the one subject with no push to hang a check on, so the alternative to an imperfectly-watched
nightly is **no detection at all** — and unwatched-but-recorded beats unchecked, because the Actions
history makes the first red findable after the fact even if the email is missed. The job fails closed
on every path I could construct, so the realistic bad outcome is a red nobody reads, never a green
that lies. And the cost is 21 seconds a day of free public-repo minutes, with the cancellation hazard
already designed out.

The gap is observability, not correctness, and it is a sentence rather than a redesign. Ship it.

## Recommendation

Merge after the `docs/dashboard-entries.md` conflict is resolved. The three Lows are all one
clarifying sentence each in the same comment block; folding them in now is cheap and keeps the block
honest about what it can and cannot promise, but none of them is a reason to hold the change.
