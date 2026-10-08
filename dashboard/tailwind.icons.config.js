// Lucide's `lucide-*` classes for the Jinja pages, the same ones the dashboard uses.
import lucideIconsPlugin from "./node_modules/frappe-ui/tailwind/lucideIconsPlugin.js"

export default {
	// Only the icon classes: the pages style everything else with espresso CSS.
	corePlugins: [],
	plugins: [lucideIconsPlugin],
	// Templates only: buzz/public also holds node_modules and the built dashboard.
	content: [
		"../buzz/{templates,www}/**/*.html",
		"../buzz/*/doctype/*/templates/**/*.html",
		"../buzz/public/js/**/*.ts",
	],
}
