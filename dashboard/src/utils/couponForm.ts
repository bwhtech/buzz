import type { CouponItem, CouponTicketType, TierPrice } from "@/types"

export type CouponValues = Pick<
	CouponItem,
	| "coupon_type"
	| "code"
	| "description"
	| "discount_type"
	| "discount_percentage"
	| "discount_amounts"
	| "applies_to_all_ticket_types"
	| "ticket_types"
	| "minimum_requirement"
	| "minimum_order_amounts"
	| "minimum_ticket_count"
	| "usage_limit"
	| "once_per_buyer"
	| "starts_on"
	| "expires_on"
>

export function blankCouponValues(
	couponType: CouponValues["coupon_type"] = "Promo Code",
): CouponValues {
	return {
		coupon_type: couponType,
		code: "",
		description: "",
		// No discount only makes sense for an access code, and is its default.
		discount_type: couponType === "Access Code" ? "None" : "Percentage",
		discount_percentage: 0,
		discount_amounts: [],
		applies_to_all_ticket_types: true,
		ticket_types: [],
		minimum_requirement: "None",
		minimum_order_amounts: [],
		minimum_ticket_count: 0,
		usage_limit: 0,
		once_per_buyer: true,
		starts_on: null,
		expires_on: null,
	}
}

export function couponValuesOf(coupon: CouponItem): CouponValues {
	const fields = Object.keys(blankCouponValues()) as (keyof CouponValues)[]
	// A JSON copy, since structuredClone refuses the reactive proxies a page's data arrives in.
	const values = Object.fromEntries(
		fields.map((field) => [field, JSON.parse(JSON.stringify(coupon[field] ?? null))]),
	)
	return {
		...(values as CouponValues),
		code: coupon.code ?? "",
		description: coupon.description ?? "",
	}
}

/** Promo and access codes are typed by participants; an automatic offer is only named. */
export const isTypedCode = (values: Pick<CouponValues, "coupon_type">) =>
	values.coupon_type !== "Automatic"

export const isAccessCode = (values: Pick<CouponValues, "coupon_type">) =>
	values.coupon_type === "Access Code"

// An access code always names the hidden types it unlocks.
const coversAllTicketTypes = (values: CouponValues) =>
	values.applies_to_all_ticket_types && !isAccessCode(values)

const isPaid = (ticketType: CouponTicketType) => ticketType.prices.some((row) => row.price > 0)

export function eligibleTicketTypes(values: CouponValues, ticketTypes: CouponTicketType[]) {
	return ticketTypes.filter(
		(ticketType) =>
			isPaid(ticketType) &&
			(coversAllTicketTypes(values) || values.ticket_types.includes(ticketType.name)),
	)
}

export function couponCurrencies(values: CouponValues, ticketTypes: CouponTicketType[]) {
	const currencies = eligibleTicketTypes(values, ticketTypes).flatMap((ticketType) =>
		ticketType.prices.filter((row) => row.price > 0).map((row) => row.currency),
	)
	return [...new Set(currencies)]
}

function coversCurrencies(rows: TierPrice[], currencies: string[]) {
	return currencies.every((currency) =>
		rows.some((row) => row.currency === currency && row.price > 0),
	)
}

function discountError(values: CouponValues, currencies: string[]) {
	if (
		values.discount_type === "Flat Amount" &&
		!coversCurrencies(values.discount_amounts, currencies)
	)
		return "Enter a discount amount for every currency."
	const percentage = values.discount_percentage
	if (values.discount_type === "Percentage" && !(percentage > 0 && percentage <= 100))
		return "Enter a discount between 1 and 100%."
	return null
}

function minimumError(values: CouponValues, currencies: string[]) {
	if (values.minimum_requirement === "Minimum Ticket Count" && !(values.minimum_ticket_count > 0))
		return "Enter a minimum ticket count above 0."
	if (
		values.minimum_requirement === "Minimum Order Amount" &&
		!coversCurrencies(values.minimum_order_amounts, currencies)
	)
		return "Enter a minimum order amount for every currency."
	return null
}

function scopeError(values: CouponValues, currencies: string[]) {
	// An access code can unlock free tickets, so it needs a scope rather than a price.
	if (isAccessCode(values))
		return values.ticket_types.length ? null : "Pick at least one hidden ticket type to unlock."
	if (currencies.length) return null
	return coversAllTicketTypes(values)
		? "Add a paid ticket type to the event first."
		: "Pick at least one paid ticket type."
}

const PROMO_CODE_PATTERN = /^[A-Z0-9_-]+$/

/** Letters, digits, hyphens and underscores only, upper-cased: what checkout can match. */
export const cleanPromoCode = (code: string) => code.toUpperCase().replace(/[^A-Z0-9_-]/g, "")

function codeError(values: CouponValues) {
	const code = values.code?.trim()
	if (!code) return isTypedCode(values) ? "Enter a code." : "Enter a name."
	if (isTypedCode(values) && !PROMO_CODE_PATTERN.test(code.toUpperCase()))
		return "Codes can only use letters, numbers, - and _."
	return null
}

/** Why the coupon can't be saved yet, or null when it can. */
export function couponError(values: CouponValues, ticketTypes: CouponTicketType[]) {
	const currencies = couponCurrencies(values, ticketTypes)
	const datesError =
		values.starts_on && values.expires_on && values.starts_on > values.expires_on
			? "The start date must be on or before the end date."
			: null
	return (
		codeError(values) ??
		scopeError(values, currencies) ??
		discountError(values, currencies) ??
		minimumError(values, currencies) ??
		datesError
	)
}

export const isCouponValid = (values: CouponValues, ticketTypes: CouponTicketType[]) =>
	!couponError(values, ticketTypes)

const onlyCurrencies = (rows: TierPrice[], currencies: string[]) =>
	rows.filter((row) => currencies.includes(row.currency))

/** The values as the doctype stores them. */
export function couponDocValues(values: CouponValues, ticketTypes: CouponTicketType[]) {
	const currencies = couponCurrencies(values, ticketTypes)
	return {
		...values,
		code: isTypedCode(values) ? values.code.trim().toUpperCase() : values.code.trim(),
		applies_to_all_ticket_types: coversAllTicketTypes(values),
		description: values.description?.trim() ?? "",
		starts_on: values.starts_on || null,
		expires_on: values.expires_on || null,
		discount_amounts: onlyCurrencies(values.discount_amounts, currencies),
		minimum_order_amounts: onlyCurrencies(values.minimum_order_amounts, currencies),
		ticket_types: coversAllTicketTypes(values)
			? []
			: values.ticket_types.map((ticket_type) => ({ ticket_type })),
	}
}

const CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

/** Eight characters, without look-alikes such as O and 0. */
export function generateCode() {
	const picks = crypto.getRandomValues(new Uint32Array(8))
	return Array.from(picks, (pick) => CODE_ALPHABET[pick % CODE_ALPHABET.length]).join("")
}
