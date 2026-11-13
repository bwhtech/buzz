<script setup lang="ts">
import { ErrorMessage, TabButtons, toast } from "frappe-ui"
import { computed, ref } from "vue"

import CommentComposer from "@/components/dashboard/comments/CommentComposer.vue"
import DocumentActivity from "@/components/dashboard/comments/DocumentActivity.vue"
import { activityFilters, useDocumentActivity } from "@/composables/useDocumentActivity"
import type { EmailAttachmentChoice, EmailAttachmentSource, EmailCopies } from "@/data/comments"
import type { TransactionDetail } from "@/types"
import { bookingStatusTheme } from "@/utils/transactionStatus"

const props = defineProps<{ transaction: TransactionDetail; canAttachInvoice: boolean }>()

// The drawer keys this by booking, so the feed always belongs to one booking.
const feed = useDocumentActivity("Event Booking", () => props.transaction.name)
const activityCount = computed(() => feed.activity.data?.length ?? 0)

const buyer = computed(() => props.transaction.buyer)
const recipients = computed(() =>
	buyer.value.email
		? [{ name: buyer.value.name || buyer.value.email, email: buyer.value.email }]
		: [],
)
const names = computed(() =>
	Object.fromEntries(recipients.value.map((person) => [person.email, person.name])),
)

// What the booking renders as PDFs, so nobody downloads a file only to upload it again.
const attachmentChoices = computed<EmailAttachmentChoice[]>(() => {
	const { name, tickets } = props.transaction
	return [
		...(props.canAttachInvoice
			? [
					{
						key: "invoice",
						label: "Invoice",
						fileName: `Invoice-${name}.pdf`,
						icon: "lucide-file-text",
						source: { kind: "invoice" as const },
					},
				]
			: []),
		...(tickets.length > 1
			? [
					{
						key: "tickets",
						label: `All ${tickets.length} tickets`,
						fileName: `Tickets-${name}.pdf`,
						icon: "lucide-tickets",
						source: { kind: "tickets" as const },
					},
				]
			: []),
		...tickets.map((ticket) => ({
			key: ticket.name,
			label: `Ticket · ${ticket.attendee_name || ticket.attendee_email || ticket.name}`,
			fileName: `Ticket-${ticket.name}.pdf`,
			icon: "lucide-ticket",
			source: { kind: "ticket" as const, ticket: ticket.name },
		})),
	]
})

const draft = ref("")

function post(
	content: string,
	toBuyer: boolean,
	copies: EmailCopies,
	attachments: EmailAttachmentSource[],
) {
	feed.add(content, toBuyer, copies, attachments).then(
		() => {
			draft.value = ""
			if (toBuyer) toast.success(`Emailed to ${recipients.value[0]?.name}`)
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
					:change-theme="bookingStatusTheme"
					created-label="booked"
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
