import { ref } from "vue"

import type { MyEvent } from "@/types"

/** The drawer state every event list keeps: which event, and whether it is showing. */
export function useEventDrawer() {
	// Held past the close so the drawer keeps its contents while it animates out.
	const selected = ref<MyEvent | null>(null)
	const open = ref(false)

	function show(event: MyEvent) {
		selected.value = event
		open.value = true
	}

	return { selected, open, show }
}
