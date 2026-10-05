import { useMutationObserver } from "@vueuse/core"

// The status bar and browser chrome follow `theme-color`. Its media queries only know the
// OS scheme, so a theme picked in the app would leave the bar in the other one.
export function useThemeColor() {
	const root = document.documentElement

	function syncThemeColor() {
		const color = getComputedStyle(root).getPropertyValue("--surface-base").trim()
		if (!color) return
		for (const meta of document.querySelectorAll<HTMLMetaElement>('meta[name="theme-color"]')) {
			meta.content = color
		}
	}

	syncThemeColor()
	useMutationObserver(root, syncThemeColor, { attributeFilter: ["data-theme"] })
}
