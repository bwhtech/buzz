export type AddEventForm = "existing" | "external"

/** The three ways onto a community calendar: an organizer adds, anyone else submits for review. */
export function addEventOptions(canReview: boolean) {
	return [
		{ type: "create", label: __("Create New"), icon: "lucide-calendar-plus" },
		{
			type: "existing",
			label: canReview ? __("Add Existing from Buzz") : __("Submit Existing from Buzz"),
			icon: "lucide-calendar-heart",
		},
		{
			type: "external",
			label: canReview ? __("Add External") : __("Submit External"),
			// The dialog has room to say what it is about.
			dialogTitle: canReview ? __("Add External Event") : __("Submit External Event"),
			icon: "lucide-link",
		},
	] as const
}

const CREATE_EVENT_PATH = "/b/manage/team/events/new"

/** The create page, told to send the organiser back to the page they are on. */
export function createEventUrl(): string {
	const redirectTo = encodeURIComponent(window.location.pathname + window.location.search)
	return `${CREATE_EVENT_PATH}?redirect-to=${redirectTo}`
}
