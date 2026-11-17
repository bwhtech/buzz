// Opens a gateway's own checkout in the page. bwh_payments says which SDK and script to load;
// each SDK has an adapter here that maps its callbacks onto CheckoutAdapter.

export interface InlineCheckout {
	request: string
	sdk: string
	script_url: string
	options: Record<string, unknown>
	redirect_to?: string | null
}

// The gateway's signed answer, posted back to bwh_payments to confirm the payment.
export type InlinePaymentResponse = Record<string, string>

export interface CheckoutAdapter {
	/** Resolves with the gateway's response once paid, or null when the buyer closes the checkout. */
	open(checkout: InlineCheckout): Promise<InlinePaymentResponse | null>
}

// Keep in step with INLINE_CHECKOUT_SDKS in buzz/payments.py.
const adapters: Record<string, () => Promise<{ default: CheckoutAdapter }>> = {
	razorpay: () => import("./razorpay"),
}

const loadedScripts = new Map<string, Promise<void>>()

function loadScript(src: string): Promise<void> {
	if (!loadedScripts.has(src)) {
		const loading = new Promise<void>((resolve, reject) => {
			const script = document.createElement("script")
			script.src = src
			script.addEventListener("load", () => resolve())
			script.addEventListener("error", () => reject(new Error(`Could not load ${src}`)))
			document.head.append(script)
		})
		// A failed load is retried on the next click.
		loading.catch(() => loadedScripts.delete(src))
		loadedScripts.set(src, loading)
	}
	return loadedScripts.get(src) as Promise<void>
}

export async function openInlineCheckout(
	checkout: InlineCheckout,
): Promise<InlinePaymentResponse | null> {
	const loadAdapter = adapters[checkout.sdk]
	if (!loadAdapter) throw new Error(`No checkout adapter for ${checkout.sdk}`)
	const [{ default: adapter }] = await Promise.all([loadAdapter(), loadScript(checkout.script_url)])
	return adapter.open(checkout)
}
