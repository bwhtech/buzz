// Mounts an island the first time its trigger is clicked, so a page pays nothing until then.
const triggers = document.querySelectorAll<HTMLElement>("[data-island]")

for (const trigger of triggers) {
	trigger.addEventListener("click", () => {
		import("./mount").then(({ openIsland }) => openIsland(trigger))
	})
}
