import type { RegistrationStep, RegistrationStepId } from "./useRegistrationSteps"

interface StepState {
	ticketCount: number
	completeAttendees: number
	showDetails: boolean
	showPayment: boolean
	paid: boolean
	isGuest: boolean
	totalLabel: string
}

export function buildSteps(state: StepState): RegistrationStep[] {
	const count = state.ticketCount
	const steps: RegistrationStep[] = [
		{
			id: "tickets",
			label: __("Tickets"),
			sub: count
				? count === 1
					? __("1 ticket selected")
					: __("{0} tickets selected", [count])
				: __("Pick your tickets"),
		},
		{
			id: "attendees",
			label: __("Attendees"),
			sub: __("{0} of {1} complete", [state.completeAttendees, count]),
		},
	]
	if (state.showDetails) {
		steps.push({
			id: "details",
			label: state.paid ? __("Billing") : __("Your details"),
			sub: state.isGuest ? __("Contact details") : __("Invoice and booking details"),
		})
	}
	if (state.showPayment) steps.push({ id: "payment", label: __("Payment"), sub: state.totalLabel })
	return steps
}

export function stepCopy(
	id: RegistrationStepId,
	event: { free: boolean; paid: boolean; isGuest: boolean },
) {
	const copy: Record<RegistrationStepId, { title: string; description: string }> = {
		tickets: {
			title: __("Choose tickets"),
			description: event.free
				? __("This event is free. Pick the tickets you'll use.")
				: __("Pick as many tickets as you need. Each one is issued to one person."),
		},
		attendees: {
			title: __("Attendee details"),
			description: __("Each ticket is issued to one person and emailed to the address you enter."),
		},
		details: {
			title: event.paid ? __("Billing") : __("Your details"),
			description: event.isGuest
				? __("Who's registering, and where to send the confirmation.")
				: __("Booking details and whether you need a tax invoice."),
		},
		payment: { title: __("Payment"), description: __("Choose how you'd like to pay.") },
	}
	return copy[id]
}
