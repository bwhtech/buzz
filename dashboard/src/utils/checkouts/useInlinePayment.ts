import { toast, useCall } from "frappe-ui"

import { serverErrorMessage } from "@/utils/serverError"

import { type InlineCheckout, type InlinePaymentResponse, openInlineCheckout } from "./index"

/** Takes the payment in the page, confirms it, then leaves for the checkout's `redirect_to`. */
export function useInlinePayment() {
	const confirmPayment = useCall<string, { request: string; response: InlinePaymentResponse }>({
		url: "/api/v2/method/bwh_payments.bwh_payments.checkout.confirm_inline_payment",
		method: "POST",
		immediate: false,
	})

	/** False when the buyer stays on the page: they closed the checkout or it failed. */
	async function pay(checkout: InlineCheckout): Promise<boolean> {
		const response = await openInlineCheckout(checkout).catch(() => {
			toast.error(__("Could not open the payment window"))
			return null
		})
		if (!response) return false

		// Once paid the buyer never returns to the form, where paying again would charge twice.
		// A failed confirm is settled by the webhook; the next page shows the booking's state.
		const redirectTo = await confirmPayment
			.submit({ request: checkout.request, response })
			.catch(() => null)
		if (!redirectTo && !checkout.redirect_to) {
			toast.error(serverErrorMessage(confirmPayment.error) || __("Could not confirm the payment"))
		}
		window.location.assign(redirectTo || checkout.redirect_to || window.location.href)
		return true
	}

	return { pay }
}
