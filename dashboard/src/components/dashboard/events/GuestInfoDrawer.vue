<script setup lang="ts">
import { Avatar, Badge, Button, Dropdown, Tooltip, call, dayjsLocal, toast } from "frappe-ui"
import { computed, ref } from "vue"
import { useRoute, useRouter } from "vue-router"

import DetailRow from "@/components/common/DetailRow.vue"
import {
	Drawer,
	DrawerCloseButton,
	DrawerContent,
	DrawerDescription,
	DrawerTitle,
} from "@/components/common/drawer"
import RecordActivity from "@/components/dashboard/comments/RecordActivity.vue"
import { useCopyToClipboard } from "@/composables/useCopyToClipboard"
import type { EmailAttachmentChoice } from "@/data/comments"
import type { EventGuest } from "@/types"
import { serverErrorMessage } from "@/utils/serverError"
import { zoneDotClass, zoneStatusLabel } from "@/utils/zoneStatus"

const props = defineProps<{
	guest: EventGuest | null
	hasPrevious: boolean
	hasNext: boolean
}>()

const open = defineModel<boolean>("open", { required: true })

const emit = defineEmits<{ previous: []; next: []; changed: [ticket: string] }>()

const route = useRoute()
const router = useRouter()
const copyToClipboard = useCopyToClipboard()

// A ticket can be issued before anyone is named on it, so the email stands in.
const name = computed(
	() => props.guest?.attendee_name || props.guest?.attendee_email || "Unnamed guest",
)

const recipients = computed(() =>
	props.guest?.attendee_email ? [{ name: name.value, email: props.guest.attendee_email }] : [],
)

const attachmentChoices = computed<EmailAttachmentChoice[]>(() =>
	props.guest
		? [
				{
					key: props.guest.name,
					label: "Ticket",
					fileName: `Ticket-${props.guest.name}.pdf`,
					icon: "lucide-ticket",
					source: { kind: "ticket", ticket: props.guest.name },
				},
			]
		: [],
)

const registeredAt = computed(() =>
	props.guest?.registered_at ? dayjsLocal(props.guest.registered_at) : null,
)

// Check-in from here is at the default zone, which is listed first.
const checkedIn = computed(() => Boolean(props.guest?.zones[0]?.checked_in_at))

const checkingIn = ref(false)

async function toggleCheckIn(ticket: string) {
	const method = checkedIn.value ? "undo_checkin" : "checkin_ticket"
	checkingIn.value = true
	try {
		const data: { message: string } = await call(`buzz.api.checkin.${method}`, {
			ticket_id: ticket,
		})
		toast.success(data.message)
		emit("changed", ticket)
	} catch (error) {
		toast.error(serverErrorMessage(error) || "Check-in failed")
	} finally {
		checkingIn.value = false
	}
}

const openTransaction = () =>
	router.push({
		name: "event-transactions",
		params: { eventId: route.params.eventId },
		query: { booking: props.guest?.booking },
	})

const actions = computed(() => {
	const guest = props.guest
	if (!guest) return []
	return [
		{
			label: checkedIn.value ? "Undo check-in" : "Check in",
			icon: checkedIn.value ? "lucide-rotate-ccw" : "lucide-scan-line",
			onClick: () => toggleCheckIn(guest.name),
		},
		{
			label: "Copy ticket ID",
			icon: "lucide-copy",
			onClick: () => copyToClipboard(guest.name, "Ticket ID copied"),
		},
		{
			label: "View transaction",
			icon: "lucide-receipt",
			onClick: openTransaction,
			condition: () => Boolean(guest.booking),
		},
	]
})
</script>

