import assert from "node:assert/strict"
import { test } from "node:test"

import { paymentGatewayLogo } from "./paymentGateways.ts"

test("matches a gateway by its exact name", () => {
	assert.equal(
		paymentGatewayLogo("Razorpay")?.light,
		"/assets/buzz/images/payment_gateways/razorpay.svg",
	)
})

test("matches an account-suffixed gateway by its provider", () => {
	assert.equal(
		paymentGatewayLogo("Razorpay-Main")?.dark,
		"/assets/buzz/images/payment_gateways/razorpay-dark.svg",
	)
})

test("returns nothing for an unknown gateway or offline method", () => {
	assert.equal(paymentGatewayLogo("Bank Transfer"), undefined)
})
