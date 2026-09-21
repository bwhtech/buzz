import { useCall, useDoc, useList, useNewDoc } from "frappe-ui"

import type { ThemeDoc, ThemeOptions, ThemeRow } from "@/types"

// v2 path: useCall reads the payload from `data`, which /api/method names `message`.
export function useThemeOptions() {
	return useCall<ThemeOptions>({ url: "/api/v2/method/buzz.api.themes.get_theme_options" })
}

export function useThemes(filters: Record<string, number> = {}) {
	return useList<ThemeRow>({
		doctype: "Buzz Theme",
		fields: ["name", "color_scheme", "enabled", "is_standard"],
		filters,
		orderBy: "creation asc",
		limit: 100,
	})
}

export function useTheme(name: () => string) {
	return useDoc<ThemeDoc>({ doctype: "Buzz Theme", name })
}

export function useNewTheme() {
	return useNewDoc<Omit<ThemeDoc, "name" | "is_standard"> & { name?: string }>("Buzz Theme")
}
