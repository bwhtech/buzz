export function resolveBookingSuccessAction(data, { isGuestMode }) {
	if (data.payment_link) {
		return { type: "external", url: data.payment_link };
	}

	if (data.redirect_to) {
		return { type: "route", path: data.redirect_to };
	}

	if (isGuestMode) {
		return { type: "guest-inline", bookingName: data.booking_name };
	}

	if (data.offline_payment) {
		return { type: "route", path: `/bookings/${data.booking_name}?success=true&offline=true` };
	}

	return { type: "route", path: `/bookings/${data.booking_name}?success=true` };
}
