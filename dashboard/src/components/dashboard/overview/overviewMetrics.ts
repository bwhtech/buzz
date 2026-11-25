import type { EventTicketTypes, ProposalTrend, RegistrationTrend } from "@/types"
import { formatCurrency } from "@/utils/currency"

export type MetricKey = "registrations" | "revenue" | "proposals"

export interface Metric {
	key: MetricKey
	label: string
	total: number
	prefix?: string
	delta: number | null
	perDay: { date: string; value: number }[]
	breakdown: { label: string; count: number }[]
	color: string
}

// One hue per metric, the same ones the guests and talks pages already draw in.
const COLOURS: Record<MetricKey, string> = {
	registrations: "oklch(0.55 0.17 252)",
	revenue: "oklch(0.6 0.15 155)",
	proposals: "oklch(0.54 0.245 292.717)",
}

function dayTotals(rows: { date: string; count: number }[]) {
	const totals = new Map<string, number>()
	rows.forEach((row) => totals.set(row.date, (totals.get(row.date) ?? 0) + row.count))
	return [...totals].map(([date, value]) => ({ date, value }))
}

function delta(perDay: { value: number }[]) {
	return perDay.length > 1
		? perDay[perDay.length - 1].value - perDay[perDay.length - 2].value
		: null
}

function registrations(trend: RegistrationTrend): Metric {
	const perDay = dayTotals(trend.per_day)
	return {
		key: "registrations",
		label: "Registrations",
		total: trend.total,
		delta: delta(perDay),
		perDay,
		breakdown: trend.by_ticket_type.map((row) => ({
			label: row.ticket_type || "General",
			count: row.count,
		})),
		color: COLOURS.registrations,
	}
}

function proposals(trend: ProposalTrend): Metric {
	const perDay = dayTotals(trend.per_day)
	return {
		key: "proposals",
		label: "Talk proposals",
		total: trend.total,
		delta: delta(perDay),
		perDay,
		breakdown: trend.by_status.map((row) => ({ label: row.status, count: row.count })),
		color: COLOURS.proposals,
	}
}

// Revenue has no daily series; the card shows the net of the event's main currency.
function revenue(ticketing: EventTicketTypes): Metric | null {
	const main = ticketing.revenue.toSorted((a, b) => b.collected - a.collected)[0]
	if (!main) return null
	const symbol = formatCurrency(0, main.currency, "en-US", { maximumFractionDigits: 0 })
	return {
		key: "revenue",
		label: "Revenue",
		total: main.collected - main.refunded,
		prefix: symbol.replace(/[\d.,\s]/g, ""),
		delta: null,
		perDay: [],
		breakdown: [],
		color: COLOURS.revenue,
	}
}

/** The metrics with numbers in them; one still at zero is left out. */
export function buildMetrics(
	registrationTrend: RegistrationTrend | null | undefined,
	proposalTrend: ProposalTrend | null | undefined,
	ticketing: EventTicketTypes | null | undefined,
): Metric[] {
	const metrics = [
		registrationTrend && registrations(registrationTrend),
		ticketing && revenue(ticketing),
		proposalTrend && proposals(proposalTrend),
	]
	return metrics.filter((metric): metric is Metric => Boolean(metric && metric.total > 0))
}
