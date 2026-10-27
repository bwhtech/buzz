import assert from "node:assert/strict"
import { test } from "node:test"

import { resolveBookingSuccessAction } from "./bookingSuccessRedirect.ts"

test("payment_link takes priority and is external", () => {
	const action = resolveBookingSuccessAction(
		{ payment_link: "https://gateway.example/pay/123" },
		{ isGuestMode: true },
	)
	assert.deepEqual(action, { type: "external", url: "https://gateway.example/pay/123" })
})

test("redirect_to routes to booking-success for a guest", () => {
	const action = resolveBookingSuccessAction(
		{ booking_name: "B-0001", redirect_to: "/booking-success/B-0001?token=abc" },
		{ isGuestMode: true },
	)
	assert.deepEqual(action, { type: "route", path: "/booking-success/B-0001?token=abc" })
})

test("redirect_to routes to booking-success for a logged-in user", () => {
	const action = resolveBookingSuccessAction(
		{ booking_name: "B-0002", redirect_to: "/booking-success/B-0002?token=def" },
		{ isGuestMode: false },
	)
	assert.deepEqual(action, { type: "route", path: "/booking-success/B-0002?token=def" })
})

test("guest with no redirect_to and no payment_link falls back to inline confirmation", () => {
	const action = resolveBookingSuccessAction({ booking_name: "B-0003" }, { isGuestMode: true })
	assert.deepEqual(action, {
		type: "guest-inline",
		bookingName: "B-0003",
		pendingVerification: false,
		approvalPending: false,
	})
})

test("guest offline booking stays inline but is pending verification", () => {
	const action = resolveBookingSuccessAction(
		{ booking_name: "B-0006", offline_payment: true },
		{ isGuestMode: true },
	)
	assert.deepEqual(action, {
		type: "guest-inline",
		bookingName: "B-0006",
		pendingVerification: true,
		approvalPending: false,
	})
})

test("logged-in offline booking routes to bookings page with offline flag", () => {
	const action = resolveBookingSuccessAction(
		{ booking_name: "B-0004", offline_payment: true },
		{ isGuestMode: false },
	)
	assert.deepEqual(action, {
		type: "route",
		path: "/bookings/B-0004?success=true&offline=true",
	})
})

test("logged-in booking with none of the above falls back to bookings page", () => {
	const action = resolveBookingSuccessAction({ booking_name: "B-0005" }, { isGuestMode: false })
	assert.deepEqual(action, { type: "route", path: "/bookings/B-0005?success=true" })
})

test("a response with no booking name and no payment link throws", () => {
	assert.throws(() => resolveBookingSuccessAction({}, { isGuestMode: false }), /booking name/)
	assert.throws(() => resolveBookingSuccessAction({}, { isGuestMode: true }), /booking name/)
})

test("guest approval request stays inline and is pending approval", () => {
	const action = resolveBookingSuccessAction(
		{ booking_name: "B-0007", approval_pending: true },
		{ isGuestMode: true },
	)
	assert.deepEqual(action, {
		type: "guest-inline",
		bookingName: "B-0007",
		pendingVerification: false,
		approvalPending: true,
	})
})

test("logged-in approval request routes to the booking with the approval flag", () => {
	const action = resolveBookingSuccessAction(
		{ booking_name: "B-0008", approval_pending: true },
		{ isGuestMode: false },
	)
	assert.deepEqual(action, { type: "route", path: "/bookings/B-0008?success=true&approval=true" })
})
