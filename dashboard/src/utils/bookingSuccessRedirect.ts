// Where the user lands after a booking is submitted. The server decides between
// a gateway hand-off and an explicit redirect; when it asks for neither, guests
// stay on the form and logged-in users go to their bookings.

export interface BookingSubmitResponse {
	booking_name: string
	payment_link?: string
	redirect_to?: string
	offline_payment?: boolean
}

export type BookingSuccessAction =
	| { type: "external"; url: string }
	| { type: "route"; path: string }
	| { type: "guest-inline"; bookingName: string }

export function resolveBookingSuccessAction(
	data: BookingSubmitResponse,
	{ isGuestMode }: { isGuestMode: boolean },
): BookingSuccessAction {
	if (data.payment_link) {
		return { type: "external", url: data.payment_link }
	}

	if (data.redirect_to) {
		return { type: "route", path: data.redirect_to }
	}

	if (isGuestMode) {
		return { type: "guest-inline", bookingName: data.booking_name }
	}

	if (data.offline_payment) {
		return {
			type: "route",
			path: `/bookings/${data.booking_name}?success=true&offline=true`,
		}
	}

	return { type: "route", path: `/bookings/${data.booking_name}?success=true` }
}
