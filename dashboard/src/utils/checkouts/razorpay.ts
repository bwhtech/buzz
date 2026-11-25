import type { CheckoutAdapter } from "./index"

declare global {
	interface Window {
		Razorpay: new (options: Record<string, unknown>) => { open(): void }
	}
}

const razorpay: CheckoutAdapter = {
	open: (checkout) =>
		new Promise((resolve) => {
			new window.Razorpay({
				...checkout.options,
				handler: resolve,
				modal: { ...(checkout.options.modal as object), ondismiss: () => resolve(null) },
			}).open()
		}),
}

export default razorpay
