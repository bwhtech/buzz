import { toast } from "frappe-ui"
import { nextTick, ref, watch } from "vue"

import type { EventPagesList } from "@/data/events"
import type { AdditionalEventPage } from "@/types"
import { serverErrorMessage } from "@/utils/serverError"

export function useEventPageOrder(pages: EventPagesList) {
	// Held locally so a move lands at once; the server order replaces it once every write is in.
	const order = ref<AdditionalEventPage[]>([])
	const reordering = ref(false)
	watch(
		() => pages.data,
		(data) => !reordering.value && (order.value = [...(data ?? [])]),
		{ immediate: true },
	)

	// Keyboard moves repeat fast, so they skip the slide.
	const animateMoves = ref(true)

	async function move(fromIndex: number, toIndex: number) {
		if (toIndex < 0 || toIndex >= order.value.length || fromIndex === toIndex) return
		const reordered = [...order.value]
		reordered.splice(toIndex, 0, ...reordered.splice(fromIndex, 1))
		order.value = reordered
		await save(reordered)
	}

	async function save(reordered: AdditionalEventPage[]) {
		reordering.value = true
		await Promise.all(
			reordered.map((page, index) =>
				page.display_order === index + 1
					? null
					: pages.setValue.submit({ name: page.name, display_order: index + 1 }).catch(() => null),
			),
		)
		reordering.value = false
		if (pages.setValue.error) toast.error(serverErrorMessage(pages.setValue.error))
		await pages.reload()
	}

	const draggedIndex = ref<number | null>(null)
	const overIndex = ref<number | null>(null)

	function dropAt(index: number) {
		if (draggedIndex.value !== null) move(draggedIndex.value, index)
		endDrag()
	}

	function endDrag() {
		draggedIndex.value = null
		overIndex.value = null
	}

	async function moveWithArrowKeys(event: KeyboardEvent, index: number) {
		const offset = { ArrowUp: -1, ArrowDown: 1 }[event.key]
		if (!offset) return
		event.preventDefault()
		const handle = event.currentTarget as HTMLElement
		animateMoves.value = false
		move(index, index + offset)
		await nextTick()
		handle.focus()
		animateMoves.value = true
	}

	return { order, animateMoves, move, draggedIndex, overIndex, dropAt, endDrag, moveWithArrowKeys }
}
