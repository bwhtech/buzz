import { useCall } from "frappe-ui"

import type { PaymentGatewayLogo } from "@/types"

// Site-wide and the same for every user, so it is safe to persist.
export function usePaymentGatewayLogos() {
	return useCall<PaymentGatewayLogo[]>({
		url: "/api/v2/method/buzz.api.payments.get_payment_gateway_logos",
		cacheKey: "payment-gateway-logos",
	})
}
