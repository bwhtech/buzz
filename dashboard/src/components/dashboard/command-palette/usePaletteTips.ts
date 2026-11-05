import { useLocalStorage } from "@vueuse/core"
import { computed, type Ref } from "vue"

import { userResource } from "@/data/user"

import { readableSources, type PaletteEvent } from "./paletteQuery"
import type { PaletteRow, PaletteScope } from "./paletteRows"

const SEARCHES_KEY = "buzz:palette-searches"
const SEARCHES_BEFORE_HIDING = 5

type TipsState = {
	query: Ref<string>
	scope: Ref<PaletteScope | null>
	event: Ref<PaletteEvent | undefined>
}

/** Example rows on an empty palette, until the user has opened a few search results. */
export function usePaletteTips({ query, scope, event }: TipsState) {
	// Per browser, not per user: a hint that returns on a new device costs nothing.
	const searches = useLocalStorage(SEARCHES_KEY, 0)

	const tips = computed<PaletteRow[]>(() => {
		if (searches.value >= SEARCHES_BEFORE_HIDING) return []
		if (query.value || scope.value || !event.value) return []
		// Nothing searchable here, so every example would lead nowhere.
		if (!readableSources(event.value).length) return []
		return tipRows(event.value, query, scope)
	})

	// A search counts once its result is opened: a record, or the filtered list.
	function countSearch(row: PaletteRow) {
		if (!row.id.startsWith("record:") && !row.id.startsWith("search:")) return
		searches.value += 1
	}

	return { tips, countSearch }
}

function tipRows(event: PaletteEvent, query: Ref<string>, scope: Ref<PaletteScope | null>) {
	const source = readableSources(event)[0]
	const name = userResource.data?.first_name?.toLowerCase() || "name"
	const example = `${name} in ${event.title}`
	const rows: PaletteRow[] = [
		{
			id: "tip:in",
			label: example,
			subtitle: __("Find a person, talk or sponsor in one event"),
			icon: "lucide-search",
			keepOpen: true,
			run: () => (query.value = example),
		},
		{
			id: "tip:event",
			label: __("Search inside {0}", [event.title]),
			subtitle: __("Same as Tab on any event or section"),
			icon: "lucide-corner-down-right",
			keepOpen: true,
			run: () => (scope.value = { event }),
		},
	]
	if (source)
		rows.splice(1, 0, {
			id: "tip:section",
			label: `${source.label} in ${event.title}`,
			subtitle: __("Search one section"),
			icon: "lucide-list-filter",
			keepOpen: true,
			run: () => (scope.value = { event, source }),
		})
	return rows
}
