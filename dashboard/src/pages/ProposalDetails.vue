<template>
	<div class="mb-6 flex items-center justify-between text-ink-gray-6">
		<BackButton :to="{ name: 'proposals-list' }" :label="__('Back to Proposals')" />

		<Button v-if="canEdit" variant="outline" size="sm" @click="showEditDialog = true">
			{{ isEditingEventTalk ? __("Edit Talk") : __("Edit Proposal") }}
		</Button>
	</div>

	<div class="w-4" v-if="proposal.get.loading">
		<Spinner />
	</div>

	<div v-else-if="proposal.doc">
		<h2 class="text-ink-gray-9 text-lg-semibold mb-6">
			{{ proposal.doc.title }}
			<span class="text-ink-gray-5 font-mono text-sm">(#{{ proposalId }})</span>
		</h2>

		<!-- Accepted Alert -->
		<div
			v-if="proposal.doc.status === 'Accepted'"
			class="mb-6 bg-surface-green-1 border border-outline-green-1 rounded-lg p-6"
		>
			<div class="flex items-center">
				<LucideCheckCircle class="w-6 h-6 text-ink-green-5 mr-3" />
				<div>
					<h3 class="text-ink-green-6 font-semibold">{{ __("Proposal Accepted") }}</h3>
					<p class="text-ink-green-5 text-sm mt-1">
						{{
							__(
								"Congratulations! Your talk proposal has been accepted for the event."
							)
						}}
					</p>
				</div>
			</div>
		</div>

		<!-- Shortlisted Alert -->
		<div
			v-else-if="proposal.doc.status === 'Shortlisted'"
			class="mb-6 bg-surface-blue-1 border border-outline-blue-1 rounded-lg p-6"
		>
			<div class="flex items-center">
				<LucideStar class="w-6 h-6 text-ink-blue-5 mr-3" />
				<div>
					<h3 class="text-ink-blue-6 font-semibold">{{ __("Proposal Shortlisted") }}</h3>
					<p class="text-ink-blue-5 text-sm mt-1">
						{{
							__(
								"Your proposal has been shortlisted and is under final consideration."
							)
						}}
					</p>
				</div>
			</div>
		</div>

		<!-- Review Pending Alert -->
		<div
			v-else-if="proposal.doc.status === 'Review Pending'"
			class="mb-6 bg-surface-orange-1 border border-outline-orange-1 rounded-lg p-6"
		>
			<div class="flex items-center">
				<LucideClock class="w-6 h-6 text-ink-gray-8 mr-3" />
				<div>
					<h3 class="text-ink-gray-8 font-semibold">{{ __("Review Pending") }}</h3>
					<p class="text-ink-gray-7 text-sm mt-1">
						{{
							__(
								"Your proposal has been submitted and is under review. You can still edit it while it's pending."
							)
						}}
					</p>
				</div>
			</div>
		</div>

		<!-- Rejected Alert -->
		<div
			v-else-if="proposal.doc.status === 'Rejected'"
			class="mb-6 bg-surface-red-1 border border-outline-red-1 rounded-lg p-6"
		>
			<div class="flex items-center">
				<LucideXCircle class="w-6 h-6 text-ink-red-5 mr-3" />
				<div>
					<h3 class="text-ink-red-6 font-semibold">{{ __("Proposal Not Selected") }}</h3>
					<p class="text-ink-red-5 text-sm mt-1">
						{{
							__(
								"Unfortunately, your proposal was not selected for this event. Thank you for your submission."
							)
						}}
					</p>
				</div>
			</div>
		</div>

		<div class="space-y-6">
			<!-- Proposal Information -->
			<div class="bg-surface-base border border-outline-gray-1 rounded-lg p-6">
				<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
					<div>
						<label class="block text-sm-medium text-ink-gray-6 mb-1">{{
							__("Title")
						}}</label>
						<p class="text-ink-gray-9">{{ proposal.doc.title }}</p>
					</div>
					<div>
						<label class="block text-sm-medium text-ink-gray-6 mb-1">{{
							__("Event")
						}}</label>
						<p class="text-ink-gray-9">{{ eventTitle }}</p>
					</div>
					<div>
						<label class="block text-sm-medium text-ink-gray-6 mb-1">{{
							__("Status")
						}}</label>
						<Badge
							:theme="getStatusTheme(proposal.doc.status)"
							variant="subtle"
							size="md"
						>
							{{ proposal.doc.status }}
						</Badge>
					</div>
					<div>
						<label class="block text-sm-medium text-ink-gray-6 mb-1">{{
							__("Submitted On")
						}}</label>
						<p class="text-ink-gray-9">{{ formatDate(proposal.doc.creation) }}</p>
					</div>
					<div v-if="proposal.doc.phone">
						<label class="block text-sm-medium text-ink-gray-6 mb-1">{{
							__("Phone")
						}}</label>
						<p class="text-ink-gray-9">{{ proposal.doc.phone }}</p>
					</div>
				</div>
			</div>

			<!-- Speakers -->
			<div class="bg-surface-base border border-outline-gray-1 rounded-lg p-6">
				<h3 class="text-ink-gray-8 text-lg-semibold mb-4">{{ __("Speakers") }}</h3>
				<ListView
					v-if="proposal.doc.speakers && proposal.doc.speakers.length > 0"
					:columns="speakerColumns"
					:rows="proposal.doc.speakers"
					row-key="name"
					:options="{ selectable: false }"
				/>
				<p v-else class="text-ink-gray-5 italic">{{ __("No speakers added") }}</p>
			</div>

			<!-- Description -->
			<div class="bg-surface-base border border-outline-gray-1 rounded-lg p-6">
				<h3 class="text-ink-gray-8 text-lg-semibold mb-4">{{ __("Description") }}</h3>
				<div
					v-if="proposal.doc.description"
					class="prose prose-sm max-w-none text-ink-gray-9"
					v-html="proposal.doc.description"
				></div>
				<p v-else class="text-ink-gray-5 italic">{{ __("No description provided") }}</p>
			</div>
		</div>
	</div>

	<div v-else-if="proposal.get.error" class="text-center py-8">
		<div class="text-ink-red-6 text-lg mb-2">{{ __("Error loading proposal details") }}</div>
		<div class="text-ink-gray-4 text-sm">{{ proposal.get.error }}</div>
	</div>

	<!-- Edit Dialog -->
	<ProposalEditDialog
		v-if="proposal.doc"
		v-model:open="showEditDialog"
		:proposal-id="proposalId"
		:event-talk-id="isEditingEventTalk ? eventTalk.name : null"
		:initial-data="{
			title: isEditingEventTalk ? eventTalk.title : proposal.doc.title,
			description: isEditingEventTalk ? eventTalk.description : proposal.doc.description,
			phone: proposal.doc.phone,
		}"
		@updated="onProposalUpdated"
	/>
