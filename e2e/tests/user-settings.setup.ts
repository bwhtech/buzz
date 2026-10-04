import { test as setup } from "@playwright/test"

import {
	SETTINGS_EMAIL,
	SETTINGS_FIRST_NAME,
	SETTINGS_PASSWORD,
	SETTINGS_STATE_PATH,
} from "../data/user-settings"
import { createUserWithRoles, saveLoginState } from "../helpers/auth"
import { createDoc, ensureTestTeam, getList, updateDoc } from "../helpers/frappe"

setup("seed the settings user", async ({ request, baseURL }) => {
	const team = await ensureTestTeam(request)

	await createUserWithRoles(request, {
		email: SETTINGS_EMAIL,
		firstName: SETTINGS_FIRST_NAME,
		password: SETTINGS_PASSWORD,
		roles: ["Buzz User"],
	})

	// createUserWithRoles resets the name; the bio is this spec's other subject.
	await updateDoc(request, "User", SETTINGS_EMAIL, { last_name: "", bio: "" })

	// The manager shell is gated on team membership, which is what get_my_teams reads.
	const [membership] = await getList(request, "Buzz Team Membership", {
		filters: { team: ["=", team], user: ["=", SETTINGS_EMAIL] },
		limit: 1,
	})
	if (!membership) {
		await createDoc(request, "Buzz Team Membership", {
			team,
			user: SETTINGS_EMAIL,
			team_role: "Manager",
			enabled: 1,
		})
	}

	await saveLoginState(baseURL!, {
		email: SETTINGS_EMAIL,
		password: SETTINGS_PASSWORD,
		statePath: SETTINGS_STATE_PATH,
	})

	console.log(`Settings user ready: ${SETTINGS_EMAIL} on team ${team}`)
})
