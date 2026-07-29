// Shared between check-in.setup.ts and check-in.spec.ts. Playwright refuses to let a spec
// import a setup file, so the seeded identifiers live here.

export const CHECK_IN_EVENT_TITLE = "E2E Check-in Event";
export const CHECK_IN_EVENT_ROUTE = "check-in-e2e";
export const CHECK_IN_ATTENDEE_NAME = "Checkin Attendee";
export const CHECK_IN_ATTENDEE_EMAIL = "checkin-attendee@buzz.test";

export const FRONTDESK_EMAIL = "frontdesk-e2e@buzz.test";
export const FRONTDESK_PASSWORD = "Frontdesk@123";
export const FRONTDESK_STATE_PATH = "e2e/.auth/frontdesk.json";

// A second identity, deliberately without the role. Administrator would not do: it holds every
// role, so the access-denied path would never render for it.
export const NO_ROLE_EMAIL = "no-frontdesk-e2e@buzz.test";
export const NO_ROLE_PASSWORD = "NoFrontdesk@123";
export const NO_ROLE_STATE_PATH = "e2e/.auth/no-frontdesk.json";
