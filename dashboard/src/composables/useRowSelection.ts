import { computed, ref, type Ref } from "vue"

/** Multi-select for a keyed list, held against the keys that are selectable right now. */
export function useRowSelection(selectableKeys: Ref<string[]>) {
	const chosen = ref(new Set<string>())

	// Intersected rather than read straight off the set, so a row a reload took away
	// cannot stay selected out of sight.
	const selected = computed(() => selectableKeys.value.filter((key) => chosen.value.has(key)))

	function isSelected(key: string) {
		return chosen.value.has(key)
	}

	function toggle(key: string) {
		const next = new Set(chosen.value)
		if (!next.delete(key)) next.add(key)
		chosen.value = next
	}

	function clear() {
		chosen.value = new Set()
	}

	return { selected, isSelected, toggle, clear }
}
