import { useCall } from "frappe-ui"

import type { ActivityEntry, TeamMember } from "@/types"

type Reference = { reference_doctype: string; reference_name: string }

// Uncached: a team's notes must not outlive a logout in IndexedDB.
export function useActivity(reference: () => Reference) {
	return useCall<ActivityEntry[], Reference>({
		url: "/api/v2/method/buzz.api.comments.get_activity",
		params: reference,
	})
}

export function useMentionMembers(reference: () => Reference) {
	return useCall<TeamMember[], Reference>({
		url: "/api/v2/method/buzz.api.comments.get_mention_members",
		params: reference,
	})
}

export type EmailCopies = { cc: string[]; bcc: string[] }

export function useEmailSender(reference: () => Reference) {
	return useCall<string | null, Reference>({
		url: "/api/v2/method/buzz.api.comments.get_email_sender",
		params: reference,
	})
}

export function useSubscription(reference: () => Reference) {
	return useCall<boolean, Reference>({
		url: "/api/v2/method/buzz.api.comments.get_subscription",
		params: reference,
	})
}

export function useSetSubscription() {
	return useCall<null, Reference & { subscribed: boolean }>({
		url: "/api/v2/method/buzz.api.comments.set_subscription",
		method: "POST",
		immediate: false,
	})
}

export function useAddComment() {
	return useCall<
		string,
		Reference & { content: string; email_recipients: boolean } & Partial<EmailCopies>
	>({
		url: "/api/v2/method/buzz.api.comments.add_comment",
		method: "POST",
		immediate: false,
	})
}

// Frappe's own endpoint: it lets only the author edit.
export function useUpdateComment() {
	return useCall<null, { name: string; content: string }>({
		url: "/api/v2/method/frappe.desk.form.utils.update_comment",
		method: "POST",
		immediate: false,
	})
}

export function useDeleteComment() {
	return useCall<null, { name: string }>({
		url: "/api/v2/method/buzz.api.comments.delete_comment",
		method: "POST",
		immediate: false,
	})
}
