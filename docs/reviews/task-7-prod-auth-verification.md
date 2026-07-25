# Task 7 — Production Supabase Auth Verification (#13 Layer-1 boundary)

**Verified: 2026-07-25 (user, Supabase dashboard).**

## Observed state — production project `uykwcybxqgewmbltroxf`
Authentication → Providers → **Email**:
- **Enable email provider: OFF** ← the load-bearing setting. Email-based sign-up and log-in are
  **disabled** in production.
- Secure email change: ON (unrelated to login — governs the email-change confirmation flow for
  existing users; the safer setting, no bearing on the invariant).

## Conclusion
The invariant's "email/password impossible to **use** in production" clause **holds**. Because
the email provider is disabled, a direct `signInWithPassword` call against the prod Supabase
Auth endpoint (reachable with the public anon key that ships in every prod bundle) is rejected
at the provider level — independent of the `/dev-login` UI gate.

- **Layer 1 (authorization boundary):** prod email provider OFF ✅ — this is the real control.
- **Layer 2 (UI, defense-in-depth):** `/dev-login` 404s in prod (`DEV_LOGIN_ENABLED` unset) ✅.

Both layers confirmed. #13's security requirement is met; the remaining gate is the merge.

**Standing note:** if the prod email provider is ever re-enabled, revisit this — Layer 2 alone
does not stop the direct-API path. The `docs/deploy.md` post-deploy `/dev-login` 404 smoke check
guards Layer 2; this provider setting guards Layer 1.
