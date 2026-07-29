// Shared between tickets.setup.ts and tickets.spec.ts. Playwright refuses to let a spec import
// a setup file, so the seeded identifiers live here.

export const TICKETS_EVENT_TITLE = "E2E Tickets Event";
export const TICKETS_EVENT_ROUTE = "tickets-e2e";

// The attendee owns the ticket. get_ticket_details refuses anyone else, so the spec has to run
// as this user rather than the shared Administrator session.
export const ATTENDEE_EMAIL = "tickets-attendee-e2e@buzz.test";
export const ATTENDEE_PASSWORD = "Attendee@123";
export const ATTENDEE_STATE_PATH = "e2e/.auth/tickets-attendee.json";

export const ADD_ON_TITLE = "E2E Meal Preference";
export const ADD_ON_OPTIONS = ["Veg", "Non-veg"];
