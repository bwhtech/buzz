import type { AttendeeAddOnSelection, AvailableAddOn, BookingAttendee } from "@/types"

// An add-on that lists no ticket types is offered with every ticket type.
export function appliesToTicketType(addOn: AvailableAddOn, ticketType: unknown) {
	return !addOn.ticket_types?.length || addOn.ticket_types.includes(String(ticketType))
}

export function addOnsForAttendee(addOns: AvailableAddOn[], attendee: BookingAttendee) {
	return addOns.filter((addOn) => appliesToTicketType(addOn, attendee.ticket_type))
}

/** The attendee's ticked add-ons that are still offered with their ticket type. */
export function selectedAddOns(
	attendee: BookingAttendee,
	addOnsMap: Record<string, AvailableAddOn>,
): [AvailableAddOn, AttendeeAddOnSelection][] {
	return Object.entries(attendee.add_ons ?? {}).flatMap(([name, selection]) => {
		const addOn = addOnsMap[name]
		const offered = addOn && appliesToTicketType(addOn, attendee.ticket_type)
		return selection.selected && offered ? [[addOn, selection]] : []
	})
}
