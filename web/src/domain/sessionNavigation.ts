/**
 * Session Navigation & Tab Routing Domain Model.
 *
 * Implements authoritative routing and landing page rules for FinEx:
 * - Successful new logins (Email/Password & Google) always land on Overview.
 * - Active session refreshes preserve the user's active tab.
 * - Workspace tabs are cleared on logout, session expiration (401), or unauthenticated entry.
 * - Deep links (verify-email, reset-password, onboarding) and public legal pages are preserved.
 */

export type NavigationTab =
  | 'overview'
  | 'markets'
  | 'indices'
  | 'charts'
  | 'portfolio'
  | 'transactions'
  | 'ask-finex'
  | 'practice'
  | 'alerts'
  | 'goals'
  | 'spending'
  | 'settings'
  | 'admin';

export const VALID_TABS: readonly NavigationTab[] = [
  'overview',
  'markets',
  'indices',
  'charts',
  'portfolio',
  'transactions',
  'ask-finex',
  'practice',
  'alerts',
  'goals',
  'spending',
  'settings',
  'admin',
] as const;

export const STORAGE_KEY_ACTIVE_TAB = 'finex_active_tab';

export function isValidTab(tab: unknown): tab is NavigationTab {
  return typeof tab === 'string' && (VALID_TABS as readonly string[]).includes(tab);
}

export function parseTabFromHash(hash?: string | null): NavigationTab | null {
  if (!hash) return null;
  const clean = hash.replace(/^#\/?/, '').trim().toLowerCase();
  return isValidTab(clean) ? clean : null;
}

export function isWorkspaceTabHash(hash?: string | null): boolean {
  return parseTabFromHash(hash) !== null;
}

export interface ResolveLandingTabOptions {
  hasActiveSession: boolean;
  locationHash?: string | null;
  storedTab?: string | null;
}

/**
 * Pure function to resolve the landing tab on application load / evaluation.
 * - For active authenticated sessions (e.g. in-session page refresh), honors the current hash or stored tab.
 * - For unauthenticated visitors or newly starting sessions, always defaults to 'overview'.
 */
export function resolveLandingTab({
  hasActiveSession,
  locationHash,
  storedTab,
}: ResolveLandingTabOptions): NavigationTab {
  if (hasActiveSession) {
    const hashTab = parseTabFromHash(locationHash);
    if (hashTab) return hashTab;

    if (isValidTab(storedTab)) return storedTab;
  }
  return 'overview';
}

export type PublicPage = 'privacy' | 'terms' | null;

export function detectPublicPage(pathname = '', hash = ''): PublicPage {
  const normPath = pathname.toLowerCase().replace(/\/$/, '');
  const normHash = hash.toLowerCase().replace(/^#\/?/, '').trim();

  if (
    normPath === '/privacy' ||
    normPath === '/privacy-policy' ||
    normPath === '/privacy.html' ||
    normHash === 'privacy' ||
    normHash === '/privacy'
  ) {
    return 'privacy';
  }

  if (
    normPath === '/terms' ||
    normPath === '/terms-of-service' ||
    normPath === '/terms.html' ||
    normHash === 'terms' ||
    normHash === '/terms'
  ) {
    return 'terms';
  }

  return null;
}

export interface LoginNavigationAction {
  targetTab: NavigationTab;
  targetHash: string;
  storageTab: string;
}

/**
 * Returns the state updates required upon a successful new login (Email or Google).
 * Guarantees that any new login lands squarely on Overview.
 */
export function getLoginSuccessNavigation(): LoginNavigationAction {
  return {
    targetTab: 'overview',
    targetHash: 'overview',
    storageTab: 'overview',
  };
}

/**
 * Returns the state updates required upon completing onboarding.
 * Guarantees that finishing onboarding lands on Overview.
 */
export function getOnboardingCompleteNavigation(): LoginNavigationAction {
  return {
    targetTab: 'overview',
    targetHash: 'overview',
    storageTab: 'overview',
  };
}
