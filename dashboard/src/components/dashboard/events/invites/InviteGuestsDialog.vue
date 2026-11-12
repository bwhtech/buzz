<script setup lang="ts">
import {
	Button,
	Dialog,
	ErrorMessage,
	LoadingText,
	SidebarItem,
	SidebarSection,
	toast,
	useCall,
	useList,
} from "frappe-ui"
import { computed, ref } from "vue"

import { useEventDoc } from "@/data/events"
import { session } from "@/data/session"
import type { GuestInviteOutcome } from "@/types"
import { serverErrorMessage } from "@/utils/serverError"

import InviteEmailsPane from "./InviteEmailsPane.vue"
import InviteLimitRing from "./InviteLimitRing.vue"
import InviteReview from "./InviteReview.vue"
import { guestCount, INVITE_LIMIT, type TierOption } from "./invites"
import PastEventGuests from "./PastEventGuests.vue"
import { useInviteSelection } from "./useInviteSelection"

const props = defineProps<{ event: string; eventTitle: string; tiers: TierOption[] }>()
const open = defineModel<boolean>({ required: true })
const emit = defineEmits<{ sent: [] }>()

const defaultTier = computed(() => props.tiers[0]?.value ?? "")
const selection = useInviteSelection(() => defaultTier.value)
const { selected } = selection
const stage = ref<"pick" | "review">("pick")
const source = ref("emails")
const message = ref("")
const emailsPane = ref<InstanceType<typeof InviteEmailsPane>>()

const eventDoc = useEventDoc(() => props.event)
// The team's other events, newest first; each one's guests load only when it is opened.
const pastEvents = useList<{ name: string; title: string; start_date: string }>({
	doctype: "Buzz Event",
	fields: ["name", "title", "start_date"],
	filters: () => ({ team: eventDoc.doc?.team ?? "", name: ["!=", props.event] }),
	orderBy: "start_date desc",
	limit: 8,
})
const openEvent = computed(() => pastEvents.data?.find((row) => String(row.name) === source.value))

type InviteParams = {
	event: string
	invites: {
		email: string
		first_name: string | null
		last_name: string | null
		ticket_type: string
	}[]
	message?: string
}

const sendCall = useCall<GuestInviteOutcome[], InviteParams>({
	url: "/api/v2/method/buzz.api.booking.invites.send_invites",
	method: "POST",
	immediate: false,
})
const addCall = useCall<GuestInviteOutcome[], InviteParams>({
	url: "/api/v2/method/buzz.api.booking.invites.add_guests",
	method: "POST",
	immediate: false,
})
const missingNames = computed(() => selected.value.some((invitee) => !invitee.first_name.trim()))
const error = computed(() => serverErrorMessage(sendCall.error ?? addCall.error))

const toggle = (contact: { email: string }) =>
	selection.isSelected(contact.email)
		? selection.removeEmail(contact.email)
		: selection.add([contact])

// Undo is the dialog's while the box is empty or holds only what undo put back; once
// the user edits the text, the browser's own undo takes over.
function onKeydown(keyEvent: KeyboardEvent) {
	if (stage.value !== "pick") return
	const mod = keyEvent.metaKey || keyEvent.ctrlKey
	if (mod && keyEvent.key === "z" && !keyEvent.shiftKey) undo(keyEvent)
	else if (keyEvent.shiftKey && keyEvent.key === "Enter") {
		keyEvent.preventDefault()
		emailsPane.value?.commit()
	}
}

function undo(keyEvent: KeyboardEvent) {
	if (emailsPane.value && !emailsPane.value.ownsUndo()) return
	const change = selection.undo()
	if (!change) return
	keyEvent.preventDefault()
	if ("added" in change && change.typed)
		emailsPane.value?.restore(change.added.map((invitee) => invitee.email))
}

async function submit(call: typeof sendCall) {
	const invites = selected.value.map(({ email, first_name, last_name, ticket_type }) => ({
		email,
		first_name: first_name.trim() || null,
		last_name: last_name.trim() || null,
		ticket_type,
	}))
	const outcomes = await call
		.submit({ event: props.event, invites, ...(call === sendCall && { message: message.value }) })
		.catch(() => null)
	if (!outcomes) return
	report(outcomes)
	emit("sent")
	open.value = false
}

function report(outcomes: GuestInviteOutcome[]) {
	const done = outcomes.filter(
		(outcome) => outcome.status === "invited" || outcome.status === "added",
	)
	const skipped = outcomes.length - done.length
	const verb = done[0]?.status === "added" ? "added" : "invited"
	const description = skipped
		? `${guestCount(skipped)} skipped: already registered or invited.`
		: undefined
	if (done.length) toast.success(`${guestCount(done.length)} ${verb}`, { description })
	else toast.info("Everyone on that list is already registered or invited")
}

