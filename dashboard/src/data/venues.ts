import { createResource } from "frappe-ui"

export interface Venue {
	name: string
	address: string
}

// Plain doctype reads and writes, so they go through frappe.client rather than a buzz
// endpoint. Event Venue carries the team query condition and permission hooks, so the
// team filter below narrows what the picker asks for — it is not what enforces scope.
export const venues = createResource<Venue[]>({
	url: "frappe.client.get_list",
	makeParams: (params: { team: string }) => ({
		doctype: "Event Venue",
		filters: { team: params.team },
		fields: ["name", "address"],
		order_by: "modified desc",
		limit_page_length: 0,
	}),
})

export const createVenue = createResource({
	url: "frappe.client.insert",
	makeParams: (params: { team: string; name: string; address: string }) => ({
		doc: {
			doctype: "Event Venue",
			// Event Venue is autonamed by prompt, so the name is the venue's own.
			__newname: params.name,
			address: params.address,
			team: params.team,
		},
	}),
})
