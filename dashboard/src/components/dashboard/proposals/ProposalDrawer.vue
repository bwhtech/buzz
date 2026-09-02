<script setup lang="ts">
import { useClipboard } from "@vueuse/core"
import {
	Alert,
	Avatar,
	Badge,
	Button,
	Dialog,
	Divider,
	Skeleton,
	dayjs,
	dayjsLocal,
	toast,
} from "frappe-ui"
import { computed, ref } from "vue"

import {
	Drawer,
	DrawerClose,
	DrawerContent,
	DrawerDescription,
	DrawerTitle,
} from "@/components/common/drawer"
import EventHoverCard from "@/components/dashboard/events/EventHoverCard.vue"
import AddSpeakerDialog from "@/components/dashboard/proposals/AddSpeakerDialog.vue"
import { useProposalStatuses } from "@/composables/useProposalStatuses"
import { useProposal } from "@/data/proposals"
import { session } from "@/data/session"
import { userResource } from "@/data/user"
import type { ProposalListItem, ProposalSpeaker, TalkProposal } from "@/types"
import { proposalActions } from "@/utils/proposalActions"
import { isReader, speakerName } from "@/utils/speakerByline"

const props = defineProps<{ proposal: ProposalListItem | null }>()

const open = defineModel<boolean>("open", { required: true })

const emit = defineEmits<{ changed: [] }>()

const { getStatusTheme, getStatusMessage } = useProposalStatuses()

const statusMessage = computed(() => getStatusMessage(props.proposal?.status || ""))

// The card's row fills the drawer at once; the document carries what the list call
// leaves out — the description and the event's own form answers.
const proposalDoc = useProposal(() => props.proposal?.name)

// Plain dayjs: a timezone shift would move a date-only value a day back.
const actions = computed(() =>
	props.proposal
		? proposalActions(props.proposal, dayjs().format("YYYY-MM-DD"))
		: { canEdit: false, canWithdraw: false, canManageSpeakers: false },
)

// The row's speakers show at once; the document's replace them, so a speaker added here
// appears without waiting on the list to refetch. Its rows are full child documents —
// the drawer only reads the three fields the byline and the list share.
const speakers = computed<ProposalSpeaker[]>(() =>
	(proposalDoc.doc?.speakers ?? props.proposal?.speakers ?? []).map((speaker) => ({
		first_name: speaker.first_name,
		last_name: speaker.last_name ?? null,
		email: speaker.email,
	})),
)

const confirmingWithdrawal = ref(false)
// The speaker the confirmation is asking about, and the row whose button spins.
const removing = ref<ProposalSpeaker | null>(null)
const addingSpeaker = ref(false)

// A speaker the drawer adds is three fields, not a saved child document, so the payload
// takes the shape the API accepts rather than the generated one.
type ProposalUpdate = Partial<Omit<TalkProposal, "speakers">> & { speakers?: ProposalSpeaker[] }

async function write(fields: ProposalUpdate, done: string) {
	try {
		await proposalDoc.setValue.submit(fields as Partial<TalkProposal>)
		toast.success(done)
		emit("changed")
	} catch {
		toast.error("Could not save your change")
	}
}

async function withdraw() {
	await write({ status: "Withdrawn" }, "Proposal withdrawn")
	confirmingWithdrawal.value = false
}

async function addSpeaker(speaker: ProposalSpeaker) {
	await write({ speakers: [...speakers.value, speaker] }, "Speaker added")
	addingSpeaker.value = false
}

async function removeSpeaker() {
	const speaker = removing.value
	// Removing yourself would take away your own access to the proposal.
	if (!speaker || isReader(speaker, reader.value)) return
	const rest = speakers.value.filter((listed) => listed.email !== speaker.email)
	await write({ speakers: rest }, "Speaker removed")
	removing.value = null
}

const reader = computed(() => userResource.data?.email || session.user)

// legacy: the async clipboard API is refused outside a secure context, and on an
// http:// host in development that is every time.
const { copy } = useClipboard({ legacy: true })

async function copyId(id: string) {
	try {
		await copy(id)
		toast.success("Copied to clipboard")
	} catch {
		toast.error("Could not copy to clipboard")
	}
}

