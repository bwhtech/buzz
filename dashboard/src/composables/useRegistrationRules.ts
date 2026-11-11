import { call, toast } from "frappe-ui"
import { computed, ref } from "vue"

import { useEventDoc } from "@/data/events"
import type { useEventTicketTypes } from "@/data/ticketTypes"
import { type ApprovalMode, approvalModeOf, approvalModeWrites } from "@/utils/approvalMode"
import { serverErrorMessage } from "@/utils/serverError"

type TicketTypesPage = ReturnType<typeof useEventTicketTypes>

/** Who gets in without review, and how the waitlist behaves, for one event. */
export function useRegistrationRules(event: string, page: TicketTypesPage) {
	const eventDoc = useEventDoc(() => event)
	const ticketTypes = computed(() => page.data?.ticket_types ?? [])

	// "Review some tickets" stores nothing until a ticket type is flagged, so the pick is
	// kept here or the cards would snap back to auto-confirm.
	const picked = ref<ApprovalMode | null>(null)
	const mode = computed<ApprovalMode>(() => {
		const stored = approvalModeOf(Boolean(page.data?.requires_approval), ticketTypes.value)
		return stored === "auto" && picked.value === "some" ? "some" : stored
	})

	const offerHours = computed(() => eventDoc.doc?.payment_offer_hours || "48")

	async function save(write: () => Promise<unknown>) {
		try {
			await write()
		} catch (error) {
			toast.error(serverErrorMessage(error) || "Could not save the setting. Try again.")
		}
		page.reload()
	}

	const setEventValue = (values: Record<string, string | number>) =>
		eventDoc.setValue.submit(values)

	const pickMode = (next: ApprovalMode) => {
		picked.value = next
		const writes = approvalModeWrites(next, ticketTypes.value)
		return save(async () => {
			await setEventValue({ requires_approval: writes.requires_approval ? 1 : 0 })
			for (const name of writes.clearTicketTypes)
				await call("frappe.client.set_value", {
					doctype: "Event Ticket Type",
					name,
					fieldname: "requires_approval",
					value: 0,
				})
		})
	}

	const setWaitlist = (enabled: boolean) =>
		save(() => setEventValue({ enable_waitlist: enabled ? 1 : 0 }))

	const setOfferHours = (hours: string) => save(() => setEventValue({ payment_offer_hours: hours }))

	return { mode, offerHours, pickMode, setWaitlist, setOfferHours }
}
