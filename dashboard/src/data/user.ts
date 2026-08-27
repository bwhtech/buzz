import { createResource } from "frappe-ui"

import type { UserInfo } from "@/types"

export const userResource = createResource<UserInfo>({
	url: "buzz.api.account.get_user_info",
	cache: "User",
})
