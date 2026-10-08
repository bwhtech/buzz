import frappeUIPreset from "frappe-ui/tailwind"

import lucideIconsPlugin from "./node_modules/frappe-ui/tailwind/lucideIconsPlugin.js"
// Not in frappe-ui's package exports, hence the relative paths.
import themePlugin from "./node_modules/frappe-ui/tailwind/plugin.js"

export default {
	// Without forms and typography, which no island uses.
	presets: [{ ...frappeUIPreset, plugins: [themePlugin, lucideIconsPlugin] }],
	// Utilities apply only inside islands, and preflight stays off, so the page keeps its styles.
	important: ".buzz-island",
	corePlugins: { preflight: false },
	// Event pages switch theme on data-mode, not data-theme.
	darkMode: ["selector", '[data-mode="dark"]'],
	content: [
		"./src/islands/**/*.{vue,ts}",
		// Add each dashboard component an island imports, and the frappe-ui component folders
		// it uses, e.g. "./node_modules/frappe-ui/src/components/{Button,Dialog}/**/*.{vue,ts}".
	],
}
