import type { CurrencySummary, TransactionSummary } from "@/types"

import { formatCurrency } from "./currency.ts"
import { pluralize } from "./pluralize.ts"

export type SummaryCard = { title: string; value: string; caption?: string }

export type CurrencyCards = { currency: string; cards: SummaryCard[]; footnote: string }

const money = (amount: number, currency: string) =>
	formatCurrency(amount, currency, "en-US", { maximumFractionDigits: 0 })

function pendingCard(summary: TransactionSummary, currency: string): SummaryCard[] {
	const pending = summary.pending_verification.find((row) => row.currency === currency)
	if (!pending?.bookings) return []
	return [
		{
			title: "Pending verification",
			value: money(pending.amount, currency),
			caption: pluralize(pending.bookings, "booking"),
		},
	]
}

function primaryCards(row: CurrencySummary): SummaryCard[] {
	const { currency } = row
	return [
		{ title: "Net revenue", value: money(row.net, currency) },
		{ title: "Gross collected", value: money(row.collected, currency) },
		{ title: "Refunded", value: money(row.refunded, currency) },
		{
			title: "Paid bookings",
			value: String(row.bookings),
			caption: `${pluralize(row.tickets, "ticket")} sold`,
		},
		{ title: "Average order value", value: money(row.average_order_value, currency) },
	]
}

/** One set of cards per currency, busiest first: amounts in two currencies are never summed. */
export function transactionSummaryCards(summary: TransactionSummary): CurrencyCards[] {
	return summary.currencies
		.toSorted((first, second) => second.bookings - first.bookings)
		.map((row) => ({
			currency: row.currency,
			cards: [...primaryCards(row), ...pendingCard(summary, row.currency)],
			footnote: `${money(row.tax, row.currency)} tax · ${money(row.discounts, row.currency)} discounts`,
		}))
}
