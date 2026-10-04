// Shared between user-settings.setup.ts and user-settings.spec.ts. Playwright refuses to let
// a spec import a setup file, so the seeded identifiers live here.

// The spec edits the session user's own profile, so it runs as a user of its own rather than
// the shared session: on CI that is FRAPPE_USER, whose name other specs assert on, and
// locally it is Administrator, whom Frappe only lets Administrator write.
export const SETTINGS_EMAIL = "settings-user-e2e@buzz.test"
export const SETTINGS_PASSWORD = "Settings@123"
export const SETTINGS_FIRST_NAME = "Settings"
export const SETTINGS_STATE_PATH = "e2e/.auth/settings-user.json"
