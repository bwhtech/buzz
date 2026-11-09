// Shared between registration-requests.setup.ts and registration-requests.spec.ts, since
// Playwright refuses to let a spec import a setup file.

export const REQUESTS_EVENT_TITLE = "E2E Registration Requests Event"
export const REQUESTS_EVENT_ROUTE = "registration-requests-e2e"
export const REQUESTS_TICKET_TITLE = "Requests E2E Ticket"

export const REQUESTER_PASSWORD = "Requester@123"
export const REQUESTER = {
	email: "registration-requester-e2e@buzz.test",
	name: "Request Guest",
	statePath: "e2e/.auth/registration-requester.json",
}
