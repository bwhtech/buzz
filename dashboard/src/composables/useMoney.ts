import { createSharedComposable } from "@vueuse/core"

import { useEnabledCurrencies } from "@/data/currencies"
import { formatNumber, getCurrencySymbol } from "@/utils/currency"

/** Formats amounts with each currency's own symbol and Frappe number format. */
export const useMoney = createSharedComposable(() => {
	const currencies = useEnabledCurrencies()
	return (amount: number, currency?: string | null) => {
		const code = currency || "INR"
		const details = currencies.data?.find((row) => row.name === code)
		const symbol = details?.symbol || getCurrencySymbol(code)
		return `${symbol}${formatNumber(amount, details?.number_format)}`
	}
})
