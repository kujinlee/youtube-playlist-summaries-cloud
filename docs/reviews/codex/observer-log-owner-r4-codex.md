# Codex adversarial review — observer-log-owner, round 4

**Subject:** the FOLD — `63093d7f` (round 4's fold of its Claude half's 7 findings) over `7840a3be`.
Mandate: refute, not confirm.

**Verdict: NOT CONVERGED — 0 Blocking, 1 High, 0 Medium, 0 Low.**

⚠ **Captured from the final message — Codex writes no file** (`docs/plugins.md` output contract).
Verdict: `docs/reviews/verdicts/observer-log-owner-r4-codex.000505d9.verdict.json`, `gate_ran=true`,
model `gpt-5.5`. ⭐ That filename is the round-4 allocator working on its own first live dispatch.

---

<!-- codex-review: model=gpt-5.5 -->

Subject: reviewed fold `63093d7f41eb94922abb18a3c10d34adb488aaff` on `observer-log-owner` against base `origin/master` / `b493edcc`; specifically the round-4 fold over `c3ad7727` and `7840a3be`. Worktree stayed clean.

**NOT CONVERGED** — 0 Blocking · 1 High · 0 Medium · 0 Low

What I verified GREEN:

```
$ python3 scripts/codex-review.py --self-test; printf 'rc=%s\n' "$?"
115/115 passed
rc=0
```

```
$ python3 scripts/check-plan-code.py --self-test; printf 'rc=%s\n' "$?"
130/130 passed
rc=0
```

```
$ python3 scripts/check-selftest-counts.py; printf 'rc=%s\n' "$?"
self-test counts: 46 script(s) declare a count, every one verified by running it
rc=0
```

```
$ python3 scripts/check-ratchet-contract.py; printf 'rc=%s\n' "$?"
guards discovered (40): ...
ratchet contract OK
rc=0
```

```
$ python3 scripts/check-docs.py; printf 'rc=%s\n' "$?"
Documentation integrity OK
rc=0

$ python3 scripts/check-plan-file-tags.py; printf 'rc=%s\n' "$?"
plan-mode tags: 0 across 1440 documents under docs/
rc=0

$ python3 scripts/check-dashboard-entry.py; printf 'rc=%s\n' "$?"
ok — an entry block was added
rc=0
```

```
$ python3 scripts/check-review-rounds.py; printf 'rc=%s\n' "$?"
FAILED — 1 review round(s) with one half and no stated reason:

  ✗ observer-log-owner round 4: only claude — codex neither ran nor recorded a `REVIEW GAP:` line
rc=1
```

That is the expected not-yet-filed Codex half, not a fold finding.

I independently reproduced the citation census:

```
7840a3be
total 95 in_file 56 cross_file 39 resolving 83 blank 10 past_eof 2 broken 12
63093d7f
total 94 in_file 56 cross_file 38 resolving 83 blank 9 past_eof 2 broken 11
```

I also measured the five new `codex-review` mutations in an isolated staged `HARNESS_TREE`, after a green control:

```
stage_problems []
control_rc 0
control_tail 115/115 passed
chosen 5
ok True ... survivors []
```

The manifest count claims also match:

```
codex-review manifest entries 21
EXPECTED codex-review 21
EXPECTED sum 986
EXPECTED files 53
```

Findings:

High — STRUCTURAL — `run_token` is not a collision-free allocator; I produced two different prompts at the same HEAD with the same verdict path.

Premise: the fold claims “different prompt or different HEAD = different token” and “Two DIFFERENT reviews differ in prompt text and so cannot collide however `--out` is named.”

Code:

`scripts/codex-review.py:239`
```
    **What the identity is, stated so a reader can predict it:** the same HEAD and the same prompt
```

`scripts/codex-review.py:241`
```
    land on its own testimony rather than accumulating debris. Two DIFFERENT reviews, which is the
```

`scripts/codex-review.py:242`
```
    H1 scenario, differ in prompt text and so cannot collide however `--out` is named. A review of a
```

`scripts/codex-review.py:248`
```
    h = hashlib.sha256()
```

`scripts/codex-review.py:251`
```
    h.update(prompt_text.encode("utf-8"))
```

`scripts/codex-review.py:252`
```
    return h.hexdigest()[:8]
```

`scripts/codex-review.py:276`
```
    if run_id:
```

`scripts/codex-review.py:277`
```
        stem = f"{stem}.{run_id}"
```

`scripts/codex-review.py:278`
```
    return os.path.join(REPO_ROOT, VERDICT_DIR, f"{stem}.verdict.json")
```

`scripts/codex-review.py:573`
```
        with open(path, "w", encoding="utf-8") as f:
```

Measurement:

```
$ python3 - <<'PY'
import hashlib, random, string
head='63093d7f41eb94922abb18a3c10d34adb488aaff'
seen={}
chars=string.ascii_letters+string.digits
for i in range(1,500000):
    prompt='review prompt '+''.join(random.choice(chars) for _ in range(16))
    h=hashlib.sha256(); h.update(head.encode()); h.update(b'\x00'); h.update(prompt.encode())
    tok=h.hexdigest()[:8]
    old=seen.get(tok)
    if old and old != prompt:
        print('collision_at', i); print('token', tok); print('prompt1', old); print('prompt2', prompt)
        break
    seen[tok]=prompt
PY
collision_at 188568
token f70aae64
prompt1 review prompt 2JJzjcp8q9CgQoO7
prompt2 review prompt kqveHC1UBOewEOKU
```

And against the shipped functions:

```
f70aae64 r.f70aae64.verdict.json 'review prompt 2JJzjcp8q9CgQoO7'
f70aae64 r.f70aae64.verdict.json 'review prompt kqveHC1UBOewEOKU'
paths_equal True
```

The other collision shapes also remain:

```
'same prompt' b43734b2 r.b43734b2.verdict.json
'same prompt' b43734b2 r.b43734b2.verdict.json
'' 5b8a5a8a r.5b8a5a8a.verdict.json
same-prompt distinct subjects collide? True
empty prompts collide? True
omit run_id collision? True
```

Why High: this is the exact class the fold says it closed: two different reviews using the documented `--out "$(mktemp -d)/r.md"` shape can still derive the same untracked verdict path, and `write_verdict` overwrites it. The probability is no longer abstract: 8 hex chars is a 32-bit namespace and I found a collision in seconds.

Proposed fix: stop claiming “cannot collide” from an 8-hex digest. Use a much longer token and include a real unique run identity, such as an explicit `--run-id` / prompt-file identity, or refuse generic stems unless the caller supplies uniqueness. A pure function of only `HEAD + prompt text` cannot distinguish two genuinely different reviews with identical prompt text.

What I could not measure:

I did not run `python3 scripts/check-plan-code.py --mutate .`; the prompt explicitly forbade it. I therefore do not independently verify the coordinator’s full-sweep claim of `53 files, 986 mutations, 986 killed, 986 attributed, 0 survivors`.