function reset() {
	stage.value = "pick"
	source.value = "emails"
	message.value = ""
	selection.reset()
}
</script>

<template>
	<Dialog v-model="open" bare size="4xl" @after-leave="reset">
		<div class="flex h-[min(42rem,85vh)] flex-col" @keydown="onKeydown">
			<header class="flex items-center gap-2 border-b border-outline-gray-1 px-5 py-3">
				<Button
					v-if="stage === 'review'"
					variant="ghost"
					icon="lucide-arrow-left"
					label="Back"
					@click="stage = 'pick'"
				/>
				<h3 class="flex-1 text-lg font-semibold text-ink-gray-9">
					{{ stage === "review" ? `Invite ${guestCount(selected.length)}` : "Invite guests" }}
				</h3>
				<InviteLimitRing :used="selected.length" :limit="INVITE_LIMIT" />
				<Button variant="ghost" icon="lucide-x" label="Close" @click="open = false" />
			</header>

			<div v-if="stage === 'pick'" class="grid min-h-0 flex-1 grid-cols-[14rem_minmax(0,1fr)]">
				<nav
					class="overflow-y-auto border-r border-outline-gray-1 p-2"
					aria-label="Where to invite from"
				>
					<SidebarSection>
						<SidebarItem
							label="Enter emails"
							icon="lucide-at-sign"
							:active="source === 'emails'"
							:on-click="() => (source = 'emails')"
						/>
					</SidebarSection>
					<SidebarSection label="Past events">
						<LoadingText v-if="pastEvents.loading && !pastEvents.data" class="px-2 py-1.5" />
						<p v-else-if="!pastEvents.data?.length" class="px-2 py-1.5 text-p-sm text-ink-gray-5">
							This is your first event.
						</p>
						<SidebarItem
							v-for="row in pastEvents.data"
							:key="row.name"
							:label="row.title"
							icon="lucide-calendar"
							:active="source === String(row.name)"
							:on-click="() => (source = String(row.name))"
						/>
					</SidebarSection>
				</nav>

				<div class="min-h-0 overflow-y-auto px-5 py-4">
					<InviteEmailsPane
						v-if="source === 'emails'"
						ref="emailsPane"
						:event="props.event"
						:selection="selection"
						:tiers="tiers"
						:default-tier="defaultTier"
					/>
					<PastEventGuests
						v-else-if="openEvent"
						:key="source"
						:event="source"
						:title="openEvent.title"
						:is-selected="selection.isSelected"
						@toggle="toggle"
						@select-all="selection.add"
					/>
				</div>
			</div>

			<InviteReview
				v-else
				v-model="selected"
				v-model:message="message"
				:tiers="tiers"
				:default-tier="defaultTier"
				:event-title="eventTitle"
				:host="session.fullName"
				ask-names
				@remove="(invitee) => selection.remove([invitee])"
			/>

			<footer class="flex items-center gap-3 border-t border-outline-gray-1 px-5 py-3">
				<template v-if="stage === 'pick'">
					<p class="flex flex-1 items-center gap-1 text-p-sm text-ink-gray-6">
						<template v-if="selected.length">
							{{ guestCount(selected.length) }} selected
							<Button
								variant="ghost"
								size="sm"
								label="Clear"
								@click="selection.remove([...selected])"
							/>
						</template>
						<template v-else>Add emails, or pick guests from a past event.</template>
					</p>
					<Button
						variant="solid"
						icon-right="lucide-arrow-right"
						label="Next"
						:disabled="!selected.length"
						@click="stage = 'review'"
					/>
				</template>
				<template v-else>
					<div class="min-w-0 flex-1">
						<ErrorMessage v-if="error" :message="error" />
						<p v-else class="text-p-sm text-ink-gray-5">
							{{
								missingNames
									? "Add directly books tickets now, so every guest needs a first name."
									: "Invited guests accept from their email. Add directly books their tickets now."
							}}
						</p>
					</div>
					<Button
						variant="outline"
						label="Add directly"
						:loading="addCall.loading"
						:disabled="!selected.length || missingNames || sendCall.loading"
						@click="submit(addCall)"
					/>
					<Button
						variant="solid"
						icon-left="lucide-send"
						label="Send invites"
						:loading="sendCall.loading"
						:disabled="!selected.length || addCall.loading"
						@click="submit(sendCall)"
					/>
				</template>
			</footer>
		</div>
	</Dialog>
</template>
