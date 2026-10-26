import type { CouponItem, CouponStatus, CouponTicketType, TierPrice } from "@/types"

import { formatCurrency } from "./currency.ts"

export function wholeAmount(amount: number, currency: string) {
	const digits = Number.isInteger(amount) ? 0 : 2
	return formatCurrency(amount, currency, "en-US", {
		minimumFractionDigits: digits,
		maximumFractionDigits: digits,
	})
}

export function amountsLabel(rows: TierPrice[]) {
	return rows.map((row) => wholeAmount(row.price, row.currency)).join(" · ")
}

export function discountLabel(coupon: CouponItem) {
	if (coupon.discount_type === "None") return "No discount"
	if (coupon.discount_type === "Percentage") return `${coupon.discount_percentage}% off`
	return `${amountsLabel(coupon.discount_amounts)} off`
}

const TYPE_LABELS: Record<CouponItem["coupon_type"], string> = {
	"Promo Code": "Promo code",
	Automatic: "Automatic",
	"Access Code": "Access code",
}

export const typeLabel = (coupon: CouponItem) => TYPE_LABELS[coupon.coupon_type]

/** The registration page with the code filled in, so the link unlocks the hidden tickets. */
export function accessCodeLink(registrationLink: string, code: string) {
	const url = new URL(registrationLink, window.location.origin)
	url.searchParams.set("code", code)
	return url.toString()
}

export function scopeLabel(coupon: CouponItem, ticketTypes: CouponTicketType[]) {
	if (coupon.applies_to_all_ticket_types) return "All tickets"
	return ticketTypes
		.filter((ticketType) => coupon.ticket_types.includes(ticketType.name))
		.map((ticketType) => ticketType.title)
		.join(", ")
}

export function usedLabel(coupon: CouponItem) {
	const used = coupon.times_used.toLocaleString()
	return coupon.usage_limit
		? `${used} / ${coupon.usage_limit.toLocaleString()} used`
		: `${used} used`
}

export function conditionLabel(coupon: CouponItem) {
	if (coupon.minimum_requirement === "Minimum Ticket Count")
		return `${coupon.minimum_ticket_count}+ tickets`
	if (coupon.minimum_requirement === "Minimum Order Amount")
		return `Orders from ${coupon.minimum_order_amounts.map((row) => wholeAmount(row.price, row.currency)).join(" / ")}`
	return null
}

function shortDate(day: string) {
	const date = new Date(`${day}T00:00`)
	return `${date.getDate()} ${date.toLocaleDateString("en-US", { month: "short" })}`
}

export const endsLabel = (coupon: CouponItem) =>
	coupon.expires_on ? `Ends ${shortDate(coupon.expires_on)}` : "No end date"

export const statusLabel = (coupon: CouponItem) =>
	coupon.status === "Scheduled" && coupon.starts_on
		? `Starts ${shortDate(coupon.starts_on)}`
		: coupon.status

const STATUS_THEMES: Partial<Record<CouponStatus, "green" | "blue">> = {
	Active: "green",
	Scheduled: "blue",
}

export function statusTheme(status: CouponStatus) {
	return STATUS_THEMES[status] ?? "gray"
}

export function couponStats(
	coupons: CouponItem[],
	discounted: { currency: string; amount: number }[],
) {
	const redeemed = coupons.reduce((sum, coupon) => sum + coupon.times_used, 0)
	const amounts = discounted.map((row) => ({ currency: row.currency, price: row.amount }))
	return [
		{
			label: "Active coupons",
			value: String(coupons.filter((coupon) => coupon.status === "Active").length),
		},
		{ label: "Redemptions", value: redeemed.toLocaleString() },
		{ label: "Discounted", value: amounts.length ? amountsLabel(amounts) : "—" },
	]
}
