<script setup lang="ts">
import { ErrorMessage } from "frappe-ui"
import { computed, ref, watch } from "vue"

import CommentComposer from "@/components/dashboard/comments/CommentComposer.vue"
import DocumentActivity from "@/components/dashboard/comments/DocumentActivity.vue"
import { useDocumentActivity } from "@/composables/useDocumentActivity"
import type { RegistrationRequest } from "@/types"
import type { BadgeTheme } from "@/utils/badgeTheme"
import { requesterName } from "@/utils/requestQueue"

const props = defineProps<{ request: RegistrationRequest }>()

// The drawer keys this by request, so the feed always belongs to one booking.
const feed = useDocumentActivity("Event Booking", () => props.request.name)

// A decision is a status change, which is a line in the feed.
watch(
	() => props.request.status,
	() => feed.reload(),
)

const names = computed(() =>
	props.request.buyer_email ? { [props.request.buyer_email]: requesterName(props.request) } : {},
)

const STATUS_THEMES: Record<string, BadgeTheme> = {
	Requested: "amber",
	Waitlisted: "gray",
	"Payment Pending": "blue",
	Confirmed: "green",
	Rejected: "red",
}
const statusTheme = (status: string) => STATUS_THEMES[status] ?? "gray"

const draft = ref("")

function post(content: string) {
	feed.add(content, false).then(
		() => (draft.value = ""),
		() => {},
	)
}
</script>

<template>
	<section class="space-y-4">
		<h3 class="text-base font-semibold text-ink-gray-9">Activity</h3>
		<DocumentActivity
			:feed="feed"
			:names="names"
			:change-theme="statusTheme"
			:created-label="request.request_type === 'Waitlist' ? 'joined the waitlist' : 'asked to join'"
		/>
		<ErrorMessage :message="feed.adding.error" />
		<CommentComposer
			v-model="draft"
			:members="feed.members.data || []"
			:loading="feed.adding.loading"
			@submit="post"
		/>
	</section>
</template>
