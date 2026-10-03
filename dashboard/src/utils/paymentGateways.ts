const LOGO_DIRECTORY = "/assets/buzz/images/payment_gateways"

// Brand marks are drawn for one background, so each gateway ships a version per theme.
export interface PaymentGatewayLogoFiles {
	light: string
	dark: string
}

const LOGOS: Record<string, PaymentGatewayLogoFiles> = {
	Razorpay: {
		light: `${LOGO_DIRECTORY}/razorpay.svg`,
		dark: `${LOGO_DIRECTORY}/razorpay-dark.svg`,
	},
}

// Gateways with per-account settings are named "<Provider>-<account>", e.g. "Stripe-Main".
export const paymentGatewayLogo = (gateway: string): PaymentGatewayLogoFiles | undefined =>
	LOGOS[gateway.split("-")[0]]
