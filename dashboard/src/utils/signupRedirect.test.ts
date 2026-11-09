import { describe, expect, it } from "vitest"

import { signupRedirect } from "./signupRedirect"

describe("signupRedirect", () => {
	it("defers onboarding during booking", () => {
		expect(signupRedirect({ pathname: "/b/register/devconf", search: "?tier=1" })).toEqual({
			redirect_to: "/b/register/devconf?tier=1",
			skip_onboarding: "1",
		})
	})

	it("sends other signups through onboarding and back", () => {
		expect(signupRedirect({ pathname: "/events/devconf", search: "" })).toEqual({
			redirect_to: "/b/onboarding?redirect-to=%2Fevents%2Fdevconf",
		})
	})
})
