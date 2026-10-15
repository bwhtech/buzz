<script setup lang="ts">
import { Button, Dialog, Select, call, dayjsLocal, toast } from "frappe-ui"
import { computed, ref, watch } from "vue"

import {
	Drawer,
	DrawerCloseButton,
	DrawerContent,
	DrawerDescription,
	DrawerTitle,
} from "@/components/common/drawer"
import { useCopyToClipboard } from "@/composables/useCopyToClipboard"
import { useHeldWrite } from "@/composables/useHeldWrite"
import { useProposalStatuses } from "@/composables/useProposalStatuses"
import { useAcceptProposal, useProposal } from "@/data/proposals"
import type { ProposalListItem, ProposalSpeaker } from "@/types"

import ProposalDocument from "./ProposalDocument.vue"

const props = defineProps<{ proposal: ProposalListItem | null; canWrite?: boolean }>()

const open = defineModel<boolean>("open", { required: true })

const emit = defineEmits<{ changed: [proposal: string, status: string] }>()

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

// Picking a status holds the write for as long as the toast offers Undo, so a mis-click
// never reaches the server. Accepting is the exception below, and a reader the server
// would refuse never gets the control — read access alone is a Viewer or Frontdesk.
const selectedStatus = computed({
	get: () => status.value,
	set: (next: string) => requestStatus(next),
})

const heldStatus = useHeldWrite()

// Accepting is the one status that is not a status write: it creates the talk the
// programme is made of, and an account for any speaker who has none. Worth a confirmation.
const ACCEPTED = "Accepted"

const accept = useAcceptProposal()
const confirmingAcceptance = ref(false)

function requestStatus(next: string) {
	const name = props.proposal?.name
	if (!name || !next || next === status.value) return
	if (next === ACCEPTED) {
		confirmingAcceptance.value = true
		return
	}
	holdStatus(name, next, status.value)
}

function holdStatus(name: string, next: string, previous: string) {
	const restore = () => props.proposal?.name === name && (status.value = previous)
	status.value = next
	heldStatus.hold({
		message: `Marked ${next.toLowerCase()}`,
		write: () => saveStatus(name, next),
		undo: restore,
		revert: () => {
			restore()
			saveStatus(name, previous)
		},
	})
}

// Bound to the proposal's name, not the drawer's document, because the drawer may have
// moved to another proposal by the time a held write goes out.
async function saveStatus(name: string, next: string) {
	try {
		await call("frappe.client.set_value", {
			doctype: "Talk Proposal",
			name,
			fieldname: "status",
			value: next,
		})
		emit("changed", name, next)
	} catch {
		if (props.proposal?.name === name) status.value = props.proposal.status
		toast.error("Could not change the status")
	}
}

async function acceptProposal() {
	const name = props.proposal?.name
	if (!name) return
	heldStatus.flush()
	try {
		await accept.submit({ proposal: name })
		status.value = ACCEPTED
		confirmingAcceptance.value = false
		toast.success("Marked accepted")
		emit("changed", name, ACCEPTED)
	} catch {
		toast.error("Could not change the status")
	}
}

const copyId = useCopyToClipboard()

// modified is a full timestamp in the site's timezone, so this converts.
const lastUpdated = computed(() => (props.proposal ? dayjsLocal(props.proposal.modified) : null))
</script>

<template>
	<Drawer v-model:open="open" swipe-direction="right">
		<DrawerContent size="xl">
			<template v-if="proposal">
				<header class="shrink-0 px-6 pt-4 pb-2">
					<div class="flex items-center gap-2">
						<DrawerCloseButton label="Close proposal" />
						<button
							type="button"
							class="copy-id cursor-copy font-mono text-sm tracking-wider uppercase text-ink-gray-5 hover:text-ink-gray-7"
							:aria-label="`Copy proposal id ${proposal.name}`"
							@click="copyId(proposal.name)"
						>
							#{{ proposal.name }}
						</button>
						<span
							v-if="lastUpdated"
							class="ml-auto text-sm text-ink-gray-5"
							:title="lastUpdated.format('D MMM YYYY, h:mm A')"
						>
							Updated {{ lastUpdated.fromNow() }}
						</span>
					</div>

					<!-- The decision leads: it is what the reviewer opened the drawer to make. -->
					<div class="mt-4">
						<Select
							v-model="selectedStatus"
							class="w-fit"
							size="md"
							aria-label="Review status"
							side="bottom"
							:options="statusOptions"
							:disabled="!canWrite || accept.loading"
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
					</div>

					<DrawerTitle class="mt-3 text-4xl font-semibold text-pretty text-ink-gray-9">
						{{ proposal.title }}
					</DrawerTitle>
					<!-- Spoken, not drawn: the speakers are listed below, and reka wants the
					     panel described. -->
					<DrawerDescription class="sr-only">
						{{ speakers.length }} speaker{{ speakers.length === 1 ? "" : "s" }}
					</DrawerDescription>
				</header>

				<ProposalDocument
					:key="proposal.name"
					:proposal="proposal"
					:doc="proposalDoc.doc"
					:loading="proposalDoc.loading"
					:speakers="speakers"
				/>

				<Dialog
					v-model:open="confirmingAcceptance"
					title="Accept this talk?"
					message="This puts the talk on the event's programme. Any speaker without a Buzz account gets one."
					size="md"
				>
					<template #actions>
						<div class="flex justify-end gap-2">
							<Button label="Not yet" @click="confirmingAcceptance = false" />
							<Button
								variant="solid"
								label="Accept and create talk"
								:loading="accept.loading"
								@click="acceptProposal"
							/>
						</div>
					</template>
				</Dialog>
			</template>
		</DrawerContent>
	</Drawer>
</template>

<style scoped>
.copy-id {
	--ease-out: cubic-bezier(0.23, 1, 0.32, 1);
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
}
</style>
