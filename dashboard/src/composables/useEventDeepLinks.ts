import { useList } from "frappe-ui"
import { ref, watch } from "vue"
import { useRoute } from "vue-router"

import { useOpenFromQuery } from "@/composables/useOpenFromQuery"
import type { MyEvent } from "@/types"
import type { TimelineTab } from "@/utils/timelineTabs"

export interface FeedEntry {
	event: MyEvent
	tab: TimelineTab
}

type Feed = Record<TimelineTab, MyEvent[]>

const TABS: TimelineTab[] = ["upcoming", "past"]

/**
 * Opens the drawer `?event=`, `?ticket=` or `?booking=` points at. A ticket or booking is
 * first resolved to its event through the list API, so its read permission still applies.
 */
export function useEventDeepLinks(
	feed: () => Feed | null | undefined,
	open: (entry: FeedEntry) => void,
) {
	const find = (name?: string | number | null): FeedEntry | undefined => {
		if (!name) return undefined
		for (const tab of TABS) {
			const event = feed()?.[tab].find((row) => row.name === String(name))
			if (event) return { event, tab }
		}
	}

	useOpenFromQuery("event", find, open)
	useOpenFromLinkedRecord("ticket", "Event Ticket", find, open)
	useOpenFromLinkedRecord("booking", "Event Booking", find, open)
}

function useOpenFromLinkedRecord(
	param: string,
	doctype: string,
	find: (event?: string) => FeedEntry | undefined,
	open: (entry: FeedEntry) => void,
) {
	const route = useRoute()
	const linked = () => (route.query[param] as string | undefined) || null
	// Held past the param being cleared, so dropping it does not refetch an empty filter.
	const recordName = ref(linked())
	watch(linked, (name) => name && (recordName.value = name))

	const records = useList<{ name: string; event: string }>({
		doctype,
		fields: ["name", "event"],
		filters: () => ({ name: recordName.value || "" }),
		limit: 1,
		immediate: Boolean(recordName.value),
		refetch: true,
	})

	useOpenFromQuery(
		param,
		(name) => find(records.data?.find((row) => row.name === name)?.event),
		open,
	)
}
