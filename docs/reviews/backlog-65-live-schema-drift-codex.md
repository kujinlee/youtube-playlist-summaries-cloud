<!-- codex-review: model=gpt-5.5 -->

**Findings**

**High** — `unexpected()` has an ambiguous relation parser for dotted identifiers, causing false positives on legitimate databases.  
[scripts/check-live-schema.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-live-schema.py:286) parses `kind:relation.object` with `rest.split(".", 1)[0]`. But [m4_catalog.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/m4_catalog.py:348), [m4_catalog.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/m4_catalog.py:370), [m4_catalog.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/m4_catalog.py:415), and [m4_catalog.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/m4_catalog.py:424) concatenate raw `relname || '.' || object_name` with no quoting or escaping.  
Trigger: M4 owns `workspaces`; a legitimate non-M4 quoted table exists as `public."workspaces.audit"` with column `seen`. Catalog string shape is `col:workspaces.audit.seen@...`; `unexpected()` attributes it to relation `workspaces` and flags drift even though the object belongs to `"workspaces.audit"`, not `workspaces`. This is exactly the kind of false alarm that can get a production gate disabled.

**Medium** — same parser produces false negatives for owned relations whose names contain dots.  
[scripts/check-live-schema.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-live-schema.py:222) derives owned relations directly from `table:`/`view:` entries, so `table:foo.bar@...` yields owned relation `foo.bar`. But [scripts/check-live-schema.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-live-schema.py:288) parses `col:foo.bar.extra@...` as relation `foo`, so it silently misses the added object.  
Trigger: manifest contains `table:foo.bar@...`; live contains all manifest entries plus `col:foo.bar.extra@...`. `unexpected()` returns empty.

**Low** — mutation 3’s bound assertions can pass without proving the bound mutation landed.  
The main added-column mutation checks before/after counts at [scripts/mutate-live-schema-check.sh](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/mutate-live-schema-check.sh:239), so that part is load-bearing. But the later bound probes do not verify their SQL succeeded: foreign column add/drop and index create/drop run at [scripts/mutate-live-schema-check.sh](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/mutate-live-schema-check.sh:261) and [scripts/mutate-live-schema-check.sh](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/mutate-live-schema-check.sh:267), with stderr swallowed and no postcondition.  
Trigger: if `create index m4_mut_idx ...` fails because that name already exists, the next gate can still pass on an unchanged DB and report the index bound as proved.

**Non-Findings / Proved From Code**

Absent polarity is unchanged for backlog 65: [scripts/check-live-schema.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-live-schema.py:308) returns `not survivors(...)` before the present-mode `unexpected()` path at line 310. Reporting also uses `residue(..., "absent")`, which remains `survivors(...)` at line 319.

View ownership is intendedly included: `owned_relations()` includes `view:` entries at lines 231-233, and `CATALOG_SQL` emits view columns for `relkind in ('r','v','m','p','f')`. The dotted-name ambiguity above still applies.

I ran `python3 scripts/check-live-schema.py --self-test`: `87/87` passed. I did not run the full mutation harness against Docker/Postgres.
