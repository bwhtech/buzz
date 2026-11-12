// Dev-only data for stress-testing the transactions list; chosen with `?data=`.
import type {
	CurrencySummary,
	DailyRevenue,
	TransactionRow,
	TransactionsPage,
	TransactionSummary,
} from "@/types"

export const DEV_DATA_KINDS = ["worst", "empty", "one", "many"] as const
export type DevDataKind = (typeof DEV_DATA_KINDS)[number]

const MATCHED_TOTAL = 1284
const MINUTE = 60_000
const YEAR = 365 * 24 * 60 * MINUTE
const PAYMENT_INTENT = "pi_3PqXyZ2eZvKYlo2C1abcDEFg"
const PAYPAL_ORDER = "PAYID-MZX4QKI7BH12345678901234"
const LONG_EMAIL = "bartholomew.fitzgerald@northwind-industries-holdings.example.com"

type Overrides = Partial<TransactionRow> & { ago?: number }

function row(index: number, overrides: Overrides): TransactionRow {
	const { ago = index * 37 * MINUTE, ...rest } = overrides
	return {
		created_at: new Date(Date.now() - ago).toISOString(),
		buyer_name: "Jane Doe",
		buyer_email: "jane@example.com",
		tickets: 2,
		total_amount: 1500,
		currency: "INR",
		payment_method: "Stripe",
		payment_status: "Paid",
		refund_status: null,
		payment_id: PAYMENT_INTENT,
		...rest,
		name: rest.name ?? `B${String(index + 1).padStart(3, "0")}`,
	}
}

const WORST_ROWS: Overrides[] = [
	{ buyer_name: "Aleksandra Wiśniewska-Kowalczyk", buyer_email: LONG_EMAIL, ago: 0 },
	{
		buyer_name: "Bartholomew Fitzgerald-Montgomery III",
		buyer_email: LONG_EMAIL,
		total_amount: 1284999.99,
		ago: -2 * MINUTE,
	},
	{
		buyer_name: null,
		buyer_email: "ops@sub.department.region.example.co.uk",
		total_amount: 0.5,
		currency: "USD",
		payment_id: null,
	},
	{
		buyer_name: "Jo",
		buyer_email: null,
		tickets: 1,
		total_amount: 123456789,
		currency: "INR",
		ago: 3 * YEAR,
	},
	{
		buyer_name: "Nguyễn Thị Phương Thảo",
		buyer_email: "thao@example.com",
		currency: "EUR",
		payment_id: PAYPAL_ORDER,
	},
	{
		buyer_name: "محمد عبدالله",
		buyer_email: "mohammed@example.org",
		currency: "JPY",
		total_amount: 15000,
	},
	{
		buyer_name: "🦊 Fox 👩🏽‍💻 Priya",
		buyer_email: "fox@example.com",
		tickets: 250,
		total_amount: 375000,
	},
	{
		buyer_name: "आदित्य कुमार सिंह राठौड़",
		buyer_email: "aditya@example.in",
		refund_status: "Partially Refunded",
	},
	{
		buyer_name: "Christopher Alexander Montgomery III",
		buyer_email: "c@b.co",
		refund_status: "Refund Initiated",
	},
	{
		buyer_name: "María José de la Cruz y Fernández",
		buyer_email: "first.last+billing-notifications@example.com",
		refund_status: "Refunded",
	},
	{
		buyer_name: "Sam Lee",
		buyer_email: "sam@example.com",
		payment_status: "Verification Pending",
		payment_id: null,
	},
	{
		buyer_name: "Dana Unknown",
		buyer_email: "dana@example.com",
		payment_status: "Awaiting Settlement Confirmation",
	},
	{
		buyer_name: "  Sam   Lee ",
		buyer_email: "sam2@example.com",
		payment_status: null,
		total_amount: 0,
	},
	{ buyer_name: "<b>Bold</b> &amp; Co", buyer_email: "tags@example.com", total_amount: -42.5 },
	{ name: "BOOK-2026-11-000128", buyer_name: "Long Booking Name", buyer_email: "long@example.com" },
]

function worstRow(index: number): TransactionRow {
	const base = WORST_ROWS[index % WORST_ROWS.length]
	return row(index, index < WORST_ROWS.length ? base : { ...base, name: undefined })
}

const manyRow = (index: number) =>
	row(index, {
		buyer_name: `Buyer ${index + 1}`,
		buyer_email: `buyer${index + 1}@example.com`,
		total_amount: 500 * ((index % 9) + 1),
	})

