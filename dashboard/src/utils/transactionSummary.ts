import type { DailyRevenue, TransactionSummary } from "@/types"

export type Money = (amount: number, currency: string) => string

export type MethodShare = { method: string; amount: number; bookings: number; percent: number }

export type Period = "7d" | "30d" | "all"

export type PeriodStats = {
	net: number
	refunded: number
	bookings: number
	averageOrder: number
	// The same stretch just before; null for "all", which has nothing before it.
	previousNet: number | null
	previousBookings: number | null
	// Running net through the period, so a sparse event still reads as a curve.
	netRunning: number[]
	// Bookings per day, grouped into at most MAX_BARS bars.
	bookingBars: number[]
}

const PERIOD_DAYS: Record<Period, number | null> = { "7d": 7, "30d": 30, all: null }
const DAY_MS = 86_400_000
const MAX_BARS = 30

/** Busiest first; amounts in two currencies are never summed, so one is shown at a time. */
export function currenciesByVolume(summary: TransactionSummary): string[] {
	return summary.currencies
		.toSorted((first, second) => second.bookings - first.bookings)
		.map((row) => row.currency)
}

const shiftDay = (day: string, by: number) =>
	new Date(Date.parse(day) + by * DAY_MS).toISOString().slice(0, 10)

function daysBetween(first: string, last: string): string[] {
	const days: string[] = []
	for (let day = first; day <= last; day = shiftDay(day, 1)) days.push(day)
	return days
}

const netOf = (row: DailyRevenue) => row.collected - row.refunded

function runningTotal(values: number[]): number[] {
	let total = 0
	return values.map((value) => (total += value))
}

/** Sums neighbouring values so a long range never draws more than `limit` bars. */
export function groupIntoBars(values: number[], limit = MAX_BARS): number[] {
	const size = Math.ceil(values.length / limit)
	if (size <= 1) return values
	return Array.from({ length: Math.ceil(values.length / size) }, (_, index) =>
		values.slice(index * size, (index + 1) * size).reduce((sum, value) => sum + value, 0),
	)
}

/** Totals and a value per day for the period ending `today` (YYYY-MM-DD), gaps filled with 0. */
export function periodStats(
	summary: TransactionSummary,
	currency: string,
	period: Period,
	today: string,
): PeriodStats {
	const byDay = new Map(
		summary.daily.filter((row) => row.currency === currency).map((row) => [row.date, row]),
	)
	const length = PERIOD_DAYS[period]
	const first = length ? shiftDay(today, 1 - length) : ([...byDay.keys()][0] ?? today)
	const days = daysBetween(first, today)
	const sum = (range: string[], pick: (row: DailyRevenue) => number) =>
		range.reduce(
			(total, day) => total + (byDay.has(day) ? pick(byDay.get(day) as DailyRevenue) : 0),
			0,
		)
	const previous = length ? daysBetween(shiftDay(first, -length), shiftDay(first, -1)) : null
	const bookings = sum(days, (row) => row.bookings)
	return {
		net: sum(days, netOf),
		refunded: sum(days, (row) => row.refunded),
		bookings,
		averageOrder: bookings ? sum(days, (row) => row.collected) / bookings : 0,
		previousNet: previous && sum(previous, netOf),
		previousBookings: previous && sum(previous, (row) => row.bookings),
		netRunning: runningTotal(
			days.map((day) => (byDay.has(day) ? netOf(byDay.get(day) as DailyRevenue) : 0)),
		),
		bookingBars: groupIntoBars(days.map((day) => byDay.get(day)?.bookings ?? 0)),
	}
}

/** Percent change, or null when there is nothing to compare against. */
export const percentChange = (current: number, previous: number | null) =>
	previous ? Math.round(((current - previous) / previous) * 1000) / 10 : null

export function pendingFor(summary: TransactionSummary, currency: string) {
	return (
		summary.pending_verification.find((row) => row.currency === currency && row.bookings) ?? null
	)
}

export function summaryFootnote(summary: TransactionSummary, currency: string, money: Money) {
	const row = summary.currencies.find((total) => total.currency === currency)
	if (!row) return ""
	return `All time: ${money(row.tax, currency)} tax · ${money(row.discounts, currency)} discounts`
}

/** Each payment method's slice of the currency's paid amount, largest first. */
export function paymentMethodShares(summary: TransactionSummary, currency: string): MethodShare[] {
	const rows = summary.by_payment_method.filter(
		(row) => row.currency === currency && row.amount > 0,
	)
	const total = rows.reduce((sum, row) => sum + row.amount, 0)
	return rows
		.toSorted((first, second) => second.amount - first.amount)
		.map((row) => ({
			method: row.payment_method || "Other",
			amount: row.amount,
			bookings: row.bookings,
			percent: (row.amount / total) * 100,
		}))
}