<template>
	<Drawer v-model:open="open" swipe-direction="right">
		<DrawerContent size="md">
			<template v-if="guest">
				<div class="flex items-center gap-1 px-5 pt-4">
					<DrawerCloseButton label="Close guest" />

					<div class="ml-auto flex items-center gap-1">
						<Tooltip text="Previous guest">
							<Button
								variant="ghost"
								size="sm"
								icon="lucide-chevron-up"
								aria-label="Previous guest"
								:disabled="!hasPrevious"
								@click="emit('previous')"
							/>
						</Tooltip>
						<Tooltip text="Next guest">
							<Button
								variant="ghost"
								size="sm"
								icon="lucide-chevron-down"
								aria-label="Next guest"
								:disabled="!hasNext"
								@click="emit('next')"
							/>
						</Tooltip>
						<Dropdown :options="actions" align="end">
							<Button
								variant="ghost"
								size="sm"
								icon="lucide-ellipsis"
								aria-label="Guest actions"
								:loading="checkingIn"
							/>
						</Dropdown>
					</div>
				</div>

				<RecordActivity
					:key="guest.name"
					doctype="Event Ticket"
					:name="guest.name"
					:recipients="recipients"
					:attachment-choices="attachmentChoices"
					created-label="registered"
				>
					<header class="flex items-center gap-3 pt-3">
						<Avatar :label="name" size="2xl" />
						<div class="min-w-0 space-y-1">
							<DrawerTitle class="truncate text-xl font-semibold text-ink-gray-9">
								{{ name }}
							</DrawerTitle>
							<DrawerDescription class="truncate text-base text-ink-gray-5">
								{{ guest.attendee_email || "No email on this ticket" }}
							</DrawerDescription>
						</div>
					</header>

					<dl class="space-y-3 text-base">
						<DetailRow label="Ticket type">
							<Badge v-if="guest.ticket_type" variant="subtle" :label="guest.ticket_type" />
							<span v-else class="text-ink-gray-5">—</span>
						</DetailRow>

						<DetailRow label="Ticket ID">
							<span class="font-mono text-sm tracking-wider uppercase">{{ guest.name }}</span>
						</DetailRow>

						<DetailRow label="Registered">
							<Tooltip v-if="registeredAt" :text="registeredAt.fromNow()">
								<span>{{ registeredAt.format("D MMM YYYY, h:mm A") }}</span>
							</Tooltip>
							<span v-else class="text-ink-gray-5">—</span>
						</DetailRow>

						<DetailRow v-if="guest.add_ons.length" label="Add-ons">
							<div class="flex flex-wrap gap-1.5">
								<Badge
									v-for="addOn in guest.add_ons"
									:key="`${addOn.title}: ${addOn.value}`"
									theme="blue"
									variant="subtle"
									:label="addOn.value ? `${addOn.title}: ${addOn.value}` : addOn.title"
								/>
							</div>
						</DetailRow>

						<DetailRow v-if="guest.booking" label="Transaction">
							<button
								type="button"
								class="inline-flex items-center gap-1 font-mono text-sm text-ink-gray-8 hover:text-ink-gray-9 hover:underline"
								@click="openTransaction"
							>
								{{ guest.booking }}
								<span class="lucide-arrow-up-right size-3.5 text-ink-gray-5" aria-hidden="true" />
							</button>
						</DetailRow>
					</dl>

					<section v-if="guest.zones.length" class="space-y-2">
						<h3 class="text-sm font-medium text-ink-gray-5">Zones</h3>
						<ul class="space-y-2 text-base">
							<li v-for="zone in guest.zones" :key="zone.name" class="flex items-center gap-2.5">
								<span class="size-2 shrink-0 rounded-full" :class="zoneDotClass(zone)" />
								<span
									class="flex-1 truncate"
									:class="zone.allowed ? 'text-ink-gray-8' : 'text-ink-gray-5'"
								>
									{{ zone.title }}
								</span>
								<span
									class="tabular-nums"
									:class="zone.checked_in_at ? 'text-ink-gray-8' : 'text-ink-gray-5'"
								>
									{{ zoneStatusLabel(zone) }}
								</span>
							</li>
						</ul>
					</section>

					<section v-if="guest.answers.length" class="space-y-2">
						<h3 class="text-sm font-medium text-ink-gray-5">Registration answers</h3>
						<dl class="space-y-3">
							<div v-for="answer in guest.answers" :key="answer.label" class="space-y-0.5">
								<dt class="text-sm text-ink-gray-5">{{ answer.label }}</dt>
								<dd class="text-base text-pretty whitespace-pre-line text-ink-gray-8">
									{{ answer.value }}
								</dd>
							</div>
						</dl>
					</section>
				</RecordActivity>
			</template>
		</DrawerContent>
	</Drawer>
</template>
