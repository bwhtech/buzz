<script setup lang="ts">
import { Avatar, Button, Select, Skeleton, dayjsLocal, toast } from "frappe-ui"
import { computed, ref, watch } from "vue"

import {
	Drawer,
	DrawerClose,
	DrawerContent,
	DrawerDescription,
	DrawerTitle,
} from "@/components/common/drawer"
import { useCopyToClipboard } from "@/composables/useCopyToClipboard"
import { useProposalStatuses } from "@/composables/useProposalStatuses"
import { useProposal } from "@/data/proposals"
import type { ProposalListItem, ProposalSpeaker } from "@/types"
import { speakerName } from "@/utils/speakerByline"

const props = defineProps<{ proposal: ProposalListItem | null; canWrite?: boolean }>()

const open = defineModel<boolean>("open", { required: true })

const emit = defineEmits<{ changed: [status: string] }>()

const { statuses, getStatusDot } = useProposalStatuses()

// The card's row fills the drawer at once; the document carries what the list call
// leaves out — the description, the phone and the event's own form answers.
const proposalDoc = useProposal(() => props.proposal?.name)

// The row's speakers show at once; the document's replace them. Its rows are full child
// documents — the drawer only reads the three fields the list already carries.
const speakers = computed<ProposalSpeaker[]>(() =>
	(proposalDoc.doc?.speakers ?? props.proposal?.speakers ?? []).map((speaker) => ({
		first_name: speaker.first_name,
		last_name: speaker.last_name ?? null,
		email: speaker.email,
	})),
)

// The select is seeded from the row and re-seeded whenever the drawer moves to another
// proposal, so a failed write leaves the control showing what is actually stored.
const status = ref("")
watch(
	() => props.proposal?.status,
	(current) => (status.value = current || ""),
	{ immediate: true },
)

// A dot rather than `option.icon`: the status's own colour reads faster than seven
// lucide glyphs. Select renders `description` natively when one is written per status.
const statusOptions = computed(() =>
	(statuses.data || []).map((row: { name: string }) => ({ value: row.name, label: row.name })),
)

// Picking a status only arms the change: the footer's button is what writes it, so a
// mis-click on a decision the speaker gets told about is still recoverable. A reader the
// server would refuse never gets the control — read access alone is a Viewer or Frontdesk.
const changed = computed(() => Boolean(status.value) && status.value !== props.proposal?.status)

async function updateStatus() {
	if (!changed.value) return
	try {
		await proposalDoc.setValue.submit({ status: status.value })
		toast.success(`Marked ${status.value.toLowerCase()}`)
		emit("changed", status.value)
	} catch {
		status.value = props.proposal?.status || ""
		toast.error("Could not change the status")
	}
}

const copyId = useCopyToClipboard()

// One theme per speaker, stable across renders so a face keeps its colour.
const AVATAR_THEMES = ["blue", "green", "amber", "red", "violet"] as const
const avatarTheme = (email: string) => {
	const seed = [...email].reduce((total, character) => total + character.charCodeAt(0), 0)
	return AVATAR_THEMES[seed % AVATAR_THEMES.length]
}

// creation and modified are full timestamps in the site's timezone, so these convert.
const submittedOn = computed(() =>
	props.proposal ? dayjsLocal(props.proposal.creation).format("D MMM YYYY") : "",
)
const lastUpdated = computed(() =>
	props.proposal ? dayjsLocal(props.proposal.modified).format("D MMM'YY, h:mm A") : "",
)

// The reviewer's own reading order: who and when first, then the form's own answers.
const fields = computed(() => [
	{ label: "Submitted on", value: submittedOn.value },
	{ label: "Phone", value: proposalDoc.doc?.phone || "—" },
	...(proposalDoc.doc?.additional_fields || [])
		.filter((field) => field.value)
		.map((field) => ({ label: field.label, value: field.value })),
])
</script>

