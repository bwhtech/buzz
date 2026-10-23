<script setup lang="ts">
import { Badge, ErrorMessage, Skeleton, TabButtons, dayjsLocal, toast } from "frappe-ui"
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

const draft = ref("")

const descriptionView = ref<"formatted" | "original">("formatted")
const showOriginal = computed(() => descriptionView.value === "original")
const canFormat = computed(
	() =>
		!!props.doc?.formatted_description && props.doc.formatted_description !== props.doc.description,
)
const description = computed(() =>
	canFormat.value && !showOriginal.value
		? props.doc?.formatted_description
		: props.doc?.description,
)

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
		<div class="scroll-fade flex-1 space-y-8 overflow-y-auto overscroll-contain px-6 pt-2 pb-6">
			<ProposalProperties :speakers="speakers" :fields="fields" />

			<section class="space-y-2">
				<div class="flex items-center justify-between gap-2">
					<h3 class="text-lg font-semibold text-ink-gray-9">Description</h3>
					<TabButtons
						v-if="canFormat"
						v-model="descriptionView"
						:options="[
							{ label: 'Formatted', value: 'formatted' },
							{ label: 'Original', value: 'original' },
						]"
					/>
				</div>
				<!-- Only the document carries the description, so it arrives a beat later. -->
				<Skeleton v-if="loading" class="h-16 w-full rounded-4" />
				<!-- Description is a Text Editor field, so it arrives as sanitized HTML. -->
				<div
					v-else-if="description"
					class="description prose prose-sm max-w-none text-base leading-[1.6] text-ink-gray-7"
					:class="showOriginal && 'whitespace-pre-line'"
					v-html="description"
				/>
				<p v-else class="text-base text-ink-gray-5">No description was submitted.</p>
			</section>

			<section class="space-y-4">
				<h3 class="flex items-center gap-2 text-lg font-semibold text-ink-gray-9">
					Activity
					<Badge v-if="feed.noteCount.value" :label="String(feed.noteCount.value)" />
				</h3>
				<DocumentActivity :feed="feed" :names="names" created-label="submitted this proposal" />
			</section>
		</div>

		<div class="shrink-0 space-y-2 px-3 pt-2 pb-3">
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
/* The timeline fades into the composer instead of being cut at its edge. The bottom
   fade is as tall as the bottom padding, so the last entry is never faded once scrolled
   to. The top fade grows in with the first 24px of scroll, so nothing fades at rest;
   without scroll-driven animations it simply stays off. */
@property --top-fade {
	syntax: "<length>";
	inherits: false;
	initial-value: 0px;
}

.scroll-fade {
	mask-image: linear-gradient(
		to bottom,
		transparent,
		black var(--top-fade),
		black calc(100% - 1.5rem),
		transparent
	);
	animation: top-fade-in linear both;
	animation-timeline: scroll(self);
	animation-range: 0 1.5rem;
}

@keyframes top-fade-in {
	to {
		--top-fade: 1.5rem;
	}
}

.description {
	transition: opacity 200ms cubic-bezier(0.23, 1, 0.32, 1);
}

@starting-style {
	.description {
		opacity: 0;
	}
}
</style>
