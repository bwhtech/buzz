import { useCall } from "frappe-ui"

import type { CurrencyItem } from "@/types"

// Site-wide and the same for every user, so it is safe to persist.
export function useEnabledCurrencies() {
	return useCall<CurrencyItem[]>({
		url: "/api/v2/method/buzz.api.payments.get_enabled_currencies",
		cacheKey: "enabled-currencies",
	})
}