<template>
	<Drawer v-model:open="open" swipe-direction="right">
		<DrawerContent size="lg">
			<template v-if="proposal">
				<div class="flex items-center gap-2 p-4 pb-0">
					<DrawerClose as-child>
						<Button size="sm" icon="lucide-chevrons-right" aria-label="Close proposal" />
					</DrawerClose>
					<button
						type="button"
						class="copy-id cursor-copy font-mono text-sm tracking-wider uppercase text-ink-gray-5 hover:text-ink-gray-7"
						:aria-label="`Copy proposal id ${proposal.name}`"
						@click="copyId(proposal.name)"
					>
						#{{ proposal.name }}
					</button>
				</div>

				<div class="flex flex-1 flex-col space-y-4 overflow-y-auto p-4">
					<!-- The decision leads: it is what the reviewer opened the drawer to make. -->
					<Select
						v-model="status"
						class="w-fit"
						size="md"
						aria-label="Review status"
						side="bottom"
						:options="statusOptions"
						:disabled="!canWrite || proposalDoc.setValue.loading"
					>
						<!-- The trigger reuses this slot for the selected option, so the dot is
						     defined once and shows in both places. -->
						<template #item-prefix="{ item }">
							<span
								class="size-2 shrink-0 rounded-full transition-colors duration-150"
								:class="getStatusDot(String(item.value))"
								aria-hidden="true"
							/>
						</template>
					</Select>

					<DrawerTitle class="text-4xl font-semibold text-pretty text-ink-gray-9">
						{{ proposal.title }}
					</DrawerTitle>
					<!-- Spoken, not drawn: the speakers and the date are both below, and reka
					     wants the panel described. -->
					<DrawerDescription class="sr-only">
						{{ speakers.length }} speaker{{ speakers.length === 1 ? "" : "s" }}, submitted
						{{ submittedOn }}
					</DrawerDescription>

					<!-- Who is proposing this leads: the panel decides on people as much as topics. -->
					<div v-if="speakers.length" class="space-y-2">
						<h3 class="text-base text-ink-gray-5">Speakers</h3>
						<ul class="space-y-1">
							<li
								v-for="speaker in speakers"
								:key="speaker.email"
								class="flex min-w-0 items-center gap-2 rounded-4 px-1 py-1 transition-colors hover:bg-surface-gray-1"
							>
								<Avatar
									size="md"
									:label="speakerName(speaker)"
									:theme="avatarTheme(speaker.email)"
								/>
								<span class="min-w-0 truncate text-base text-ink-gray-8">
									{{ speakerName(speaker) }}
								</span>
								<span class="ml-auto min-w-0 truncate text-base text-ink-gray-5">
									{{ speaker.email }}
								</span>
							</li>
						</ul>
					</div>

					<div class="grid grid-cols-2 gap-x-5 gap-y-3">
						<div v-for="field in fields" :key="field.label" class="space-y-0.5">
							<p class="text-base text-ink-gray-5">{{ field.label }}</p>
							<p class="text-base text-ink-gray-8">{{ field.value }}</p>
						</div>
					</div>

					<div class="space-y-2">
						<h3 class="text-base text-ink-gray-5">Description</h3>
						<!-- Only the document carries the description, so it arrives a beat later. -->
						<Skeleton v-if="proposalDoc.loading" class="h-16 w-full rounded-4" />
						<!-- Description is a Text Editor field, so it arrives as sanitized HTML. -->
						<div
							v-else-if="proposalDoc.doc?.description"
							class="description prose prose-sm max-w-none text-base leading-[1.6] text-ink-gray-7"
							v-html="proposalDoc.doc.description"
						/>
						<p v-else class="text-base leading-[1.6] text-ink-gray-7">
							No description was submitted.
						</p>
					</div>
				</div>
			</template>

			<template v-if="proposal" #footer>
				<!-- Arriving rather than appearing: the buttons showing up is the confirmation
				     that the pick registered, so the footer is not allowed to jump. -->
				<div v-if="canWrite && changed" class="status-actions flex items-center gap-2">
					<Button
						variant="solid"
						size="md"
						label="Update"
						:loading="proposalDoc.setValue.loading"
						@click="updateStatus"
					/>
					<Button size="md" label="Cancel" @click="status = proposal.status" />
				</div>
				<p class="ml-auto flex items-center gap-1 text-xs text-ink-gray-5">
					<span class="lucide-clock-fading size-3.5 shrink-0" aria-hidden="true" />
					Last updated {{ lastUpdated }}
				</p>
			</template>
		</DrawerContent>
	</Drawer>
</template>

<style scoped>
.status-actions,
.description,
.copy-id {
	--ease-out: cubic-bezier(0.23, 1, 0.32, 1);
}

.status-actions {
	transition:
		opacity 160ms var(--ease-out),
		transform 160ms var(--ease-out);
}

@starting-style {
	.status-actions {
		opacity: 0;
		transform: translateY(4px);
	}
}

/* The description lands a beat after the row it belongs to, so it fades in rather than
   replacing its own skeleton in one frame. */
.description {
	transition: opacity 200ms var(--ease-out);
}

@starting-style {
	.description {
		opacity: 0;
	}
}

.copy-id {
	transition:
		color 160ms var(--ease-out),
		transform 160ms var(--ease-out);
}

.copy-id:active {
	transform: scale(0.97);
}

/* Gentler, not none: the fade still explains what happened, nothing travels. */
@media (prefers-reduced-motion: reduce) {
	.copy-id:active {
		transform: none;
	}

	@starting-style {
		.status-actions {
			transform: none;
		}
	}
}
</style>
