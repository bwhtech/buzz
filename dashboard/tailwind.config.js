import frappeUIPreset, { content as frappeUIContent } from "frappe-ui/tailwind"

export default {
	presets: [frappeUIPreset],
	content: [
		"./index.html",
		"./src/**/*.{vue,js,ts,jsx,tsx}",
		...frappeUIContent,
		// ListView lives in frappe-ui/experimental, which the `content` export
		// deliberately skips. Without this its classes are never scanned and every
		// list renders unstyled.
		"./node_modules/frappe-ui/experimental/ListView/**/*.{vue,js,ts,jsx,tsx}",
	],
	theme: {
		extend: {},
	},
	plugins: [],
}
