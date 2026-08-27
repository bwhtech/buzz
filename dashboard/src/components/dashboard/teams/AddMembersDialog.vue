<script setup lang="ts">
import { Button, Dialog, FormControl, toast } from "frappe-ui"
import { computed, nextTick, ref, watch } from "vue"

import { inviteMembers } from "@/data/teams"
import type { FrappeError, InviteOutcome } from "@/types"

// Mirrors the membership doctype's own options, minus Owner. The server rejects
// anything outside this set, so a drift here fails loudly rather than silently.
const ROLE_OPTIONS = ["Admin", "Manager", "Frontdesk", "Viewer"]
const DEFAULT_ROLE = "Manager"
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

interface InviteRow {
	id: number
	email: string
	team_role: string
}

const props = defineProps<{ team: string }>()
const isOpen = defineModel<boolean>({ required: true })
const emit = defineEmits<{ success: [] }>()

// Rows are spliced, so they need an identity of their own — a key by position would
// hand Vue the wrong node the moment a row in the middle goes.
let lastRowId = 0

const rows = ref<InviteRow[]>([newRow()])
const showErrors = ref(false)
const form = ref<HTMLFormElement>()

// createResource types its error as {}, so the message needs narrowing.
const errorMessage = computed(() => (inviteMembers.error as FrappeError | null)?.message)

const filled = computed(() => rows.value.filter((row) => row.email.trim()))

const invalid = computed(() => filled.value.filter((row) => !EMAIL_PATTERN.test(row.email.trim())))

function newRow(email = "", team_role = DEFAULT_ROLE): InviteRow {
	lastRowId += 1
	return { id: lastRowId, email, team_role }
}

function isInvalid(row: InviteRow) {
	return showErrors.value && invalid.value.includes(row)
}

watch(isOpen, async (open) => {
	if (!open) return
	rows.value = [newRow()]
	showErrors.value = false
	inviteMembers.reset()
	await nextTick()
	form.value?.querySelector("input")?.focus()
})

// One watcher rather than an input handler: it only ever sees values the model has
// already committed, so a paste cannot be read a keystroke late.
watch(
	rows,
	(current) => {
		splitPastedEmails(current)

		// Typing in the last row opens the next one, so a second invite needs no click.
		const last = current[current.length - 1]
		if (last?.email.trim()) current.push(newRow("", last.team_role))
	},
	{ deep: true },
)

// A pasted list is the fastest way to invite a whole team, so commas become rows.
function splitPastedEmails(current: InviteRow[]) {
	const index = current.findIndex((row) => row.email.includes(","))
	if (index < 0) return

	const row = current[index]
	const emails = row.email
		.split(",")
		.map((email) => email.trim())
		.filter(Boolean)

	row.email = emails[0] ?? ""
	current.splice(index + 1, 0, ...emails.slice(1).map((email) => newRow(email, row.team_role)))
}

// The trailing blank row is not a member, so there is nothing to take off the list.
function canRemove(index: number) {
	return rows.value.length > 1 && index < rows.value.length - 1
}

function removeRow(index: number) {
	rows.value.splice(index, 1)
	if (!rows.value.length) rows.value.push(newRow())
}

function labelFor(outcome: InviteOutcome) {
	return outcome.full_name || outcome.email
}

// Two names read better than a count; past that a count reads better than a queue.
function nameList(outcomes: InviteOutcome[]) {
	const [first, second] = outcomes.map(labelFor)
	if (outcomes.length === 1) return first
	if (outcomes.length === 2) return `${first} and ${second}`
	return `${first} and ${outcomes.length - 1} others`
}

