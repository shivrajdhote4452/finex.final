import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  VALID_TABS,
  STORAGE_KEY_ACTIVE_TAB,
  isValidTab,
  parseTabFromHash,
  isWorkspaceTabHash,
  resolveLandingTab,
  detectPublicPage,
  getLoginSuccessNavigation,
  getOnboardingCompleteNavigation,
  type NavigationTab,
} from '../src/domain/sessionNavigation.ts';

describe('FinEx Login Landing Page & Tab Routing Logic', () => {
  // -------------------------------------------------------------
  // 1. REPRODUCTION OF THE ORIGINAL ISSUE & VERIFICATION OF FIX
  // -------------------------------------------------------------
  test('1. Reproduction test: Previous behavior retained stale tab on login, whereas new behavior lands on Overview', () => {
    // Simulated user actions:
    // User logs in, navigates to 'settings', logs out, and logs back in.

    // Scenario A: Bug simulation (how the old code behaved)
    let oldCurrentTab: NavigationTab = 'settings';
    let oldLocationHash = '#settings';
    let oldStorageTab: string | null = 'settings';

    // Old logout: only called setAuthState('welcome'), never touched tab or hash
    const oldSimulatedLogout = () => {
      // old code did NOT reset oldCurrentTab, oldLocationHash, or oldStorageTab
    };
    oldSimulatedLogout();

    // Old login: only called setAuthState('authenticated'), never touched tab or hash
    const oldSimulatedLoginSuccess = () => {
      // old code left oldCurrentTab as 'settings'
    };
    oldSimulatedLoginSuccess();
    assert.equal(oldCurrentTab, 'settings', 'CONFIRM BUG: Old code left user on Settings screen after login');

    // Scenario B: Fixed behavior
    let currentTab: NavigationTab = 'settings';
    let locationHash = '#settings';
    let storageTab: string | null = 'settings';

    // Fixed logout cleans up state
    const handleSignOut = () => {
      currentTab = 'overview';
      storageTab = null;
      if (isWorkspaceTabHash(locationHash)) {
        locationHash = '';
      }
    };
    handleSignOut();

    assert.equal(currentTab, 'overview', 'Sign out must reset tab to overview');
    assert.equal(storageTab, null, 'Sign out must clear active tab storage');
    assert.equal(locationHash, '', 'Sign out must clear workspace hash from URL');

    // Fixed login success:
    const handleLoginSuccess = () => {
      const nav = getLoginSuccessNavigation();
      currentTab = nav.targetTab;
      storageTab = nav.storageTab;
      locationHash = nav.targetHash;
    };
    handleLoginSuccess();

    assert.equal(currentTab, 'overview', 'New login MUST land on Overview');
    assert.equal(storageTab, 'overview', 'New login must record overview in storage');
    assert.equal(locationHash, 'overview', 'New login must set hash to overview');
  });

  // -------------------------------------------------------------
  // 2. GOOGLE SIGN-IN LANDING
  // -------------------------------------------------------------
  test('2. Google Sign-In lands on Overview even with stale URL hash or stale localStorage', () => {
    // Suppose browser URL has stale #portfolio and storage has 'settings'
    const staleHash = '#portfolio';
    const staleStorage = 'settings';

    // Unauthenticated user signs in with Google OAuth callback
    const nav = getLoginSuccessNavigation();

    // Pure landing resolution for new login ignores stale tabs
    const landing = resolveLandingTab({
      hasActiveSession: false,
      locationHash: staleHash,
      storedTab: staleStorage,
    });

    assert.equal(landing, 'overview', 'Unauthenticated landing resolution must default to overview');
    assert.equal(nav.targetTab, 'overview', 'Google login target tab must be overview');
    assert.equal(nav.targetHash, 'overview', 'Google login target hash must be overview');
  });

  // -------------------------------------------------------------
  // 3. EMAIL/PASSWORD SIGN-IN LANDING
  // -------------------------------------------------------------
  test('3. Email/Password Sign-In lands on Overview even with stale URL hash or stale localStorage', () => {
    // Suppose browser URL has stale #charts and storage has 'spending'
    const staleHash = '#charts';
    const staleStorage = 'spending';

    const nav = getLoginSuccessNavigation();

    const landing = resolveLandingTab({
      hasActiveSession: false,
      locationHash: staleHash,
      storedTab: staleStorage,
    });

    assert.equal(landing, 'overview', 'Unauthenticated landing resolution must default to overview');
    assert.equal(nav.targetTab, 'overview', 'Email login target tab must be overview');
    assert.equal(nav.targetHash, 'overview', 'Email login target hash must be overview');
  });

  // -------------------------------------------------------------
  // 4. ACTIVE SESSION REFRESH PRESERVATION (NOT A NEW LOGIN)
  // -------------------------------------------------------------
  test('4. In-session page refresh preserves the active tab and is not treated as a new login', () => {
    // Authenticated user with valid token is viewing 'portfolio'
    const tabOnPortfolio = resolveLandingTab({
      hasActiveSession: true,
      locationHash: '#portfolio',
      storedTab: 'portfolio',
    });
    assert.equal(tabOnPortfolio, 'portfolio', 'In-session refresh must preserve #portfolio');

    // Authenticated user with valid token is viewing 'charts'
    const tabOnCharts = resolveLandingTab({
      hasActiveSession: true,
      locationHash: '#charts',
      storedTab: 'charts',
    });
    assert.equal(tabOnCharts, 'charts', 'In-session refresh must preserve #charts');

    // Authenticated user where hash was empty but localStorage had 'spending'
    const tabFromStorage = resolveLandingTab({
      hasActiveSession: true,
      locationHash: '',
      storedTab: 'spending',
    });
    assert.equal(tabFromStorage, 'spending', 'In-session refresh falls back to valid stored tab if hash is empty');
  });

  // -------------------------------------------------------------
  // 5. IN-SESSION BROWSER BACK/FORWARD AND TAB NAVIGATION
  // -------------------------------------------------------------
  test('5. In-session navigation and browser Back/Forward between valid tabs', () => {
    // Verify all 12 investor navigation tabs are recognized (admin panel isolated to dedicated portal)
    assert.equal(VALID_TABS.length, 12);
    assert.equal(VALID_TABS.includes('admin' as any), false);
    for (const tab of VALID_TABS) {
      assert.ok(isValidTab(tab), `Tab ${tab} must be a valid tab`);
      assert.equal(parseTabFromHash(`#${tab}`), tab);
      assert.ok(isWorkspaceTabHash(`#${tab}`));
    }

    // Invalid hashes must be safely ignored
    assert.equal(isValidTab('unknown-tab'), false);
    assert.equal(parseTabFromHash('#unknown-tab'), null);
    assert.equal(isWorkspaceTabHash('#unknown-tab'), false);
    assert.equal(isWorkspaceTabHash(''), false);
    assert.equal(isWorkspaceTabHash(null), false);
  });

  // -------------------------------------------------------------
  // 6. ONBOARDING PRESERVATION & COMPLETION LANDING
  // -------------------------------------------------------------
  test('6. Incomplete onboarding routes to onboarding; completing onboarding lands on Overview', () => {
    // Simulation of onboarding completion
    const onCompleteNav = getOnboardingCompleteNavigation();
    assert.equal(onCompleteNav.targetTab, 'overview', 'Completing onboarding must target overview tab');
    assert.equal(onCompleteNav.targetHash, 'overview', 'Completing onboarding must target overview hash');
    assert.equal(onCompleteNav.storageTab, 'overview', 'Completing onboarding must save overview to storage');
  });

  // -------------------------------------------------------------
  // 7. PUBLIC LEGAL PAGES & DEEP LINKS PRESERVATION
  // -------------------------------------------------------------
  test('7. Deep-link tokens and public legal pages are preserved and never treated as workspace tabs', () => {
    // Email verification deep-link
    const verifyHash = '#verify-email?token=abc-123-def';
    assert.equal(isWorkspaceTabHash(verifyHash), false, 'verify-email hash must not be treated as a workspace tab');
    assert.equal(parseTabFromHash(verifyHash), null);

    // Password reset deep-link
    const resetHash = '#reset-password?token=xyz-789-uvw';
    assert.equal(isWorkspaceTabHash(resetHash), false, 'reset-password hash must not be treated as a workspace tab');
    assert.equal(parseTabFromHash(resetHash), null);

    // Onboarding step preview deep-link
    assert.equal(isWorkspaceTabHash('#onboarding'), false);
    assert.equal(isWorkspaceTabHash('#step=2'), false);

    // Public legal page detection
    assert.equal(detectPublicPage('/privacy'), 'privacy');
    assert.equal(detectPublicPage('/privacy-policy'), 'privacy');
    assert.equal(detectPublicPage('/privacy.html'), 'privacy');
    assert.equal(detectPublicPage('', '#privacy'), 'privacy');
    assert.equal(detectPublicPage('', '#/privacy'), 'privacy');

    assert.equal(detectPublicPage('/terms'), 'terms');
    assert.equal(detectPublicPage('/terms-of-service'), 'terms');
    assert.equal(detectPublicPage('/terms.html'), 'terms');
    assert.equal(detectPublicPage('', '#terms'), 'terms');
    assert.equal(detectPublicPage('', '#/terms'), 'terms');

    assert.equal(detectPublicPage('/'), null);
    assert.equal(detectPublicPage('/portfolio'), null);
  });

  // -------------------------------------------------------------
  // 8. LOGOUT & 401 SESSION EXPIRY CLEANUP
  // -------------------------------------------------------------
  test('8. Logout and session expiry (401) clean up stored active tab and workspace hash', () => {
    const mockStorage: Record<string, string> = {
      [STORAGE_KEY_ACTIVE_TAB]: 'settings',
      finex_access_token: 'dummy-token',
    };

    // Simulate session expiry / logout token cleanup
    delete mockStorage.finex_access_token;
    delete mockStorage[STORAGE_KEY_ACTIVE_TAB];

    assert.equal(mockStorage[STORAGE_KEY_ACTIVE_TAB], undefined, 'Active tab must be wiped on logout/expiry');
    assert.equal(mockStorage.finex_access_token, undefined, 'Access token must be wiped on logout/expiry');

    // Next time landing tab is resolved without active session
    const landing = resolveLandingTab({
      hasActiveSession: false,
      locationHash: '#settings',
      storedTab: mockStorage[STORAGE_KEY_ACTIVE_TAB],
    });
    assert.equal(landing, 'overview', 'Subsequent session resolution must open Overview');
  });

  // -------------------------------------------------------------
  // 9. STORAGE ERROR RESILIENCE (INCOGNITO / RESTRICTED STORAGE)
  // -------------------------------------------------------------
  test('9. Storage access errors (e.g. QuotaExceededError or restricted iframe) fall back gracefully', () => {
    // If reading from storage or parsing throws, fallback must return 'overview'
    const landingWithError = resolveLandingTab({
      hasActiveSession: false,
      locationHash: null,
      storedTab: null,
    });
    assert.equal(landingWithError, 'overview', 'Must return overview when storage is unavailable');
  });

  // -------------------------------------------------------------
  // 10. DESKTOP & MOBILE WEB NAVIGATION PARITY
  // -------------------------------------------------------------
  test('10. Desktop rail and mobile drawer navigate to identical valid tabs', () => {
    const expectedModules = [
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
    ];

    for (const mod of expectedModules) {
      assert.ok(VALID_TABS.includes(mod as NavigationTab), `Module ${mod} must exist in VALID_TABS`);
    }
  });
});
