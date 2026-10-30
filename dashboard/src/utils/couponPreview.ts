import type { CouponTicketType, TierPrice } from "@/types"

import { type CouponValues, eligibleTicketTypes } from "./couponForm.ts"
import { wholeAmount } from "./couponLabels.ts"

export type PreviewPick = { ticketType?: string; currency?: string }

export type CheckoutPreview = {
	ticketType: string
	currency: string
	quantity: number
	subtotal: number
	discount: number
	total: number
	note?: string
}

const amountIn = (rows: TierPrice[], currency: string) =>
	rows.find((row) => row.currency === currency)?.price ?? 0

// Enough tickets to meet the coupon's minimum, so the preview shows it applying.
function quantityFor(values: CouponValues, price: number, currency: string) {
	if (values.minimum_requirement === "Minimum Ticket Count")
		return Math.max(values.minimum_ticket_count, 1)
	if (values.minimum_requirement === "Minimum Order Amount")
		return Math.max(Math.ceil(amountIn(values.minimum_order_amounts, currency) / price), 1)
	return 1
}

function discountFor(values: CouponValues, subtotal: number, currency: string) {
	if (values.discount_type === "Percentage")
		return Math.round(subtotal * Math.min(values.discount_percentage, 100)) / 100
	return Math.min(amountIn(values.discount_amounts, currency), subtotal)
}

function noteFor(values: CouponValues, line: string, currency: string, subtotal: number) {
	const minimum = amountIn(values.minimum_order_amounts, currency)
	if (
		values.discount_type === "Flat Amount" &&
		amountIn(values.discount_amounts, currency) > subtotal
	)
		return "The discount is capped at the order total."
	if (values.minimum_requirement === "Minimum Order Amount" && minimum > 0)
		return `${line} reaches the ${wholeAmount(minimum, currency)} minimum.`
	if (values.minimum_requirement === "Minimum Ticket Count" && values.minimum_ticket_count > 0)
		return `Shown with the minimum of ${values.minimum_ticket_count} tickets.`
}

/** One eligible ticket type's order at checkout, priced the way `discount_for` prices it. */
export function checkoutPreview(
	values: CouponValues,
	ticketTypes: CouponTicketType[],
	pick: PreviewPick,
): CheckoutPreview | null {
	const eligible = eligibleTicketTypes(values, ticketTypes)
	const ticketType = eligible.find((row) => row.name === pick.ticketType) ?? eligible[0]
	if (!ticketType) return null
	const prices = ticketType.prices.filter((row) => row.price > 0)
	const price = prices.find((row) => row.currency === pick.currency) ?? prices[0]
	const quantity = quantityFor(values, price.price, price.currency)
	const subtotal = price.price * quantity
	const discount = discountFor(values, subtotal, price.currency)
	return {
		ticketType: ticketType.name,
		currency: price.currency,
		quantity,
		subtotal,
		discount,
		total: subtotal - discount,
		note: noteFor(values, `${ticketType.title} × ${quantity}`, price.currency, subtotal),
	}
}
