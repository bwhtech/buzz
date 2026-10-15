<script setup lang="ts">
import { ErrorMessage, Skeleton, dayjsLocal, toast } from "frappe-ui"
import { computed, ref, watch } from "vue"

import CommentComposer from "@/components/dashboard/comments/CommentComposer.vue"
import DocumentActivity from "@/components/dashboard/comments/DocumentActivity.vue"
import { useDocumentActivity } from "@/composables/useDocumentActivity"
import type { ProposalListItem, ProposalSpeaker, TalkProposal } from "@/types"
import { speakerName } from "@/utils/speakerByline"

import ProposalProperties from "./ProposalProperties.vue"

const props = defineProps<{
	proposal: ProposalListItem
	doc: TalkProposal | null | undefined
	loading: boolean
	speakers: ProposalSpeaker[]
}>()

// The drawer keys this by proposal, so the feed always belongs to one proposal.
const feed = useDocumentActivity("Talk Proposal", () => props.proposal.name)

// A status change is a line in the feed.
watch(
	() => props.proposal.status,
	() => feed.reload(),
)

const fields = computed(() => [
	{
		label: "Submitted",
		value: dayjsLocal(props.proposal.creation).format("D MMM YYYY"),
		icon: "lucide-calendar",
	},
	{ label: "Phone", value: props.doc?.phone || "—", icon: "lucide-phone" },
	...(props.doc?.additional_fields || [])
		.filter((field) => field.value)
		.map((field) => ({
			label: field.label || "",
			value: String(field.value),
			icon: "lucide-text",
		})),
])

const recipients = computed(() =>
	props.speakers.map((speaker) => ({ name: speakerName(speaker), email: speaker.email })),
)
const names = computed(() =>
	Object.fromEntries(recipients.value.map((person) => [person.email, person.name])),
)
const noteCount = computed(
	() =>
		(feed.activity.data ?? []).filter((entry) => entry.kind === "comment" || entry.kind === "email")
			.length,
)

const draft = ref("")

function post(content: string, toSpeakers: boolean) {
	feed.add(content, toSpeakers).then(
		() => {
			draft.value = ""
			if (toSpeakers)
				toast.success(`Emailed to ${recipients.value.map((person) => person.name).join(" and ")}`)
		},
		() => {},
	)
}
</script>

<template>
	<div class="flex min-h-0 flex-1 flex-col">
		<div class="flex-1 space-y-8 overflow-y-auto overscroll-contain px-6 pt-2 pb-6">
			<ProposalProperties :speakers="speakers" :fields="fields" />

			<section class="space-y-2">
				<h3 class="text-lg font-semibold text-ink-gray-9">Description</h3>
				<!-- Only the document carries the description, so it arrives a beat later. -->
				<Skeleton v-if="loading" class="h-16 w-full rounded-4" />
				<!-- Description is a Text Editor field, so it arrives as sanitized HTML. -->
				<div
					v-else-if="doc?.description"
					class="description prose prose-sm max-w-none text-base leading-[1.6] text-ink-gray-7"
					v-html="doc.description"
				/>
				<p v-else class="text-base text-ink-gray-5">No description was submitted.</p>
			</section>

			<section class="space-y-4">
				<h3 class="flex items-baseline gap-2 text-lg font-semibold text-ink-gray-9">
					Activity
					<span v-if="noteCount" class="text-sm font-normal text-ink-gray-4 tabular-nums">{{
						noteCount
					}}</span>
				</h3>
				<DocumentActivity :feed="feed" :names="names" created-label="submitted this proposal" />
			</section>
		</div>

		<div class="shrink-0 space-y-2 px-6 pt-2 pb-5">
			<ErrorMessage :message="feed.adding.error" />
			<CommentComposer
				v-model="draft"
				:members="feed.members.data || []"
				:recipients="recipients"
				recipients-label="speakers"
				:loading="feed.adding.loading"
				@submit="post"
			/>
		</div>
	</div>
</template>

<style scoped>
.description {
	transition: opacity 200ms cubic-bezier(0.23, 1, 0.32, 1);
}

@starting-style {
	.description {
		opacity: 0;
	}
}
</style>