// One theme per speaker, stable across renders so a face keeps its colour.
const AVATAR_THEMES = ["blue", "green", "amber", "red", "violet"] as const
const avatarTheme = (speaker: ProposalSpeaker) => {
	const seed = [...speaker.email].reduce((total, character) => total + character.charCodeAt(0), 0)
	return AVATAR_THEMES[seed % AVATAR_THEMES.length]
}

// Plain dayjs: start_date is date-only, and a timezone shift moves it a day back.
const eventDate = computed(() =>
	props.proposal?.start_date ? dayjs(props.proposal.start_date).format("D MMMM YYYY") : "",
)

// creation and modified are full timestamps in the site's timezone, so these convert.
const submittedOn = computed(() =>
	props.proposal ? dayjsLocal(props.proposal.creation).format("D MMM YYYY") : "",
)
const lastUpdated = computed(() =>
	props.proposal ? dayjsLocal(props.proposal.modified).format("D MMM'YY, h:mm A") : "",
)

// The form's own questions fill the grid; Submitted on always holds the last cell.
const fields = computed(() => [
	...(proposalDoc.doc?.additional_fields || [])
		.filter((field) => field.value)
		.slice(0, 3)
		.map((field) => ({ label: field.label, value: field.value })),
	{ label: "Submitted on", value: submittedOn.value },
])
</script>

