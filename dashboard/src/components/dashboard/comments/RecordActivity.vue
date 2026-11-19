<script setup lang="ts">
import { ErrorMessage, TabButtons, toast } from "frappe-ui"
import { computed, ref } from "vue"

import type { Recipient } from "@/components/dashboard/comments/CommentComposer.vue"
import CommentComposer from "@/components/dashboard/comments/CommentComposer.vue"
import DocumentActivity from "@/components/dashboard/comments/DocumentActivity.vue"
import { activityFilters, useDocumentActivity } from "@/composables/useDocumentActivity"
import type { EmailAttachmentChoice, EmailAttachmentSource, EmailCopies } from "@/data/comments"
import type { BadgeTheme } from "@/utils/badgeTheme"

// A drawer's scrolling body: its own content in the slot, then the record's activity,
// with the composer pinned below.
const props = defineProps<{
	doctype: string
	name: string
	recipients: Recipient[]
	createdLabel: string
	attachmentChoices?: EmailAttachmentChoice[]
	changeTheme?: (value: string) => BadgeTheme
}>()

// The drawer keys this by record, so the feed always belongs to one record.
const feed = useDocumentActivity(props.doctype, () => props.name)
const activityCount = computed(() => feed.activity.data?.length ?? 0)
const names = computed(() =>
	Object.fromEntries(props.recipients.map((person) => [person.email, person.name])),
)

const draft = ref("")

function post(
	content: string,
	toRecipients: boolean,
	copies: EmailCopies,
	attachments: EmailAttachmentSource[],
) {
	feed.add(content, toRecipients, copies, attachments).then(
		() => {
			draft.value = ""
			if (toRecipients) toast.success(`Emailed to ${props.recipients[0]?.name}`)
		},
		() => {},
	)
}
</script>

<template>
	<div class="flex min-h-0 flex-1 flex-col">
		<div class="scroll-fade flex-1 space-y-8 overflow-y-auto overscroll-contain px-6 pt-2 pb-16">
			<slot />

			<!-- Notes are for team members; a ticketing collaborator is refused the feed. -->
			<section v-if="!feed.activity.error" class="space-y-4">
				<div class="flex items-center justify-between gap-2">
					<h3 class="flex items-center gap-2 text-lg font-semibold text-ink-gray-9">
						Activity
						<span v-if="activityCount" class="text-base font-normal tabular-nums text-ink-gray-5">
							{{ activityCount }}
						</span>
					</h3>
					<TabButtons v-if="activityCount" v-model="feed.filter.value" :options="activityFilters" />
				</div>
				<DocumentActivity
					:feed="feed"
					:names="names"
					:change-theme="changeTheme"
					:created-label="createdLabel"
				/>
			</section>
		</div>

		<div v-if="!feed.activity.error" class="shrink-0 space-y-2 px-5 pt-3 pb-4">
			<ErrorMessage :message="feed.adding.error" />
			<CommentComposer
				v-model="draft"
				:members="feed.members.data || []"
				:recipients="recipients"
				:sender="feed.sender.data"
				:attachment-choices="attachmentChoices"
				:loading="feed.adding.loading"
				@submit="post"
			/>
		</div>
	</div>
</template>

<style scoped>
/* Same fade as the Talk drawer: the timeline runs under the pinned composer. */
.scroll-fade {
	mask-image: linear-gradient(
		to bottom,
		black calc(100% - 4rem),
		rgb(0 0 0 / 0.7) calc(100% - 2.5rem),
		rgb(0 0 0 / 0.3) calc(100% - 1.25rem),
		transparent
	);
}
</style>
