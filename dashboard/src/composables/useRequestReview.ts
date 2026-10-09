import { toast } from "frappe-ui"
import { ref } from "vue"

import { useReviewAction } from "@/data/communities"
import { serverErrorMessage } from "@/utils/serverError"

/** Approve and reject for a community's pending requests, shared by the list and the drawer. */
export function useRequestReview(onReviewed: () => void) {
	const approval = useReviewAction("approve_request")
	const rejection = useReviewAction("reject_request")
	const approving = ref<string | null>(null)

	// Resolves true when the server took it, so a caller knows to close its dialog or drawer.
	async function run(
		action: typeof approval,
		params: { request: string; note?: string },
		done: string,
	) {
		await action.submit(params)
		// useCall does not reject on a server error; it sets `error`.
		if (action.error) {
			toast.error(serverErrorMessage(action.error))
			return false
		}
		toast.success(done)
		onReviewed()
		return true
	}

	async function approve(request: string) {
		approving.value = request
		const done = await run(approval, { request }, __("Event added to your calendar"))
		approving.value = null
		return done
	}

	function reject(request: string, note: string) {
		return run(rejection, { request, note: note.trim() || undefined }, __("Submission rejected"))
	}

	return { approve, reject, approving, rejection }
}
