import { computed, onBeforeUnmount, ref } from "vue"

import {
	useActivity,
	useAddComment,
	type EmailCopies,
	useDeleteComment,
	useEmailSender,
	useMentionMembers,
	useUpdateComment,
} from "@/data/comments"
import { useSocket } from "@/socket"
import type { ActivityEntry } from "@/types"

type ActivityUpdate = { reference_doctype: string; reference_name: string }

const ignore = () => {}

export type ActivityFilter = "all" | "email" | "comment" | "update"

export const activityFilters: { label: string; value: ActivityFilter }[] = [
	{ label: "All", value: "all" },
	{ label: "Emails", value: "email" },
	{ label: "Notes", value: "comment" },
	{ label: "Updates", value: "update" },
]

const filterKinds: Record<Exclude<ActivityFilter, "all">, ActivityEntry["kind"][]> = {
	email: ["email"],
	comment: ["comment"],
	update: ["change", "created"],
}

/**
 * A record's activity feed and the calls that change it, shared by the timeline and the
 * composer pinned below it. Failures surface through each call's `error`.
 */
export function useDocumentActivity(doctype: string, name: () => string) {
	const reference = () => ({ reference_doctype: doctype, reference_name: name() })

	const activity = useActivity(reference)
	const members = useMentionMembers(reference)
	const sender = useEmailSender(reference)
	const adding = useAddComment()
	const updating = useUpdateComment()
	const deleting = useDeleteComment()

	const noteCount = computed(
		() =>
			(activity.data ?? []).filter((entry) => entry.kind === "comment" || entry.kind === "email")
				.length,
	)

	const filter = ref<ActivityFilter>("all")
	const entries = computed(() => {
		const all = activity.data ?? []
		const value = filter.value
		return value === "all" ? all : all.filter((entry) => filterKinds[value].includes(entry.kind))
	})

	const reload = () => activity.reload()

	const add = (content: string, emailRecipients: boolean, copies?: EmailCopies) =>
		adding
			.submit({ ...reference(), content, email_recipients: emailRecipients, ...copies })
			.then(() => {
				// What was just posted must be in view, whatever the filter hid.
				filter.value = "all"
				return reload()
			})
	const update = (comment: string, content: string) =>
		updating.submit({ name: comment, content }).then(reload, ignore)
	const remove = (comment: string) => deleting.submit({ name: comment }).then(reload, ignore)

	// The server sends this to team members only, without the note itself.
	const socket = useSocket()
	const onUpdate = (message: ActivityUpdate) => {
		if (message.reference_doctype === doctype && message.reference_name === name()) reload()
	}
	socket?.on("buzz_comment_update", onUpdate)
	onBeforeUnmount(() => socket?.off("buzz_comment_update", onUpdate))

	return {
		activity,
		members,
		sender,
		noteCount,
		filter,
		entries,
		adding,
		updating,
		deleting,
		add,
		update,
		remove,
		reload,
	}
}
