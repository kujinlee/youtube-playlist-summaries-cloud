'use client';

import { createContext, useContext, type ReactNode } from 'react';

/** Which backend + identity a client component's data operations are scoped to.
 *  Local: filesystem-backed, addressed by outputFolder (the currently viewed playlist
 *  folder) and baseOutputFolder (the vault root, used for folder-picker relative paths).
 *  Cloud: Postgres-backed, addressed by the playlists.id UUID. */
export type Scope =
  | { mode: 'local'; outputFolder: string; baseOutputFolder: string }
  | { mode: 'cloud'; playlistId: string };

const ScopeContext = createContext<Scope | null>(null);

export function ScopeProvider({ scope, children }: { scope: Scope; children: ReactNode }) {
  return <ScopeContext.Provider value={scope}>{children}</ScopeContext.Provider>;
}

/** Reads the current Scope from context. Throws if called outside a ScopeProvider —
 *  every shared component that fetches data must be mounted under one. */
export function useScope(): Scope {
  const scope = useContext(ScopeContext);
  if (!scope) {
    throw new Error('useScope must be used within a ScopeProvider');
  }
  return scope;
}
