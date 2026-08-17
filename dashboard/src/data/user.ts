import type { UserInfo } from "@/types"
import { createResource } from "frappe-ui"

export const userResource = createResource<UserInfo>({
	url: "buzz.api.account.get_user_info",
	cache: "User",
})
