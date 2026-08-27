import { test as setup } from "@playwright/test"

import { getDoc, updateDoc } from "../helpers/frappe"

/**
 * The specs need a second language to switch to. German ships with every Frappe
 * site, so enabling it beats depending on whatever the site has turned on.
 */
setup("enable a second language", async ({ request }) => {
	const language = await getDoc<{ enabled: number }>(request, "Language", "de")

	if (!language.enabled) {
		await updateDoc(request, "Language", "de", { enabled: 1 })
		console.log("🌍 Enabled the German language for the language specs")
	}
})
