import frappeUIPreset, { content as frappeUIContent } from "frappe-ui/tailwind"

export default {
	presets: [frappeUIPreset],
	// Tailwind 4 does this by default; on 3 a `hover:` style sticks after a tap, so every
	// hover state on the dashboard stays lit until something else is touched.
	future: { hoverOnlyWhenSupported: true },
	content: [
		"./index.html",
		"./src/**/*.{vue,js,ts,jsx,tsx}",
		...frappeUIContent,
		// frappe-ui/experimental is deliberately absent from the `content` export, so
		// nothing under it is scanned: ListView renders unstyled, and Accordion loses
		// its chevron rotation, which lives in a group-data variant.
		"./node_modules/frappe-ui/experimental/**/*.{vue,js,ts,jsx,tsx}",
	],
	theme: {
		extend: {},
	},
	plugins: [],
}
