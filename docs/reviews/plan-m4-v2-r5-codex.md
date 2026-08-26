<!-- codex-review: model=gpt-5.5 -->

**Findings**

**Blocking: `--expect-absent` still blesses M4-named residue if the digest differs.**

Premise:
- [scripts/check-live-schema.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-live-schema.py:124): `if mode == "absent":`
- [scripts/check-live-schema.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-live-schema.py:125): `return not (live & manifest)`
- [scripts/check-live-schema.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-live-schema.py:131): `return (live & manifest) if mode == "absent" else (manifest - live)`

Executed against throwaway DB `m4_round5_absent_digest_probe`, then dropped:
```text
create function public.corrections_hash_of(p_corrections text) returns text
  language sql as $$ select 'wrong'; $$;

check-live-schema --expect-absent status=0
live schema [local container db 'm4_round5_absent_digest_probe']: M4 is ABSENT as expected — checked all 161 objects...
live fn row:
fn:corrections_hash_of(p_corrections text)@05490a35e55794ed3fd2fd32459d9cb8
```

That is the exact mirror of r4: present mode moved from names to digests, but absent mode also moved, and now a surviving M4 object with a different definition is invisible. `--expect-absent` should reject by M4 object name, not by full `name@digest`.

**Blocking: the digest predicate does not cover behavior-critical catalog state.**

Premise:
- [scripts/m4_catalog.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/m4_catalog.py:53): `select 'table:' || c.relname`
- [scripts/m4_catalog.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/m4_catalog.py:60): `select 'col:' || table_name || '.' || column_name || '@' ||`
- [scripts/m4_catalog.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/m4_catalog.py:71): `select 'fn:' || p.proname || '(' || pg_get_function_identity_arguments(p.oid) || ')' || '@' ||`
- [scripts/m4_catalog.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/m4_catalog.py:72): `md5(coalesce(p.prosrc, ''))`
- [scripts/m4_catalog.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/m4_catalog.py:81): `select 'idx:' || indexname || '@' || md5(indexdef) from pg_indexes where schemaname = 'public'`
- [scripts/m4_catalog.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/m4_catalog.py:83): `select 'pol:' || tablename || '.' || policyname || '@' ||`
- [scripts/m4_catalog.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/m4_catalog.py:84): `md5(cmd || coalesce(roles::text, '') || coalesce(qual, '') || coalesce(with_check, ''))`

Executed RLS sabotage against throwaway DB `m4_round5_rls_probe`, then dropped:
```text
alter table public.video_artifacts disable row level security;

before_disable_rls_status=0
after_disable_rls_status=0
live schema [local container db 'm4_round5_rls_probe']: M4 is PRESENT as expected...
catalog rls state:
video_artifacts: relrowsecurity=false, relforcerowsecurity=true
```

Executed function metadata sabotage against throwaway DB `m4_round5_fnmeta_probe`, then dropped:
```text
alter function public.record_artifact(...) security invoker;
alter function public.record_artifact(...) volatile;
alter function public.record_artifact(...) reset search_path;

after_fnmeta_status=0
function metadata:
f|v|<null>
```

Per-kind blind spots from the selected columns:
- table: RLS enabled/forced, owner, ACL, persistence are invisible.
- column: identity/generated-ness, collation, storage/compression, privileges are invisible.
- function: `security definer`, `search_path`, volatility, owner, ACL are invisible.
- index: `indisvalid` / `indisready` are invisible through `pg_indexes.indexdef`.
- policy: `permissive` vs `restrictive` is invisible; table-level RLS OFF makes all policy digests moot.
- type: only enum labels are digested; owner/grants are invisible.
- trigger: I did not find the requested `WHEN`/`tgtype` hole; `pg_get_triggerdef(...) || tgenabled` should cover those.

Negative search executed for the blind fields:
```text
rg -n "relrowsecurity|relforcerowsecurity|prosecdef|provolatile|proconfig|proowner|relowner|convalidated|indisvalid|indisready|attidentity|attgenerated|relacl|proacl|GRANT|REVOKE|permissive" scripts/m4_catalog.py scripts/check-live-schema.py scripts/gen-m4-manifest.py docs/superpowers/specs/m4/live-manifest.txt
# no matches
```

