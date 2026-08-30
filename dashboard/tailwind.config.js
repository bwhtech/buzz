import frappeUIPreset, { content as frappeUIContent } from "frappe-ui/tailwind"

export default {
	presets: [frappeUIPreset],
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