</template>

<script setup lang="ts">
import ProposalEditDialog from "@/components/ProposalEditDialog.vue";
import BackButton from "@/components/common/BackButton.vue";
import { useProposalStatuses } from "@/composables/useProposalStatuses";
import {
	Badge,
	Button,
	ListView,
	Spinner,
	createDocumentResource,
	createResource,
	dayjsLocal,
} from "frappe-ui";
import { computed, ref, watch } from "vue";
import LucideCheckCircle from "~icons/lucide/check-circle";
import LucideClock from "~icons/lucide/clock";
import LucideStar from "~icons/lucide/star";
import LucideXCircle from "~icons/lucide/x-circle";

const props = defineProps({
	proposalId: {
		type: String,
		required: true,
	},
});

const showEditDialog = ref(false);

const proposal = createDocumentResource({
	doctype: "Talk Proposal",
	name: props.proposalId,
	auto: true,
});

// Fetch event details including title and allow_editing_talks_after_acceptance
const eventResource = createResource({
	url: "frappe.client.get_value",
	makeParams() {
		return {
			doctype: "Buzz Event",
			filters: { name: proposal.doc?.event },
			fieldname: ["title", "allow_editing_talks_after_acceptance"],
		};
	},
});

// Fetch Event Talk record if proposal is accepted
const eventTalkResource = createResource({
	url: "frappe.client.get_value",
	makeParams() {
		return {
			doctype: "Event Talk",
			filters: { proposal: props.proposalId },
			fieldname: ["name", "title", "description"],
		};
	},
});

watch(
	() => proposal.doc?.event,
	(eventId) => {
		if (eventId) {
			eventResource.fetch();
		}
	},
	{ immediate: true }
);

watch(
	() => proposal.doc?.status,
	(status) => {
		if (status === "Accepted") {
			eventTalkResource.fetch();
		}
	},
	{ immediate: true }
);

const eventTitle = computed(() => eventResource.data?.title || proposal.doc?.event);
const allowEditingAfterAcceptance = computed(
	() => eventResource.data?.allow_editing_talks_after_acceptance
);
const eventTalk = computed(() => eventTalkResource.data);

const speakerColumns = [
	{ label: __("First Name"), key: "first_name" },
	{ label: __("Last Name"), key: "last_name" },
	{ label: __("Email"), key: "email" },
];

// Check if user can edit
// - Always allowed when status is "Review Pending" (edits Talk Proposal)
// - Allowed when status is "Accepted" AND event has allow_editing_talks_after_acceptance enabled (edits Event Talk)
const canEdit = computed(() => {
	if (proposal.doc?.status === "Review Pending") {
		return true;
	}
	if (
		proposal.doc?.status === "Accepted" &&
		allowEditingAfterAcceptance.value &&
		eventTalk.value
	) {
		return true;
	}
	return false;
});

// Determine if we're editing the Event Talk (after acceptance) or the Talk Proposal
const isEditingEventTalk = computed(() => {
	return (
		proposal.doc?.status === "Accepted" && allowEditingAfterAcceptance.value && eventTalk.value
	);
});

const { getStatusTheme } = useProposalStatuses();

const formatDate = (dateString: string) => {
	return dayjsLocal(dateString).format("MMM DD, YYYY");
};

const onProposalUpdated = () => {
	proposal.reload();
	if (proposal.doc?.status === "Accepted") {
		eventTalkResource.fetch();
	}
};
</script>
