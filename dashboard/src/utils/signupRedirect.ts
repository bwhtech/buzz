const BOOKING_PATH = "/b/register/"

// Where a new account lands after verifying its email. Booking stays uninterrupted, so
// onboarding waits for the next dashboard visit; everywhere else onboarding comes first
// and then returns the user to the page they signed up on.
export function signupRedirect({
	pathname,
	search,
}: {
	pathname: string
	search: string
}): Record<string, string> {
	const here = pathname + search
	if (pathname.startsWith(BOOKING_PATH)) return { redirect_to: here, skip_onboarding: "1" }
	return { redirect_to: `/b/onboarding?redirect-to=${encodeURIComponent(here)}` }
}
