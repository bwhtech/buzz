import { createResource } from "frappe-ui"

export const userResource = createResource({
	url: "buzz.api.account.get_user_info",
	cache: "User",
})
