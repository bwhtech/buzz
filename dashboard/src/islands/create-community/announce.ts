import { toast } from "frappe-ui"

import { ensureToasts } from "../mount"
import { translate } from "../translate"
import type { CreatedNotice } from "./reveal"

// Lands once the page has finished growing in.
const AFTER_REVEAL_MS = 560

// Monochrome over the provider's blue link: the action is the toast's one button.
const ACTION_CLASS =
	"!text-ink-base !bg-surface-gray-8 hover:!bg-surface-gray-7 min-w-[5.5rem] justify-center active:scale-[0.97] transition-transform"

export function announceCreatedCommunity({ name, url }: CreatedNotice) {
	ensureToasts()
	const title = translate("{0} is live", [name])
	const show = (label: string, onClick: (event: MouseEvent) => void) =>
		toast.success(title, {
			id: url,
			duration: 10000,
			classes: { actionButton: ACTION_CLASS },
			action: { label, onClick },
		})

	const copy = (event: MouseEvent) => {
		// Keeps the toast up, to say it worked in place.
		event.preventDefault()
		const settle = (label: string) => show(label, (again) => again.preventDefault())
		navigator.clipboard.writeText(url).then(
			() => settle(translate("Copied")),
			() => settle(translate("Could not copy")),
		)
	}
	setTimeout(() => show(translate("Copy link"), copy), AFTER_REVEAL_MS)
}
