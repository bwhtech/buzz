import { createSharedComposable } from "@vueuse/core"
import { useCall } from "frappe-ui"

// Site-wide and the same for every user, so it is safe to persist.
export const usePaymentGatewaysNeedingPhone = createSharedComposable(() =>
	useCall<string[]>({
		url: "/api/v2/method/buzz.api.payments.get_payment_gateways_needing_phone",
		cacheKey: "payment-gateways-needing-phone",
	}),
)
