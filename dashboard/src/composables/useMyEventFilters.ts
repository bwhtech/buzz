import { refDebounced } from "@vueuse/core"
import { useRouteQuery } from "@vueuse/router"
import { computed } from "vue"

import type { FilterField } from "@/components/common/filters"
import { useListQuery } from "@/composables/useListQuery"
import { teams } from "@/data/teams"

// The keys buzz.api.events.MyEventFilters reads; a hand-edited link cannot send others.
const FILTER_KEYS = ["role", "medium", "team"]

const choiceField = (
	key: string,
	label: string,
	options: [value: string, label: string][],
	searchable = false,
): FilterField => ({
	key,
	label,
	fieldtype: "Select",
	section: "standard",
	searchable,
	// One operator: the feed's filters only ever narrow to the picked values.
	operators: [{ operator: "in", label: "is" }],
	options: options.map(([value, optionLabel]) => ({ value, label: optionLabel })),
})

/** The personal events feed's search, filters and archived toggle, kept in the URL. */
export function useMyEventFilters() {
	const { search, conditions, isFiltered } = useListQuery()
	const archivedParam = useRouteQuery<string | null>("archived", null)
	const includeArchived = computed<boolean>({
		get: () => archivedParam.value === "1",
		set: (include) => (archivedParam.value = include ? "1" : null),
	})
	// Typing rewrites the URL, and every rewrite is a request — wait for the pause.
	const debouncedSearch = refDebounced(search, 300)

	const fields = computed(() => [
		choiceField("role", "Role", [
			["hosting", "Hosting"],
			["attending", "Attending"],
		]),
		choiceField("medium", "Medium", [
			["In Person", "In Person"],
			["Online", "Online"],
		]),
		...(teams.value.length > 1
			? [
					choiceField(
						"team",
						"Team",
						teams.value.map((team) => [team.name, team.team_name]),
						true,
					),
				]
			: []),
	])

	const filters = () => ({
		...Object.fromEntries(
			conditions.value
				.filter(([key]) => FILTER_KEYS.includes(key))
				.map(([key, , value]) => [key, value]),
		),
		search: debouncedSearch.value.trim(),
		include_archived: includeArchived.value,
	})

	return { search, conditions, isFiltered, includeArchived, fields, filters }
}
