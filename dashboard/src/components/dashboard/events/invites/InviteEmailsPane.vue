<script setup lang="ts">
import {
	Avatar,
	Button,
	ErrorMessage,
	KeyboardShortcut,
	TextInput,
	useCall,
	useFileUpload,
} from "frappe-ui"
import { computed, ref } from "vue"

import ImportDropzone from "@/components/dashboard/imports/ImportDropzone.vue"
import { downloadCsv } from "@/utils/csv"
import { serverErrorMessage } from "@/utils/serverError"

import {
	displayName,
	guestCount,
	INVITE_LIMIT,
	type Invitee,
	isValidEmail,
	newInvitee,
	readyInvitees,
	splitEmails,
	TEMPLATE_COLUMNS,
	tierFromSheet,
	type TierOption,
} from "./invites"
import InviteSheetCheck from "./InviteSheetCheck.vue"
import type { InviteSelection } from "./useInviteSelection"

type SheetRow = { first_name: string; last_name: string; email: string; tier: string }

const props = defineProps<{
	event: string
	selection: InviteSelection
	tiers: TierOption[]
	defaultTier: string
}>()

const draft = ref("")
// What undo last put back in the box; while the box still reads that, undo stays the dialog's.
const restored = ref("")
const field = ref<HTMLElement>()
const error = ref("")
const sheet = ref<{ rows: Invitee[]; fileName: string } | null>(null)
const skipInvalid = ref(false)

const selected = computed(() => props.selection.selected.value)
const sheetReady = computed(() => readyInvitees(sheet.value?.rows ?? [], props.tiers))
const uploader = useFileUpload()
const readSheet = useCall<SheetRow[], { event: string; file_url: string }>({
	url: "/api/v2/method/buzz.api.booking.invites.read_invite_sheet",
	method: "POST",
	immediate: false,
})
const sheetError = computed(
	() => uploader.error.value?.message ?? serverErrorMessage(readSheet.error),
)
const progress = computed(() =>
	uploader.isUploading.value ? uploader.progress.value : readSheet.loading ? 100 : null,
)
const sheetBlocked = computed(
	() => !skipInvalid.value && sheetReady.value.length < (sheet.value?.rows.length ?? 0),
)

const overLimit = (left: number) =>
	left ? `Only ${INVITE_LIMIT} guests per batch. ${left} left out.` : ""

/** Adds every valid address in the box; anything that isn't an email stays for fixing. */
function commit() {
	const tokens = splitEmails(draft.value)
	if (!tokens.length) return
	const invalid = tokens.filter((email) => !isValidEmail(email))
	const left = props.selection.add(
		tokens.filter(isValidEmail).map((email) => ({ email })),
		true,
	)
	draft.value = invalid.join(", ")
	const notEmail = invalid.length ? `“${invalid[0]}” isn't an email address.` : ""
	error.value = [notEmail, overLimit(left)].filter(Boolean).join(" ")
}

// Space and comma end an address; Enter and Shift+Enter press Add.
function onKeydown(event: KeyboardEvent) {
	if (![" ", ",", "Enter"].includes(event.key)) return
	event.preventDefault()
	commit()
}

// The pasted text lands in the box after this event, so the commit waits a tick.
const commitAfterPaste = () => setTimeout(commit)

async function loadSheet(file: File) {
	const uploaded = await uploader.upload(file, { private: true }).catch(() => null)
	if (!uploaded) return
	const rows = await readSheet
		.submit({ event: props.event, file_url: uploaded.file_url })
		.catch(() => null)
	if (!rows) return
	sheet.value = {
		fileName: file.name,
		rows: rows.map((row) =>
			newInvitee({ ...row, ticket_type: tierFromSheet(row.tier, props.tiers, props.defaultTier) }),
		),
	}
}

const downloadTemplate = () => downloadCsv("guest invites.csv", [TEMPLATE_COLUMNS])

function addSheet() {
	error.value = overLimit(props.selection.add(sheetReady.value))
	sheet.value = null
	skipInvalid.value = false
}

/** Puts addresses an undo took off the list back into the box, ahead of anything typed. */
function restore(emails: string[]) {
	draft.value = [...emails, draft.value.trim()].filter(Boolean).join(", ")
	restored.value = draft.value
	error.value = ""
	field.value?.querySelector("input")?.focus()
}

const ownsUndo = () => !draft.value || draft.value === restored.value

defineExpose({ commit, restore, ownsUndo })
</script>