**High: `--prod` leaks the database URL to host `ps`, and “read-only” is not enforced.**

Premise:
- [scripts/m4_catalog.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/m4_catalog.py:104): `Same source `check-anon-exposure.py` uses. Read-only by construction: `claude_ro` holds no write`
- [scripts/m4_catalog.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/m4_catalog.py:133): `return ["docker", "exec", "-i", "-e", f"PGU={url}", container,`
- [scripts/m4_catalog.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/m4_catalog.py:134): `"bash", "-c", 'psql "$PGU" -tAq -v ON_ERROR_STOP=1']`
- [scripts/check-live-schema.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-live-schema.py:289): `subject = "PRODUCTION (read-only claude_ro)" if url else f"local container db '{a.database}'"`

Executed harmless `docker exec ... sleep` with a fake secret URL:
```text
ps:
docker exec -i -e PGU=postgresql://claude_ro:[REDACTED]@example.invalid:5432/postgres?sslmode=require&x=semi;dollar$HOME ...
```

Shell metacharacters stayed data, so I do not have a shell-injection finding. But credentials are exposed in process args. Also, the code accepts any `CLAUDE_RO_DATABASE_URL`; the only search hits for read-only enforcement are the env read and label, not a `current_user`, role, privilege, or transaction-read-only check.

**Medium: manifest integrity authenticates the unique object set, not the file.**

Premise:
- [scripts/check-live-schema.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-live-schema.py:88): `objs = {ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")}`
- [scripts/check-live-schema.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-live-schema.py:94): `claimed_n = re.search(r"^#\s*objects:\s*(\d+)\s*$", text, re.M)`
- [scripts/check-live-schema.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-live-schema.py:105): `actual = hashlib.sha256(("\n".join(sorted(objs)) + "\n").encode()).hexdigest()`

Executed with a temp manifest containing a duplicate object plus contradictory second headers:
```text
load_manifest passed: 161 unique objects
duplicate_count=2
second_header_lines=2
```

So the header blocks truncation, but not duplicate body lines or later contradictory headers. That is weaker than “the file matches its own header.”

**Medium: r4’s production instructions still do not use the new `--prod` path, and the plan still claims 9 checks.**

Premise:
- [docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md:963): `python3 scripts/check-live-schema.py --expect-present   # pointed at prod`
- [docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md:1003): `1. `M4_PHASE=post ./scripts/check-schema-gates.sh` — **nine checks, numbered 0-8, all green**:`
- [scripts/check-schema-gates.sh](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-schema-gates.sh:30): `run "1/8  schema + assertions (verify-schema.sh)"      "$SPEC/verify-schema.sh"`
- [scripts/check-schema-gates.sh](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-schema-gates.sh:77): `run "8/8  live catalog matches M4_PHASE=${M4_PHASE:-pre}" \`

Search executed:
```text
rg -n "check-live-schema\\.py --expect-present|check-live-schema\\.py --prod|--expect-present.*--prod|9 checks|numbered 0-8" docs scripts .github .claude package.json -S
```

It found the stale prod command and no `check-live-schema.py --prod` production instruction. The coordinator says B3 is fixed, but the plan still tells the human to run the local default while commenting “pointed at prod.”

**What I Ran**

```text
python3 scripts/check-live-schema.py --self-test
# 24/24, status=0

python3 scripts/gen-m4-manifest.py --check
# manifest current, 161 objects, status=0

./scripts/mutate-live-schema-check.sh
# every mutation caught, status=0

M4_PHASE=pre ./scripts/check-schema-gates.sh
# gates 7 and 8 ran; final status=1 because gates 3 and 4 are red

scratch probes:
m4_round5_absent_digest_probe
m4_round5_rls_probe
m4_round5_fnmeta_probe
# all dropped by trap/cleanup

git status --short
# clean
```

**Non-Findings / Checked**

`forbidden()` matching by name is consistent for the listed ADR-0011 names:
- [scripts/check-live-schema.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-live-schema.py:154): `return {o for o in live if name_of(o) in ADR0011_REMOVED}`

The self-test covers any digest for the removed sync function and passed. I did not find a digest-based evasion for those exact ADR object names.

NOT CONVERGED
