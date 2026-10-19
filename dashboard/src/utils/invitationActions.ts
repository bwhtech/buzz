/** The menu every sent invitation carries, whether to a team or to one event. */
export function invitationActions(handlers: { resend: () => void; retract: () => void }) {
	return [
		{ label: __("Resend"), icon: "lucide-arrow-up-from-line", onClick: handlers.resend },
		{
			label: __("Retract"),
			icon: "lucide-shredder",
			theme: "red" as const,
			onClick: handlers.retract,
		},
	]
}
