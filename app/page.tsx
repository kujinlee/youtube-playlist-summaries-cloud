import CloudApp from '@/components/cloud/CloudApp';
import LocalApp from '@/components/local/LocalApp';
import { getPageSession } from '@/lib/supabase/page-session';

// MUST render per request — never statically prerendered. This page dispatches on
// `STORAGE_BACKEND` (a RUNTIME value) and, in cloud mode, reads the per-request session. Without
// this, a build where STORAGE_BACKEND is absent — e.g. Fly, where it is a runtime secret, NOT a
// build arg — takes the `local` branch, which reads no per-request data, so Next bakes the page as
// static LocalApp. That frozen page then serves the LOCAL UI in the cloud forever, ignoring the
// runtime STORAGE_BACKEND=supabase entirely. (2026-07-22 first-deploy failure: a signed-in cloud
// user got LocalApp + the filesystem-path ingest, which 400s in a container.) An authenticated,
// backend-dependent page has no business being static regardless.
export const dynamic = 'force-dynamic';

/**
 * Stage 2a T12 (§3.1): thin server dispatch. Reads `STORAGE_BACKEND` and — in cloud mode
 * only — the current session (read-only, N2) via `lib/supabase/page-session.ts`, then
 * renders one of two client shells. No `'use client'` here, no client-only hooks, and no
 * import of `lib/supabase/server.ts`/`service.ts` — only a serializable `session` prop
 * crosses the server/client boundary.
 */
export default async function Page() {
  const backend = process.env.STORAGE_BACKEND ?? 'local';
  if (backend === 'supabase') {
    const session = await getPageSession();
    return <CloudApp session={session} />;
  }
  return <LocalApp />;
}
