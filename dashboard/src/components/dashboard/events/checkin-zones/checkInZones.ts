import { useList } from "frappe-ui"

export type CheckInZone = {
	name: string
	event?: string
	title: string
	is_default: 0 | 1
	enabled: 0 | 1
	repeat_rule: "Once per day" | "Once per event"
	ticket_types: { ticket_type: string }[]
}

export type RepeatRule = CheckInZone["repeat_rule"]

export const REPEAT_RULES: RepeatRule[] = ["Once per day", "Once per event"]

export function useCheckInZones(event: string) {
	return useList<CheckInZone>({
		doctype: "Event Check-in Zone",
		filters: { event },
		fields: [
			"name",
			"title",
			"is_default",
			"enabled",
			"repeat_rule",
			{ ticket_types: ["ticket_type"] },
		],
		orderBy: "is_default desc, creation asc",
		limit: 100,
	})
}

export type CheckInZoneList = ReturnType<typeof useCheckInZones>

export function useEventTicketTypes(event: string) {
	return useList<{ name: string; title: string }>({
		doctype: "Event Ticket Type",
		filters: { event },
		fields: ["name", "title"],
		orderBy: "creation asc",
		limit: 100,
	})
}
