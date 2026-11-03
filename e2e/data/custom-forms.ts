// Shared between custom-forms.setup.ts and custom-forms.spec.ts. Playwright refuses to let a
// spec import a setup file, so the seeded identifiers live here.

export const CUSTOM_FORMS_EVENT_ROUTE = "custom-forms-e2e"

export const MEMBERS_ONLY_FORM_ROUTE = "members-only"
export const CLOSED_FORM_ROUTE = "closed-feedback"
export const CLOSED_FORM_TITLE = "Feedback Closed"
export const CLOSED_FORM_MESSAGE = "Feedback for this event is no longer accepted."

// Registration questions are answered by a website user, the way attendees book.
export const ATTENDEE_EMAIL = "form-attendee-e2e@buzz.test"
export const ATTENDEE_PASSWORD = "Attendee@123"
export const ATTENDEE_STATE_PATH = "e2e/.auth/form-attendee.json"
export const BOOKING_QUESTION = { label: "Company", fieldname: "company" }
export const ATTENDEE_QUESTION = { label: "Dietary preference", fieldname: "dietary_preference" }
