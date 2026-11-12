<script setup lang="ts">
import { ErrorMessage } from "frappe-ui"
import { computed, ref } from "vue"

import CommentComposer from "@/components/dashboard/comments/CommentComposer.vue"
import DocumentActivity from "@/components/dashboard/comments/DocumentActivity.vue"
import { useDocumentActivity } from "@/composables/useDocumentActivity"

const props = defineProps<{
	booking: string
	buyerName: string | null
	buyerEmail: string | null
}>()

const feed = useDocumentActivity("Event Booking", () => props.booking)

const names = computed(() =>
	props.buyerEmail ? { [props.buyerEmail]: props.buyerName || props.buyerEmail } : {},
)

const draft = ref("")

function post(content: string) {
	feed.add(content, false).then(
		() => (draft.value = ""),
		() => {},
	)
}
</script>

<template>
	<!-- Notes are for team members; a ticketing collaborator is refused the feed. -->
	<section v-if="!feed.activity.error" class="space-y-4">
		<h3 class="text-base font-semibold text-ink-gray-8">Activity</h3>
		<DocumentActivity :feed="feed" :names="names" created-label="booked" />
		<ErrorMessage :message="feed.adding.error" />
		<CommentComposer
			v-model="draft"
			:members="feed.members.data || []"
			:loading="feed.adding.loading"
			@submit="post"
		/>
	</section>
</template>