<template>
	<div class="space-y-5">
		<section class="space-y-2">
			<h4 class="text-base font-medium text-ink-gray-9">Add emails</h4>
			<div class="flex gap-2">
				<div ref="field" class="flex-1">
					<TextInput
						v-model="draft"
						placeholder="Paste or type emails"
						aria-label="Emails"
						@keydown="onKeydown"
						@paste="commitAfterPaste"
					/>
				</div>
				<Button variant="subtle" label="Add" :disabled="!draft.trim()" @click="commit">
					<template #suffix>
						<KeyboardShortcut class="max-md:hidden" combo="Shift+Enter" />
					</template>
				</Button>
			</div>
			<ErrorMessage v-if="error" :message="error" />
			<p v-else class="flex items-center gap-1.5 text-p-sm text-ink-gray-5">
				Space or comma adds an address
				<span class="flex items-center gap-1.5 max-md:hidden">
					· <KeyboardShortcut combo="Mod+Z" /> to undo
				</span>
			</p>
		</section>

		<Transition name="swap" mode="out-in">
			<TransitionGroup
				v-if="selected.length && !sheet"
				key="list"
				tag="ul"
				name="guest"
				class="relative -mx-2"
				aria-label="Added guests"
			>
				<li
					v-for="invitee in selected"
					:key="invitee.id"
					class="group flex items-center gap-3 rounded-4 px-2 py-1.5 hover:bg-surface-gray-2"
				>
					<Avatar :label="displayName(invitee)" size="md" />
					<span class="min-w-0 flex-1">
						<span class="block truncate text-p-sm text-ink-gray-9">{{ displayName(invitee) }}</span>
						<span v-if="invitee.first_name" class="block truncate text-p-xs text-ink-gray-5">{{
							invitee.email
						}}</span>
					</span>
					<Button
						variant="ghost"
						size="sm"
						icon="lucide-x"
						class="shrink-0 transition-opacity duration-150 [@media(hover:hover)]:opacity-0 [@media(hover:hover)]:group-hover:opacity-100 [@media(hover:hover)]:focus-visible:opacity-100"
						:label="`Remove ${displayName(invitee)}`"
						@click="selection.remove([invitee])"
					/>
				</li>
			</TransitionGroup>

			<section v-else key="upload" class="space-y-2">
				<h4 class="text-base font-medium text-ink-gray-9">Import a sheet</h4>
				<template v-if="!sheet">
					<ImportDropzone
						requirement="Columns: First Name, Last Name, Email, Tier"
						:row-limit="INVITE_LIMIT"
						:progress="progress"
						@file="loadSheet"
						@template="downloadTemplate"
					/>
					<ErrorMessage :message="sheetError" />
				</template>
				<!-- The checked sheet is its own task until its rows are added, so it gets a box. -->
				<div v-else class="space-y-4 rounded-5 border border-outline-gray-2 p-4">
					<InviteSheetCheck
						v-model:rows="sheet.rows"
						v-model:skip-invalid="skipInvalid"
						:file-name="sheet.fileName"
						:tiers="tiers"
						@replace="sheet = null"
					/>
					<div class="flex justify-end gap-2">
						<Button variant="ghost" label="Cancel" @click="sheet = null" />
						<Button
							variant="solid"
							:label="`Add ${guestCount(sheetReady.length)}`"
							:disabled="sheetBlocked"
							@click="addSheet"
						/>
					</div>
				</div>
			</section>
		</Transition>
	</div>
</template>

<style scoped>
/* A row arrives mid-keystroke, so entry is opacity only: movement under the caret reads as lag. */
.guest-enter-active {
	transition: opacity 140ms cubic-bezier(0.23, 1, 0.32, 1);
}
.guest-enter-from {
	opacity: 0;
}

/* The leaving row drops out of flow so the rows below start closing the gap at once. */
.guest-leave-active {
	position: absolute;
	inset-inline: 0;
	transition:
		opacity 120ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 120ms cubic-bezier(0.23, 1, 0.32, 1);
}
.guest-leave-to {
	opacity: 0;
	transform: translateX(8px);
}
.guest-move {
	transition: transform 200ms cubic-bezier(0.23, 1, 0.32, 1);
}

/* List and upload trade places: the incoming side settles up, the outgoing side just fades. */
.swap-enter-active {
	transition:
		opacity 200ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 200ms cubic-bezier(0.23, 1, 0.32, 1),
		filter 200ms cubic-bezier(0.23, 1, 0.32, 1);
}
.swap-leave-active {
	transition: opacity 120ms cubic-bezier(0.23, 1, 0.32, 1);
}
.swap-enter-from {
	opacity: 0;
	transform: translateY(6px);
	filter: blur(2px);
}
.swap-leave-to {
	opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
	.guest-leave-to,
	.swap-enter-from {
		transform: none;
		filter: none;
	}
	.guest-move {
		transition: none;
	}
}
</style>
