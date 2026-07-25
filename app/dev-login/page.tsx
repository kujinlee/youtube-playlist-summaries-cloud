import { notFound } from 'next/navigation';
import { devLoginEnabled } from '@/lib/supabase/dev-login';
import { DevLoginForm } from '@/components/DevLoginForm';

// Env-gated dev affordance (#13). force-dynamic so the gate is evaluated per request and
// never prerendered with a frozen decision. In prod DEV_LOGIN_ENABLED is unset → 404.
export const dynamic = 'force-dynamic';

export default async function DevLoginPage() {
  if (!devLoginEnabled()) {
    notFound();
  }
  return <DevLoginForm />;
}
