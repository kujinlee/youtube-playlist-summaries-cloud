import CloudApp from '@/components/cloud/CloudApp';
import LocalApp from '@/components/local/LocalApp';
import { getPageSession } from '@/lib/supabase/page-session';

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
