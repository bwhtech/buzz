import { computed, type Ref } from "vue"

import type { AvailableAddOn, AvailableTicketType, BookingAttendee } from "@/types"

import { useDiscountQuote } from "./useDiscountQuote"

export interface PricingInputs {
	attendees: Ref<BookingAttendee[]>
	ticketTypesMap: Ref<Record<string, AvailableTicketType>>
	addOnsMap: Ref<Record<string, AvailableAddOn>>
	taxSettings: () => Record<string, any>
	currency: Ref<string>
	eventId: Ref<string | null>
	guestEmail: () => string | null
}

interface SummaryLine {
	key: string
	title: string
	count: number
	amount: number
}

/** Order lines, coupon, discount and tax for the attendees picked so far. */
export function useOrderPricing(inputs: PricingInputs) {
	const { attendees, ticketTypesMap, addOnsMap } = inputs

	const lines = computed(() => {
		const byKey: Record<string, SummaryLine> = {}
		const add = (key: string, item?: AvailableTicketType | AvailableAddOn) => {
			if (!item) return
			byKey[key] ??= { key, title: item.title ?? "", count: 0, amount: 0 }
			byKey[key].count++
			byKey[key].amount += item.price ?? 0
		}
		for (const attendee of attendees.value) {
			add(`ticket-${attendee.ticket_type}`, ticketTypesMap.value[String(attendee.ticket_type)])
			for (const [name, selection] of Object.entries(attendee.add_ons ?? {})) {
				if (selection.selected) add(`add-on-${name}`, addOnsMap.value[name])
			}
		}
		const all = Object.values(byKey)
		return [
			...all.filter((line) => line.key.startsWith("ticket-")),
			...all.filter((line) => line.key.startsWith("add-on-")),
		]
	})

	const netAmount = computed(() => lines.value.reduce((sum, line) => sum + line.amount, 0))

	const coupon = useDiscountQuote(inputs, netAmount)
	const discountAmount = coupon.discountAmount

	const tax = computed(() => {
		const settings = inputs.taxSettings()
		return {
			apply: Boolean(settings.apply_tax),
			label: settings.tax_label || "Tax",
			percentage: settings.apply_tax ? settings.tax_percentage || 0 : 0,
			inclusive: Boolean(settings.tax_inclusive),
		}
	})

	const amountAfterDiscount = computed(() => netAmount.value - discountAmount.value)

	const taxAmount = computed(() => {
		const { apply, percentage, inclusive } = tax.value
		if (!apply) return 0
		// An inclusive price already holds the tax, so it's backed out of the amount.
		if (inclusive)
			return Math.round(((amountAfterDiscount.value * percentage) / (100 + percentage)) * 100) / 100
		return (amountAfterDiscount.value * percentage) / 100
	})

	const total = computed(() =>
		tax.value.inclusive ? amountAfterDiscount.value : amountAfterDiscount.value + taxAmount.value,
	)
	const totalBeforeDiscount = computed(() =>
		tax.value.inclusive ? netAmount.value : netAmount.value * (1 + tax.value.percentage / 100),
	)

	return {
		lines,
		netAmount,
		discountAmount,
		tax,
		taxAmount,
		total,
		totalBeforeDiscount,
		coupon,
		couponNote: coupon.note,
	}
}
