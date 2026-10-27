// Shared between approval-registration.setup.ts and approval-registration.spec.ts. Playwright
// refuses to let a spec import a setup file, so the seeded identifiers live here.

export const APPROVAL_EVENT_TITLE = "E2E Approval Event"
export const APPROVAL_EVENT_ROUTE = "approval-e2e"
export const APPROVAL_TICKET_TITLE = "Approval Ticket"

// One requester per scenario: a second pending request from the same user is refused.
export const REQUESTER_PASSWORD = "Requester@123"
export const REQUESTERS = {
	approved: {
		email: "approval-approved-e2e@buzz.test",
		name: "Approved Requester",
		statePath: "e2e/.auth/approval-approved.json",
	},
	declined: {
		email: "approval-declined-e2e@buzz.test",
		name: "Declined Requester",
		statePath: "e2e/.auth/approval-declined.json",
	},
	kept: {
		email: "approval-kept-e2e@buzz.test",
		name: "Kept Requester",
		statePath: "e2e/.auth/approval-kept.json",
	},
}
