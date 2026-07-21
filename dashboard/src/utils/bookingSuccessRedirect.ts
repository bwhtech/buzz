// Where the user lands after a booking is submitted. The server decides between
// a gateway hand-off and an explicit redirect; when it asks for neither, guests
// stay on the form and logged-in users go to their bookings.

// A paid booking comes back with only a payment link — the booking name is
// carried by every other response.
export interface BookingSubmitResponse {
	booking_name?: string
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

	// Past the two branches above, every response the server sends names the
	// booking. Refuse rather than build a URL pointing at "undefined".
	const bookingName = data.booking_name
	if (!bookingName) {
		throw new Error("Booking response carried neither a payment link nor a booking name")
	}

	if (isGuestMode) {
		return { type: "guest-inline", bookingName }
	}

	if (data.offline_payment) {
		return {
			type: "route",
			path: `/bookings/${bookingName}?success=true&offline=true`,
		}
	}

	return { type: "route", path: `/bookings/${bookingName}?success=true` }
}
