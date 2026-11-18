import { test as setup } from "@playwright/test"

import { ONBOARDING_PASSWORD, ONBOARDING_USERS } from "../data/onboarding"
import { createUserWithRoles, saveLoginState } from "../helpers/auth"
import { updateDoc } from "../helpers/frappe"

setup("seed the onboarding users", async ({ request, baseURL }) => {
	await updateDoc(request, "Buzz Settings", "Buzz Settings", {
		enable_onboarding: 1,
		enable_personal_teams: 1,
		enable_communities: 1,
	})

	for (const user of Object.values(ONBOARDING_USERS)) {
		await createUserWithRoles(request, {
			email: user.email,
			firstName: user.firstName,
			password: ONBOARDING_PASSWORD,
			roles: ["Buzz User"],
			userType: "Website User",
			onboarding: "Pending",
		})
		await updateDoc(request, "User", user.email, { username: user.username })
		await saveLoginState(baseURL!, {
			email: user.email,
			password: ONBOARDING_PASSWORD,
			statePath: user.statePath,
		})
	}
})
