// What each status means for the applicant, and what they can still do about it.
const STATUS_MESSAGES: Record<string, string> = {
	"Approval Pending":
		"The event team is reviewing your enquiry. You will be notified once it is approved for payment.",
	"Payment Pending": "Your enquiry is approved. Complete the payment to confirm your sponsorship.",
	Paid: "Your sponsorship is confirmed. Payment details are in your email.",
	Cancelled: "The event team has cancelled this sponsorship.",
	Withdrawn: "You withdrew this enquiry. It is no longer active.",
}

// Tailwind emits only the icon classes it can see, so no interpolated names.
const STATUS_ICONS: Record<string, string> = {
	"Approval Pending": "lucide-clock",
	"Payment Pending": "lucide-credit-card",
	Paid: "lucide-circle-check",
	Cancelled: "lucide-circle-slash",
	Withdrawn: "lucide-circle-x",
}

const SETTLED_STATUSES = ["Paid", "Cancelled", "Withdrawn"]

export const enquiryStatusMessage = (status: string) => STATUS_MESSAGES[status] || ""

export const enquiryStatusIcon = (status: string) =>
	STATUS_ICONS[status] || "lucide-squircle-dashed"

export function enquiryActions(status: string) {
	return {
		canPay: status === "Payment Pending",
		canWithdraw: !SETTLED_STATUSES.includes(status),
	}
}
