import type { MyEvents } from "@/types"
import { createResource } from "frappe-ui"

export const myEvents = createResource<MyEvents>({
	url: "buzz.api.events.get_my_events",
	cache: "My Events",
	auto: true,
})
