// Shared between custom-forms.setup.ts and custom-forms.spec.ts. Playwright refuses to let a
// spec import a setup file, so the seeded identifiers live here.

export const CUSTOM_FORMS_EVENT_ROUTE = "custom-forms-e2e";

export const MEMBERS_ONLY_FORM_ROUTE = "members-only";
export const CLOSED_FORM_ROUTE = "closed-feedback";
export const CLOSED_FORM_TITLE = "Feedback Closed";
export const CLOSED_FORM_MESSAGE = "Feedback for this event is no longer accepted.";
