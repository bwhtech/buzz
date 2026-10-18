import { useRouteQuery } from "@vueuse/router"
import { toast, useCall } from "frappe-ui"
import { computed, ref, watch, type Ref } from "vue"

import type { AvailableAddOn, AvailableTicketType, BookingAttendee, CouponData } from "@/types"
import { formatCurrency, formatPriceOrFree } from "@/utils/currency"
import { serverErrorMessage } from "@/utils/serverError"

interface PricingInputs {
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

	const coupon = useCoupon(inputs, netAmount)
	const discountAmount = computed(() => coupon.discountFor(netAmount.value))

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
		couponNote: computed(() => coupon.note(discountAmount.value)),
	}
}

function useCoupon(inputs: PricingInputs, netAmount: Ref<number>) {
	const { attendees, ticketTypesMap, addOnsMap, currency } = inputs
	// Keeps the URL in step with the applied coupon, so a shared link carries it.
	const couponQuery = useRouteQuery<string | null>("coupon", null)
	const code = ref("")
	const error = ref("")
	const data = ref<CouponData | null>(null)
	const applied = computed(() => Boolean(data.value))

	// POST although it only reads: a guest's email stays out of the query string.
	const validateCall = useCall<Record<string, any>, Record<string, any>>({
		url: "/api/v2/method/buzz.api.booking.validate_coupon",
		method: "POST",
		immediate: false,
	})

	const freeTicketHolders = computed(() => {
		const coupon = data.value
		if (coupon?.coupon_type !== "Free Tickets") return []
		const holders = attendees.value.filter(
			(a) => String(a.ticket_type) === String(coupon.ticket_type),
		)
		return holders.slice(0, coupon.remaining_tickets ?? 0)
	})
	const eligibleCount = computed(() =>
		data.value?.coupon_type === "Free Tickets"
			? attendees.value.filter((a) => String(a.ticket_type) === String(data.value?.ticket_type))
					.length
			: 0,
	)

	function discountFor(amount: number) {
		const coupon = data.value
		if (!coupon) return 0
		if (coupon.coupon_type === "Free Tickets") return freeTicketsDiscount(coupon)
		if (coupon.discount_type === "Percentage") {
			const discount = amount * ((coupon.discount_value ?? 0) / 100)
			return coupon.max_discount_amount ? Math.min(discount, coupon.max_discount_amount) : discount
		}
		return Math.min(coupon.discount_value ?? 0, amount)
	}

	// Free tickets also make their holders' free add-ons free.
	function freeTicketsDiscount(coupon: CouponData) {
		const ticketPrice = ticketTypesMap.value[coupon.ticket_type ?? ""]?.price ?? 0
		let discount = freeTicketHolders.value.length * ticketPrice
		for (const holder of freeTicketHolders.value) {
			for (const addOn of coupon.free_add_ons ?? []) {
				if (holder.add_ons?.[addOn]?.selected) discount += addOnsMap.value[addOn]?.price ?? 0
			}
		}
		return discount
	}

	async function apply() {
		const normalized = code.value.trim().toUpperCase()
		if (!normalized) {
			error.value = __("Please enter a coupon code")
			return
		}
		code.value = normalized
		error.value = ""
		const email = inputs.guestEmail()?.trim().toLowerCase()
		const result = await validateCall
			.submit({
				coupon_code: normalized,
				event: inputs.eventId.value,
				currency: currency.value,
				// Lets the server check a guest's per-person limit.
				...(email ? { user_email: email } : {}),
			})
			.catch(() => null)
		if (validateCall.error || !result) {
			error.value = serverErrorMessage(validateCall.error) || __("Failed to validate coupon")
			return
		}
		if (!result.valid) {
			data.value = null
			error.value = result.error
			return
		}
		if (result.coupon_type === "Discount" && result.min_order_value > netAmount.value) {
			error.value = __("Add {0} more to use this coupon (min order {1})", [
				formatCurrency(result.min_order_value - netAmount.value, currency.value),
				formatCurrency(result.min_order_value, currency.value),
			])
			return
		}
		data.value = couponFromResult(result)
		couponQuery.value = normalized
	}

	function remove() {
		code.value = ""
		error.value = ""
		data.value = null
		couponQuery.value = null
	}

	function note(discount: number) {
		const coupon = data.value
		if (!coupon) return ""
		if (coupon.coupon_type === "Free Tickets") {
			const ticketTitle =
				ticketTypesMap.value[coupon.ticket_type ?? ""]?.title || coupon.ticket_type || ""
			return __("{0} free · {1} of {2} eligible", [
				__(ticketTitle),
				eligibleCount.value,
				attendees.value.length,
			])
		}
		const off =
			coupon.discount_type === "Percentage"
				? `${coupon.discount_value}%`
				: formatPriceOrFree(coupon.discount_value, currency.value)
		return __("{0} off · you save {1}", [off, formatCurrency(discount, currency.value)])
	}

	watch(currency, () => applied.value && apply())

	watch(netAmount, (amount) => {
		if (amount < (data.value?.min_order_value ?? 0)) {
			remove()
			toast.warning(__("Coupon removed - minimum order not met"))
		}
	})

	watch(eligibleCount, (count) => {
		if (count === 0 && data.value?.coupon_type === "Free Tickets") {
			remove()
			toast.warning(__("Coupon removed — no eligible attendees for this ticket type"))
		}
	})

	// A ?coupon= link applies its code once the form is ready.
	function applyFromLink() {
		const linked = couponQuery.value
		if (typeof linked !== "string" || !linked.trim() || applied.value) return
		code.value = linked.trim().toUpperCase()
		return apply()
	}

	return {
		code,
		error,
		data,
		applied,
		loading: computed(() => validateCall.loading),
		apply,
		remove,
		applyFromLink,
		discountFor,
		note,
	}
}

function couponFromResult(result: Record<string, any>): CouponData {
	if (result.coupon_type === "Discount") {
		return {
			coupon_type: "Discount",
			discount_type: result.discount_type,
			discount_value: result.discount_value,
			max_discount_amount: result.max_discount_amount || 0,
			min_order_value: result.min_order_value || 0,
		}
	}
	return {
		coupon_type: "Free Tickets",
		ticket_type: String(result.ticket_type),
		remaining_tickets: result.remaining_tickets,
		free_add_ons: result.free_add_ons || [],
	}
}