const builders: Record<DevDataKind, (index: number) => TransactionRow> = {
	worst: worstRow,
	many: manyRow,
	one: (index) => worstRow(index + 2),
	empty: worstRow,
}

const matchedByKind: Record<DevDataKind, number> = {
	worst: MATCHED_TOTAL,
	many: MATCHED_TOTAL,
	one: 1,
	empty: 0,
}

export function devDataKind(): DevDataKind | null {
	if (!import.meta.env.DEV) return null
	const kind = new URLSearchParams(window.location.search).get("data")
	return DEV_DATA_KINDS.find((candidate) => candidate === kind) ?? null
}

/** Swaps one page of server rows for fixture rows; `matched` stays realistic. */
export function devTransactionsPage(
	page: TransactionsPage,
	start: number,
	limit: number,
): TransactionsPage {
	const kind = devDataKind()
	if (!kind) return page
	const matched = matchedByKind[kind]
	const count = Math.max(0, Math.min(limit, matched - start))
	return {
		...page,
		title:
			kind === "worst"
				? "Frappe Build 2026: The Annual Conference on Open Source Business Software and Community"
				: page.title,
		total: matched,
		matched,
		has_next_page: start + count < matched,
		currencies: ["INR", "USD", "EUR", "JPY"],
		transactions: Array.from({ length: count }, (_, offset) => builders[kind](start + offset)),
	}
}

const currencyTotals = (currency: string, scale: number, bookings: number): CurrencySummary => ({
	currency,
	collected: 1284999.99 * scale,
	refunded: 12500.5 * scale,
	net: 1272499.49 * scale,
	tax: 195999.5 * scale,
	discounts: 4200 * scale,
	bookings,
	tickets: bookings * 2,
	average_order_value: 1000.77 * scale,
})

const EMPTY_SUMMARY: TransactionSummary = {
	currencies: [],
	daily: [],
	pending_verification: [],
	by_payment_method: [],
}

/** Ninety days of sales up to today, uneven like a real launch. */
function dailyFixture(currency: string, scale: number): DailyRevenue[] {
	return Array.from({ length: 90 }, (_, index) => {
		const date = new Date(Date.now() - (89 - index) * 86_400_000).toISOString().slice(0, 10)
		const bookings = Math.round((Math.sin(index / 6) + 1.4) * (index / 15 + 1))
		return {
			date,
			currency,
			bookings,
			collected: bookings * 1000 * scale,
			refunded: index % 11 ? 0 : 500 * scale,
		}
	})
}

const SUMMARIES: Record<DevDataKind, TransactionSummary> = {
	worst: {
		currencies: [
			currencyTotals("INR", 100, 1284),
			currencyTotals("USD", 1, 87),
			currencyTotals("JPY", 150, 1),
		],
		daily: [...dailyFixture("INR", 100), ...dailyFixture("USD", 1)],
		pending_verification: [{ currency: "INR", bookings: 1, amount: 123456789 }],
		by_payment_method: [
			{ currency: "INR", payment_method: "Razorpay", bookings: 900, amount: 90000000 },
			{
				currency: "INR",
				payment_method: "Offline: Bank transfer to the organiser's account",
				bookings: 300,
				amount: 30000000,
			},
			{ currency: "INR", payment_method: "Stripe", bookings: 80, amount: 8000000 },
			{ currency: "INR", payment_method: "Cash", bookings: 3, amount: 300000 },
			{ currency: "INR", payment_method: null, bookings: 1, amount: 499.99 },
			{ currency: "USD", payment_method: "Stripe", bookings: 87, amount: 1284999.99 },
		],
	},
	many: {
		...EMPTY_SUMMARY,
		currencies: [currencyTotals("INR", 1, 1284)],
		daily: dailyFixture("INR", 1),
		by_payment_method: [
			{ currency: "INR", payment_method: "Razorpay", bookings: 1284, amount: 1284999.99 },
		],
	},
	one: {
		...EMPTY_SUMMARY,
		currencies: [{ ...currencyTotals("INR", 0.001, 1), tickets: 1 }],
		by_payment_method: [{ currency: "INR", payment_method: "Razorpay", bookings: 1, amount: 1285 }],
	},
	empty: EMPTY_SUMMARY,
}

export function devTransactionSummary(summary: TransactionSummary): TransactionSummary {
	const kind = devDataKind()
	return kind ? SUMMARIES[kind] : summary
}