// An invited stranger does not appear in the table behind this dialog until they
// accept, so the toast has to say so — otherwise they look like they went missing.
function report(outcomes: InviteOutcome[]) {
	const added = outcomes.filter((outcome) => outcome.status === "added")
	const invited = outcomes.filter((outcome) => outcome.status === "invited")
	const pending = "They'll show up here once they accept."

	if (!added.length && !invited.length) {
		toast.info("Everyone on that list is already on the team")
		return
	}

	if (!invited.length) {
		toast.success(`${nameList(added)} joined the team`)
		return
	}

	if (!added.length) {
		const title =
			invited.length === 1
				? `Invitation sent to ${nameList(invited)}`
				: `${invited.length} invitations sent`
		toast.success(title, { description: pending })
		return
	}

	// Not "they" here — half of them are already in the table behind this toast.
	toast.success(`${added.length} joined, ${invited.length} invited`, {
		description: "The invitations show up here once they're accepted.",
	})
}

// One bad address should cost the user that row, not the whole batch.
async function submit() {
	showErrors.value = true
	if (!filled.value.length || invalid.value.length) return

	const outcomes = await inviteMembers.submit({
		team: props.team,
		invites: filled.value.map((row) => ({
			email: row.email.trim(),
			team_role: row.team_role,
		})),
	})

	report(outcomes ?? [])
	emit("success")
	isOpen.value = false
}
</script>

<template>
	<Dialog v-model="isOpen" title="Add members" size="xl">
		<!-- novalidate: the action button lives outside this form, so the browser's own
			 bubble would only ever fire on the Enter path. One rule for both. -->
		<form ref="form" novalidate class="space-y-3" @submit.prevent="submit">
			<p class="text-base text-ink-gray-5">
				Colleagues who already have an account join straight away. Everyone else gets an email
				invitation.
			</p>

			<div
				class="grid grid-cols-[minmax(0,1fr)_9rem_2rem] items-center gap-2 text-sm text-ink-gray-5"
			>
				<span>Email</span>
				<span>Role</span>
			</div>

			<TransitionGroup tag="div" name="row" class="relative space-y-2">
				<div
					v-for="(row, index) in rows"
					:key="row.id"
					class="grid grid-cols-[minmax(0,1fr)_9rem_2rem] items-center gap-2"
				>
					<FormControl
						v-model="row.email"
						type="email"
						placeholder="colleague@example.com"
						aria-label="Email"
						:class="isInvalid(row) && '[&_input]:!border-outline-red-3'"
					/>

					<FormControl
						v-model="row.team_role"
						type="select"
						aria-label="Role"
						:options="ROLE_OPTIONS"
					/>

					<Button
						v-if="canRemove(index)"
						variant="ghost"
						:label="`Remove ${row.email || 'row'}`"
						@click="removeRow(index)"
					>
						<template #icon>
							<span class="lucide-x size-4" />
						</template>
					</Button>
				</div>
			</TransitionGroup>

			<ErrorMessage
				:message="invalid.length && showErrors ? 'Check the highlighted addresses.' : errorMessage"
			/>

			<!-- Lets Enter submit from any field, since the actions live outside this form. -->
			<button type="submit" class="hidden" />
		</form>

		<template #actions="{ close }">
			<div class="flex gap-2">
				<Button
					variant="solid"
					label="Send invites"
					:loading="inviteMembers.loading"
					:disabled="!filled.length"
					@click="submit"
				/>
				<Button variant="outline" label="Cancel" @click="close" />
			</div>
		</template>
	</Dialog>
</template>

<style scoped>
/* Matches the members table behind this dialog: the leaving row drops out of flow so
   the rows below start closing the gap straight away. */
.row-leave-active {
	position: absolute;
	inset-inline: 0;
	transition:
		opacity 150ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 150ms cubic-bezier(0.23, 1, 0.32, 1);
}

.row-leave-to {
	opacity: 0;
	transform: translateX(0.5rem);
}

.row-move {
	transition: transform 250ms cubic-bezier(0.23, 1, 0.32, 1);
}

/* Entry is opacity only, on purpose: a row arrives mid-keystroke, and anything that
   moves under the caret reads as lag. */
.row-enter-from {
	opacity: 0;
}

.row-enter-active {
	transition: opacity 120ms cubic-bezier(0.23, 1, 0.32, 1);
}

@media (prefers-reduced-motion: reduce) {
	.row-leave-to {
		transform: none;
	}

	.row-move {
		transition: none;
	}
}
</style>
