// Shared between onboarding.setup.ts and onboarding.spec.ts. Each flow finishes onboarding
// for its user, so every flow gets a fresh one.
export const ONBOARDING_PASSWORD = "Onboarding@123"

const onboardingUser = (key: string) => ({
	email: `onboarding-${key}-e2e@buzz.test`,
	firstName: `Onboard${key.charAt(0).toUpperCase()}${key.slice(1)}`,
	username: `onboarding-${key}-e2e`,
	statePath: `e2e/.auth/onboarding-${key}.json`,
})

export const ONBOARDING_USERS = {
	personal: onboardingUser("personal"),
	community: onboardingUser("community"),
	attendee: onboardingUser("attendee"),
}
