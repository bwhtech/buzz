import { useColorScheme } from "frappe-ui"
import { computed } from "vue"

import { openUserSettings } from "@/composables/useUserSettings"
import { session } from "@/data/session"
import { teamLabel, teams } from "@/data/teams"
import { managerNavigation } from "@/utils/managerNavigation"

import type { PaletteRow } from "./paletteRows"

const ROOT_NAVIGATION = managerNavigation({ creatingEvent: false, hasSponsorships: false })

/** Rows that need no server: navigation, settings, theme and session. */
export function usePaletteCommands() {
	const { colorScheme, setColorScheme } = useColorScheme()
	const isDark = computed(() => colorScheme.value === "dark")

	const themeRow = computed<PaletteRow>(() => ({
		id: "command:theme",
		label: isDark.value ? __("Switch to Light Theme") : __("Switch to Dark Theme"),
		icon: isDark.value ? "lucide-sun" : "lucide-moon",
		keywords: ["theme", "dark", "light", "appearance"],
		run: () => setColorScheme(isDark.value ? "light" : "dark"),
	}))

	const commands = computed<PaletteRow[]>(() => [
		{
			id: "command:create-event",
			label: __("Create Event"),
			icon: "lucide-plus",
			to: "/manage/team/events/new",
			keywords: ["new event"],
		},
		...ROOT_NAVIGATION.map((item) => ({
			id: `command:${item.to}`,
			label: __("Go to {0}", [__(item.label)]),
			icon: item.icon,
			to: item.to,
		})),
		themeRow.value,
		{
			id: "command:settings",
			label: __("Settings"),
			icon: "lucide-settings",
			keywords: ["profile", "preferences"],
			run: openUserSettings,
		},
		{
			id: "command:check-in",
			label: __("Check-in"),
			icon: "lucide-scan-line",
			to: "/check-in",
			keywords: ["scan"],
		},
		{
			id: "command:logout",
			label: __("Log Out"),
			icon: "lucide-log-out",
			keywords: ["sign out"],
			run: () => session.logout.fetch(),
		},
	])

	// Every destination of every community, for switching between them.
	const communityRows = computed<PaletteRow[]>(() =>
		teams.value.flatMap((team) => {
			const title = teamLabel(team)
			return managerNavigation({
				teamId: team.name,
				creatingEvent: false,
				hasSponsorships: false,
			}).map((item) => ({
				id: `community:${item.to}`,
				label: `${title} › ${__(item.label)}`,
				icon: item.icon,
				to: item.to,
				keywords: ["community", "switch"],
			}))
		}),
	)

	return { commands, communityRows }
}
