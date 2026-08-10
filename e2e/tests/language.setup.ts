import { test as setup } from "@playwright/test";
import { getDoc, updateDoc } from "../helpers/frappe";

/**
 * The language specs need a second enabled language to switch to. German ships
 * with every Frappe site; enabling it here keeps the specs from depending on
 * whatever the site happens to have turned on.
 */
setup("enable a second language", async ({ request }) => {
	const language = await getDoc<{ enabled: number }>(request, "Language", "de");

	if (!language.enabled) {
		await updateDoc(request, "Language", "de", { enabled: 1 });
		console.log("🌍 Enabled the German language for the language specs");
	}
});
