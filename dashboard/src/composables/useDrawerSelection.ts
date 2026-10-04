import { ref, shallowRef } from "vue"

/** The drawer state every list keeps: which row, and whether it is showing. */
export function useDrawerSelection<T>() {
	// Held past the close so the drawer keeps its contents while it animates out.
	const selected = shallowRef<T | null>(null)
	const open = ref(false)

	function show(item: T) {
		selected.value = item
		open.value = true
	}

	return { selected, open, show }
}
