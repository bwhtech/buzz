import { CREATED_KEY } from "./create-community/reveal"

// Mounts an island the first time its trigger is clicked; its code is fetched once the page is idle.
const triggers = document.querySelectorAll<HTMLElement>("[data-island]")

for (const trigger of triggers) {
	trigger.addEventListener("click", (event) => {
		// A link trigger keeps its href for new-tab clicks and for when this script fails.
		if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
		event.preventDefault()
		import("./mount").then(({ openIsland }) => openIsland(trigger))
	})
}

// Islands that open with the page rather than on a click, such as the playground bar.
for (const trigger of document.querySelectorAll<HTMLElement>("[data-island-auto]")) {
	import("./mount").then(({ openIsland }) => openIsland(trigger))
}

type Connection = { saveData?: boolean; effectiveType?: string }
const connection = (navigator as Navigator & { connection?: Connection }).connection

// Fetches the code of the page's islands once it is idle, so a first click opens one without a
// download. Skipped where data is scarce; those visitors fetch on click.
function prefetchIslands() {
	if (connection?.saveData || connection?.effectiveType?.endsWith("2g")) return
	const names = new Set([...triggers].map((trigger) => trigger.dataset.island || ""))
	import("./mount").then(({ prefetchIsland }) => names.forEach(prefetchIsland))
}

if (triggers.length) {
	window.addEventListener("load", () => (window.requestIdleCallback || setTimeout)(prefetchIslands))
}

// A community just created on /community; see create-community/reveal.ts.
const created = sessionStorage.getItem(CREATED_KEY)
if (created) {
	sessionStorage.removeItem(CREATED_KEY)
	import("./create-community/announce").then(({ announceCreatedCommunity }) =>
		announceCreatedCommunity(JSON.parse(created)),
	)
}
