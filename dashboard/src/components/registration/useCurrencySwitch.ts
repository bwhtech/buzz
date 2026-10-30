import { computed, ref, type Ref } from "vue"

import type { AvailableAddOn, AvailableTicketType, BookingAttendee } from "@/types"

type Priced = { price?: number; currency?: string; prices?: { currency: string; price: number }[] }

// A free item sells in every currency; a priced one only where it has a price row.
export function priceIn(item: Priced, currency: string) {
	if (currency === item.currency) return item.price ?? 0
	if (!item.price) return 0
	return item.prices?.find((row) => row.currency === currency)?.price
}

export function pricedIn<T extends Priced>(item: T, currency: string): T {
	const price = priceIn(item, currency)
	return price === undefined ? item : { ...item, price, currency }
}

/**
 * The currency the order is paid in. Switching drops tickets and add-ons not sold in the
 * new currency, and keeps what it dropped so the person can undo the switch.
 */
export function useCurrencySwitch(
	ticketTypes: Ref<AvailableTicketType[]>,
	addOns: Ref<AvailableAddOn[]>,
	attendees: Ref<BookingAttendee[]>,
) {
	const baseCurrency = computed(() => ticketTypes.value[0]?.currency || "INR")
	const currency = ref(baseCurrency.value)
	const undoState = ref<{ attendees: string; currency: string; message: string } | null>(null)

	const currencies = computed(() => [
		...new Set(
			ticketTypes.value.flatMap((ticketType) =>
				(ticketType.prices ?? []).map((row) => row.currency),
			),
		),
	])

	const notSoldIn = (item: Priced) => priceIn(item, currency.value) === undefined

	function setCurrency(next: string) {
		if (next === currency.value) return
		const snapshot = JSON.stringify(attendees.value)
		const dropped = new Set<string>()
		const ticketTypesByName = Object.fromEntries(ticketTypes.value.map((t) => [String(t.name), t]))
		attendees.value = attendees.value.filter((attendee) => {
			const ticketType = ticketTypesByName[String(attendee.ticket_type)]
			const sold = !ticketType || priceIn(ticketType, next) !== undefined
			if (!sold) dropped.add(__(ticketType.title ?? ""))
			return sold
		})
		for (const addOn of addOns.value) {
			if (priceIn(addOn, next) !== undefined) continue
			for (const attendee of attendees.value) {
				const selection = attendee.add_ons?.[addOn.name]
				if (selection?.selected) {
					selection.selected = false
					dropped.add(__(addOn.title ?? ""))
				}
			}
		}
		undoState.value = dropped.size
			? {
					attendees: snapshot,
					currency: currency.value,
					message: __("Removed {0}. Not sold in {1}.", [[...dropped].join(", "), next]),
				}
			: null
		currency.value = next
	}

	function undo() {
		if (!undoState.value) return
		attendees.value = JSON.parse(undoState.value.attendees)
		currency.value = undoState.value.currency
		undoState.value = null
	}

	const removedMessage = computed(() => undoState.value?.message ?? "")
	const dismissUndo = () => (undoState.value = null)

	return {
		baseCurrency,
		currency,
		currencies,
		notSoldIn,
		setCurrency,
		undo,
		dismissUndo,
		removedMessage,
	}
}
