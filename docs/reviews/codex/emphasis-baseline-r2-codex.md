<!-- codex-review: model=gpt-5.5 -->

START HEAD: `72df637bb99620c3d018023f32ad8607aa0e9360`  
END HEAD: `72df637bb99620c3d018023f32ad8607aa0e9360`  
HEAD unchanged; round stands. Working tree had unrelated untracked review docs; I did not touch them.

**Findings**

**Low / Transitional — the fold’s mutation/comment overstates the decorated population as “every served page.”**  
Premise: `scripts/explainer-serve.py:1683-1684` says severing `body = decorate_html(body)` made “EVERY served page” lose the live-reload client. The manifest repeats it at `scripts/mutations/explainer-serve.json:509`: “every served page loses the live-reload client.”

Measurement: driving real `do_GET` with a stubbed `_send` showed:

```text
/probe.html 200 text/html; charset=utf-8 reload=True
/           200 text/html; charset=utf-8 reload=False
/src/x.md   200 text/html; charset=utf-8 reload=False strong=True
```

That matches the code: `/` returns `index_html(ROOT).encode()` at `scripts/explainer-serve.py:1151`; `/src/` returns `source_shell(...).encode()` at `scripts/explainer-serve.py:1231`; only the static `.html` branch calls `decorate_html(body)` at `scripts/explainer-serve.py:1239-1240`.

Why Low: the old Blocking is closed for the static `.html` call site, but the executable evidence now teaches a broader contract than the server actually has. This matters because round 1’s Medium 5 was specifically `/src/` serving `text/html` with `<strong>` while bypassing decoration. The CSS part is moot after withdrawal; the live-reload part is still outside the contract and should not be described as covered.

Proposed fix: rename the mutation/comment to “every static `.html` page” or explicitly document that `/` and `/src/` are outside the decoration/live-reload contract. If they are meant to be inside it, decorate all `text/html` exits and add cases for `/` and `/src/`.

**Other Measurements**

`python3 scripts/explainer-serve.py --self-test` passed: `206/206`.

Severing `body = decorate_html(body)` in a scratch copy failed the named case: `205/206 passed`.

Harness-path attacks in scratch copies all failed red, not falsely green: deleting the sandbox `ROOT` rebind, making `_send` capture an empty body, and writing the wrong fixture each produced `204/206`.

`python3 scripts/check-selftest-counts.py` passed: all 50 declared script counts verified.

`python3 scripts/check-plan-code.py --self-test` passed: `131/131`.

`python3 scripts/check-plan-code.py --mutate .` passed: `57 file(s), 1179 mutation(s), 1179 killed`.

Manifest count independently parsed as 47 entries. The withdrawn `BASELINE_CSS`/`--emph` strings remain only in review/backlog historical text; I found no generated page carrying the injected style.

NOT CONVERGED: 0 Blocking · 0 High · 0 Medium · 1 Low
