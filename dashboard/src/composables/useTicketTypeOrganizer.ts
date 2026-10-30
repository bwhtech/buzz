import { call, toast } from "frappe-ui"
import { type Ref, computed, reactive, ref } from "vue"

import { useHeldWrite } from "@/composables/useHeldWrite"
import type { EventTicketTypes, TicketCategoryItem, TicketTypeItem } from "@/types"

export type TicketTypeGroup = {
	key: string
	category: TicketCategoryItem | null
	title: string
	ticketTypes: TicketTypeItem[]
}

export type TicketTypeOrganizer = ReturnType<typeof useTicketTypeOrganizer>

// Moves and deletes show at once and reach the server once their Undo window closes.
// Until the page reloads after a write, local overrides sit on top of the fetched data.
export function useTicketTypeOrganizer(
	data: Ref<EventTicketTypes | null>,
	reload: () => Promise<unknown>,
) {
	const held = useHeldWrite()
	const dragging = ref<string | null>(null)
	const dropTarget = ref<string | null>(null)
	const moved = reactive(new Map<string, string>())
	const deleted = reactive(new Set<string>())
	const order = ref<string[] | null>(null)

	const ticketTypes = computed(() => data.value?.ticket_types ?? [])
	const categories = computed(() => {
		const kept = (data.value?.categories ?? []).filter((category) => !deleted.has(category.name))
		const position = (name: string) => order.value?.indexOf(name) ?? 0
		return order.value ? kept.toSorted((a, b) => position(a.name) - position(b.name)) : kept
	})

	// The empty key stands for Uncategorized: the API sends "" or null for no category.
	function categoryOf(ticketType: TicketTypeItem) {
		const key = moved.get(ticketType.name) ?? ticketType.category ?? ""
		return deleted.has(key) ? "" : key
	}

	const groups = computed<TicketTypeGroup[]>(() => {
		const inGroup = (key: string) => ticketTypes.value.filter((row) => categoryOf(row) === key)
		const categorized = categories.value.map((category) => ({
			key: category.name,
			category,
			title: category.title,
			ticketTypes: inGroup(category.name),
		}))
		const uncategorized = inGroup("")
		if (!uncategorized.length && !dragging.value) return categorized
		return [
			...categorized,
			{ key: "", category: null, title: "Uncategorized", ticketTypes: uncategorized },
		]
	})

	const titleOf = (key: string) =>
		categories.value.find((category) => category.name === key)?.title ?? "Uncategorized"

	// The override stays until the reload brings the written value, so nothing flickers back.
	async function write(request: () => Promise<unknown>, clear: () => void, failure: string) {
		try {
			await request()
			await reload()
		} catch {
			toast.error(failure)
		}
		clear()
	}

	function saveCategory(name: string, key: string) {
		moved.set(name, key)
		const request = () =>
			call("frappe.client.set_value", {
				doctype: "Event Ticket Type",
				name,
				fieldname: "category",
				value: key,
			})
		write(request, () => moved.delete(name), "Could not move the ticket type")
	}

	function move(ticketType: TicketTypeItem, key: string) {
		const previous = categoryOf(ticketType)
		if (previous === key) return
		moved.set(ticketType.name, key)
		held.hold({
			message: `Moved ${ticketType.title} to ${titleOf(key)}`,
			write: () => saveCategory(ticketType.name, key),
			undo: () => moved.delete(ticketType.name),
			revert: () => saveCategory(ticketType.name, previous),
		})
	}

	// No revert: once the delete goes out, the category is gone.
	function remove(category: TicketCategoryItem) {
		deleted.add(category.name)
		const request = () =>
			call("frappe.client.delete", { doctype: "Event Ticket Category", name: category.name })
		held.hold({
			message: `Deleted ${category.title}`,
			write: () =>
				write(request, () => deleted.delete(category.name), "Could not delete the category"),
			undo: () => deleted.delete(category.name),
		})
	}

	// Swaps a category with its neighbour and renumbers sort_order. No Undo: the arrow undoes it.
	// ponytail: one write per category, a bulk endpoint if events grow past a handful.
	function shift(category: TicketCategoryItem, step: -1 | 1) {
		const names = categories.value.map((row) => row.name)
		const from = names.indexOf(category.name)
		const to = from + step
		if (to < 0 || to >= names.length) return
		;[names[from], names[to]] = [names[to], names[from]]
		order.value = names
		const request = () =>
			Promise.all(
				names.map((name, index) =>
					call("frappe.client.set_value", {
						doctype: "Event Ticket Category",
						name,
						fieldname: "sort_order",
						value: index,
					}),
				),
			)
		write(request, () => (order.value = null), "Could not reorder the categories")
	}

	const drag = useDrag(dragging, dropTarget, move)
	return { groups, categoryOf, titleOf, dragging, dropTarget, move, remove, shift, drag }
}

// Native drag and drop: a ticket type card is the source, a category group the target.
function useDrag(
	dragging: Ref<string | null>,
	dropTarget: Ref<string | null>,
	move: (ticketType: TicketTypeItem, key: string) => void,
) {
	let source: TicketTypeItem | null = null

	function end() {
		source = null
		dragging.value = null
		dropTarget.value = null
	}

	const handle = (ticketType: TicketTypeItem) => ({
		dragstart: (event: DragEvent) => {
			event.dataTransfer!.effectAllowed = "move"
			source = ticketType
			// Deferred so the browser snapshots the card before it dims.
			requestAnimationFrame(() => (dragging.value = ticketType.name))
		},
		dragend: end,
	})

	const zone = (key: string) => ({
		dragover: (event: DragEvent) => {
			if (!source) return
			event.preventDefault()
			dropTarget.value = key
		},
		dragleave: (event: DragEvent) => {
			const target = event.currentTarget as HTMLElement
			if (!target.contains(event.relatedTarget as Node) && dropTarget.value === key)
				dropTarget.value = null
		},
		drop: (event: DragEvent) => {
			event.preventDefault()
			if (source) move(source, key)
			end()
		},
	})

	return { handle, zone }
}
