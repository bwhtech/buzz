import { test } from "node:test";
import assert from "node:assert/strict";
import { resolveBookingSuccessAction } from "./bookingSuccessRedirect.ts";

test("payment_link takes priority and is external", () => {
	const action = resolveBookingSuccessAction(
		{ payment_link: "https://gateway.example/pay/123" },
		{ isGuestMode: true }
	);
	assert.deepEqual(action, { type: "external", url: "https://gateway.example/pay/123" });
});

test("redirect_to routes to booking-success for a guest", () => {
	const action = resolveBookingSuccessAction(
		{ booking_name: "B-0001", redirect_to: "/booking-success/B-0001?token=abc" },
		{ isGuestMode: true }
	);
	assert.deepEqual(action, { type: "route", path: "/booking-success/B-0001?token=abc" });
});

test("redirect_to routes to booking-success for a logged-in user", () => {
	const action = resolveBookingSuccessAction(
		{ booking_name: "B-0002", redirect_to: "/booking-success/B-0002?token=def" },
		{ isGuestMode: false }
	);
	assert.deepEqual(action, { type: "route", path: "/booking-success/B-0002?token=def" });
});

test("guest with no redirect_to and no payment_link falls back to inline confirmation", () => {
	const action = resolveBookingSuccessAction({ booking_name: "B-0003" }, { isGuestMode: true });
	assert.deepEqual(action, { type: "guest-inline", bookingName: "B-0003" });
});

test("logged-in offline booking routes to bookings page with offline flag", () => {
	const action = resolveBookingSuccessAction(
		{ booking_name: "B-0004", offline_payment: true },
		{ isGuestMode: false }
	);
	assert.deepEqual(action, {
		type: "route",
		path: "/bookings/B-0004?success=true&offline=true",
	});
});

test("logged-in booking with none of the above falls back to bookings page", () => {
	const action = resolveBookingSuccessAction({ booking_name: "B-0005" }, { isGuestMode: false });
	assert.deepEqual(action, { type: "route", path: "/bookings/B-0005?success=true" });
});

test("a response with no booking name and no payment link throws", () => {
	assert.throws(() => resolveBookingSuccessAction({}, { isGuestMode: false }), /booking name/);
	assert.throws(() => resolveBookingSuccessAction({}, { isGuestMode: true }), /booking name/);
});
