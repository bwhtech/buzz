<script setup lang="ts">
import { ErrorMessage, Skeleton, toast } from "frappe-ui"
import { onBeforeUnmount, ref } from "vue"

import CommentEditor from "@/components/dashboard/comments/CommentEditor.vue"
import CommentItem from "@/components/dashboard/comments/CommentItem.vue"
import {
	useAddComment,
	useComments,
	useDeleteComment,
	useMentionMembers,
	useUpdateComment,
} from "@/data/comments"
import { useSocket } from "@/socket"

const props = defineProps<{ doctype: string; name: string; emailLabel?: string }>()

const reference = () => ({ reference_doctype: props.doctype, reference_name: props.name })

const comments = useComments(reference)
const members = useMentionMembers(reference)
const addComment = useAddComment()
const updateComment = useUpdateComment()
const deleteComment = useDeleteComment()

const draft = ref("")

// Failures show through ErrorMessage below, so a rejected call only skips the reload.
const reload = () => comments.reload()
const shownBelow = () => {}

function add(content: string, emailRecipients: boolean) {
	addComment.submit({ ...reference(), content, email_recipients: emailRecipients }).then(() => {
		draft.value = ""
		if (emailRecipients) toast.success("Comment emailed")
		reload()
	}, shownBelow)
}

function update(name: string, content: string) {
	updateComment.submit({ name, content }).then(reload, shownBelow)
}

function remove(name: string) {
	deleteComment.submit({ name }).then(reload, shownBelow)
}

// The server sends this to team members only, without the comment itself.
const socket = useSocket()
function onCommentUpdate(message: { reference_doctype: string; reference_name: string }) {
	if (message.reference_doctype === props.doctype && message.reference_name === props.name)
		comments.reload()
}
socket?.on("buzz_comment_update", onCommentUpdate)
onBeforeUnmount(() => socket?.off("buzz_comment_update", onCommentUpdate))
</script>

<template>
	<div class="space-y-4">
		<Skeleton v-if="comments.loading && !comments.data" class="h-16 w-full rounded-4" />
		<ErrorMessage :message="comments.error" />
		<p v-if="comments.data && !comments.data.length" class="text-base text-ink-gray-5">
			No comments yet. Notes here are visible to your team only.
		</p>
		<ul v-if="comments.data?.length" class="space-y-4">
			<CommentItem
				v-for="comment in comments.data"
				:key="comment.name"
				:comment="comment"
				:members="members.data || []"
				:saving="updateComment.loading"
				@update="(content) => update(comment.name, content)"
				@delete="remove(comment.name)"
			/>
		</ul>
		<ErrorMessage :message="addComment.error || updateComment.error || deleteComment.error" />
		<CommentEditor
			v-model="draft"
			:members="members.data || []"
			:loading="addComment.loading"
			:email-label="emailLabel"
			@submit="add"
		/>
	</div>
</template>
