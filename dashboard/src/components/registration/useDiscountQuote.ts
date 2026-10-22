import { watchDebounced } from "@vueuse/core"
import { useRouteQuery } from "@vueuse/router"
import { toast, useCall } from "frappe-ui"
import { computed, ref, type Ref } from "vue"

import type { DiscountQuote } from "@/types"
import { formatCurrency } from "@/utils/currency"
import { serverErrorMessage } from "@/utils/serverError"

import type { PricingInputs } from "./useOrderPricing"

/** Server-side discount for the picked tickets: the best automatic coupon or the applied promo code. */
export function useDiscountQuote(inputs: PricingInputs, netAmount: Ref<number>) {
	const { attendees, currency } = inputs
	// Keeps the URL in step with the applied code, so a shared link carries it.
	const codeQuery = useRouteQuery<string | null>("coupon", null)
	const code = ref("")
	const appliedCode = ref("")
	const error = ref("")
	const quote = ref<DiscountQuote | null>(null)
	const applied = computed(() => Boolean(appliedCode.value))

	// POST although it only reads: a guest's email stays out of the query string.
	const quoteCall = useCall<DiscountQuote, Record<string, any>>({
		url: "/api/v2/method/buzz.api.booking.get_discount",
		method: "POST",
		immediate: false,
	})

	const discountAmount = computed(() =>
		netAmount.value > 0 ? (quote.value?.discount_amount ?? 0) : 0,
	)

	const ticketMix = computed(() =>
		attendees.value
			.map((attendee) => String(attendee.ticket_type))
			.toSorted()
			.join(","),
	)

	function fetchQuote(couponCode: string) {
		const email = inputs.guestEmail()?.trim().toLowerCase()
		return quoteCall
			.submit({
				quote: {
					event: inputs.eventId.value,
					currency: currency.value,
					ticket_types: attendees.value.map((attendee) => String(attendee.ticket_type)),
					coupon_code: couponCode || null,
					buyer_email: email || null,
				},
			})
			.catch(() => null)
	}

	async function apply() {
		const normalized = code.value.trim().toUpperCase()
		if (!normalized) {
			error.value = __("Please enter a coupon code")
			return
		}
		code.value = normalized
		error.value = ""
		const result = await fetchQuote(normalized)
		if (!result) {
			error.value = serverErrorMessage(quoteCall.error) || __("Failed to validate coupon")
			return
		}
		if (result.error) {
			error.value = result.error
			return
		}
		quote.value = result
		appliedCode.value = normalized
		codeQuery.value = normalized
	}

	function remove() {
		code.value = ""
		error.value = ""
		appliedCode.value = ""
		codeQuery.value = null
	}

	async function refreshQuote() {
		if (netAmount.value <= 0 || !attendees.value.length) {
			quote.value = null
			return
		}
		const result = await fetchQuote(appliedCode.value)
		if (result?.error) {
			remove()
			toast.warning(__("Coupon removed: {0}", [result.error]))
			return
		}
		quote.value = result ?? quote.value
	}

	watchDebounced([ticketMix, currency, appliedCode, () => inputs.guestEmail()], refreshQuote, {
		debounce: 300,
	})

	const note = computed(() =>
		applied.value ? __("You save {0}", [formatCurrency(discountAmount.value, currency.value)]) : "",
	)

	// A ?coupon= link applies its code once the form is ready.
	function applyFromLink() {
		const linked = codeQuery.value
		if (typeof linked !== "string" || !linked.trim() || applied.value) return
		code.value = linked
		return apply()
	}

	return {
		code,
		appliedCode,
		error,
		applied,
		loading: computed(() => quoteCall.loading),
		discountAmount,
		note,
		apply,
		remove,
		applyFromLink,
	}
}
