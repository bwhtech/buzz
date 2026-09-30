import { useCall } from "frappe-ui"

import type { UserInfo } from "@/types"

// Uncached: the session user is not known until this answers, so there is no user to key by.
export const userResource = useCall<UserInfo>({
	url: "/api/v2/method/buzz.api.account.get_user_info",
	immediate: false,
})

let pending: Promise<unknown> | null = null

// Session info doesn't change between navigations, so it is fetched once per app load.
// Anything that changes it (login, profile and preference saves) calls reload() itself.
// A failed fetch clears the memo so the next navigation retries.
export function loadUser() {
	pending ??= userResource.fetch().then((user) => {
		if (userResource.error) pending = null
		return user
	})
	return pending
}
