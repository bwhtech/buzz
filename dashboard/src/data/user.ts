import { createResource } from "frappe-ui"

import type { UserInfo } from "@/types"

export const userResource = createResource<UserInfo>({
	url: "buzz.api.account.get_user_info",
	cache: "User",
})

let pending: Promise<unknown> | null = null

// Session info doesn't change between navigations, so it is fetched once per app load.
// Anything that changes it (login, profile and preference saves) calls reload() itself.
// A failed fetch clears the memo so the next navigation retries.
export function loadUser() {
	pending ??= userResource.fetch().catch(() => {
		pending = null
		return null
	})
	return pending
}
