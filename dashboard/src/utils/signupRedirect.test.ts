import assert from "node:assert/strict"
import { test } from "node:test"

import { signupRedirect } from "./signupRedirect.ts"

test("defers onboarding during booking", () => {
	assert.deepEqual(signupRedirect({ pathname: "/b/register/devconf", search: "?tier=1" }), {
		redirect_to: "/b/register/devconf?tier=1",
		skip_onboarding: "1",
	})
})

test("sends other signups through onboarding and back", () => {
	assert.deepEqual(signupRedirect({ pathname: "/events/devconf", search: "" }), {
		redirect_to: "/b/onboarding?redirect-to=%2Fevents%2Fdevconf",
	})
})