<template>
	<Drawer v-model:open="open" swipe-direction="right">
		<DrawerContent size="lg">
			<template v-if="proposal">
				<div class="flex items-center gap-2 p-4 pb-0">
					<button
						type="button"
						class="cursor-copy font-mono text-sm tracking-wider uppercase text-ink-gray-5"
						:aria-label="`Copy proposal id ${proposal.name}`"
						@click="copyId(proposal.name)"
					>
						#{{ proposal.name }}
					</button>
					<DrawerClose as-child>
						<Button class="ml-auto" variant="ghost" size="sm" icon="lucide-x" aria-label="Close" />
					</DrawerClose>
				</div>

				<div class="flex flex-1 flex-col space-y-4 overflow-y-auto p-4">
					<!-- The status leads: it is the answer the submitter opened the drawer for. -->
					<Alert
						:theme="getStatusTheme(proposal.status)"
						:title="proposal.status"
						:description="statusMessage"
					/>

					<div class="space-y-2">
						<DrawerTitle class="text-4xl font-semibold text-pretty text-ink-gray-9">
							{{ proposal.title }}
						</DrawerTitle>
						<DrawerDescription class="text-base text-ink-gray-6">
							<EventHoverCard
								class="text-ink-gray-6"
								:event="proposal.event"
								:title="proposal.event_title || 'Deleted event'"
								:start-date="proposal.start_date"
								:start-time="proposal.start_time"
								:venue="proposal.venue"
								:banner-image="proposal.banner_image"
							/>
							<template v-if="eventDate"> · {{ eventDate }}</template>
						</DrawerDescription>
					</div>

					<div class="grid grid-cols-2 gap-x-5 gap-y-3">
						<div v-for="field in fields" :key="field.label" class="space-y-0.5">
							<p class="text-base text-ink-gray-5">{{ field.label }}</p>
							<p class="text-base font-medium text-ink-gray-8">{{ field.value }}</p>
						</div>
					</div>

					<Divider flex-item />

					<div v-if="speakers.length" class="space-y-2">
						<div class="flex items-center justify-between gap-2">
							<h3 class="text-lg font-semibold text-ink-gray-8">Speakers</h3>
							<Button
								v-if="actions.canManageSpeakers"
								variant="ghost"
								size="sm"
								label="Add speaker"
								icon-left="lucide-plus"
								@click="addingSpeaker = true"
							/>
						</div>
						<!-- Headerless: the three columns are self-evident, and a header would
						     read as a form the reader has to fill. -->
						<table class="w-full table-fixed">
							<tbody>
								<tr v-for="speaker in speakers" :key="speaker.email" class="group">
									<td
										class="w-[calc(50%-1.5rem)] py-1 pl-1 rounded-l-4 transition-colors group-hover:bg-surface-gray-1"
									>
										<span class="flex min-w-0 items-center gap-2">
											<Avatar
												size="md"
												:label="speakerName(speaker)"
												:theme="avatarTheme(speaker)"
											/>
											<span class="min-w-0 truncate text-base text-ink-gray-8">
												{{ speakerName(speaker) }}
											</span>
										</span>
									</td>
									<td
										class="w-[calc(50%-1.5rem)] min-w-0 truncate py-1 text-right text-base text-ink-gray-5 transition-colors group-hover:bg-surface-gray-1"
									>
										{{ speaker.email }}
									</td>
									<td
										class="w-12 py-1 pr-1 rounded-r-4 text-right transition-colors group-hover:bg-surface-gray-1"
									>
										<Badge v-if="isReader(speaker, reader)" theme="gray" label="You" />
										<!-- Opacity, not v-if: the button stays in the tab order for anyone
										     who never hovers. -->
										<Button
											v-else-if="actions.canManageSpeakers"
											class="speaker-remove opacity-0 transition-opacity duration-100 ease-out focus-visible:opacity-100 group-hover:opacity-100"
											variant="ghost"
											size="sm"
											icon="lucide-x"
											:loading="removing?.email === speaker.email && proposalDoc.setValue.loading"
											:aria-label="`Remove ${speakerName(speaker)}`"
											@click="removing = speaker"
										/>
									</td>
								</tr>
							</tbody>
						</table>
					</div>

					<div class="space-y-2">
						<h3 class="text-lg font-semibold text-ink-gray-8">Description</h3>
						<!-- Only the document carries the description, so it arrives a beat later. -->
						<Skeleton v-if="proposalDoc.loading" class="h-16 w-full rounded-4" />
						<!-- Description is a Text Editor field, so it arrives as sanitized HTML. -->
						<div
							v-else-if="proposalDoc.doc?.description"
							class="prose prose-sm max-w-none text-base leading-[1.6] text-ink-gray-7"
							v-html="proposalDoc.doc.description"
						/>
						<p v-else class="text-base leading-[1.6] text-ink-gray-7">
							No description was submitted.
						</p>
					</div>
				</div>

				<AddSpeakerDialog
					v-model:open="addingSpeaker"
					:speakers="speakers"
					:saving="proposalDoc.setValue.loading"
					@add="addSpeaker"
				/>

				<Dialog
					:open="Boolean(removing)"
					:title="`Remove ${removing ? speakerName(removing) : ''}?`"
					message="They lose access to the proposal, and the panel stops seeing them on it."
					size="md"
					@update:open="removing = null"
				>
					<template #actions>
						<div class="flex justify-end gap-2">
							<Button label="Keep them" @click="removing = null" />
							<Button
								variant="solid"
								theme="red"
								label="Remove speaker"
								:loading="proposalDoc.setValue.loading"
								@click="removeSpeaker"
							/>
						</div>
					</template>
				</Dialog>

				<Dialog
					v-model:open="confirmingWithdrawal"
					title="Withdraw this proposal?"
					message="The review panel stops considering it, and you cannot put it back yourself."
					size="md"
				>
					<template #actions>
						<div class="flex justify-end gap-2">
							<Button label="Keep it" @click="confirmingWithdrawal = false" />
							<Button
								variant="solid"
								theme="red"
								label="Withdraw"
								:loading="proposalDoc.setValue.loading"
								@click="withdraw"
							/>
						</div>
					</template>
				</Dialog>
			</template>

			<template v-if="proposal" #footer>
				<p class="flex items-center gap-1 text-xs text-ink-gray-5">
					<span class="lucide-clock-fading size-3.5 shrink-0" aria-hidden="true" />
					Last updated {{ lastUpdated }}
				</p>
				<Button
					v-if="actions.canWithdraw"
					class="ml-auto"
					variant="ghost"
					theme="red"
					size="md"
					label="Withdraw"
					@click="confirmingWithdrawal = true"
				/>
				<Button
					v-if="actions.canEdit"
					:class="{ 'ml-auto': !actions.canWithdraw }"
					variant="solid"
					size="md"
					label="Edit proposal"
				/>
			</template>
		</DrawerContent>
	</Drawer>
</template>

<style scoped>
/* A touch device never hovers, so the button that hover reveals has to stay put. */
@media (hover: none) {
	.speaker-remove {
		opacity: 1;
	}
}
</style>
