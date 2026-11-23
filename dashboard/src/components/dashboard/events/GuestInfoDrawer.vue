<script setup lang="ts">
import { Avatar, Badge, Button, Dropdown, Tooltip, call, dayjsLocal, toast } from "frappe-ui"
import { computed, ref } from "vue"
import { useRoute, useRouter } from "vue-router"

import CopyId from "@/components/common/CopyId.vue"
import DetailRow from "@/components/common/DetailRow.vue"
import {
	Drawer,
	DrawerContent,
	DrawerDescription,
	DrawerNavBar,
	DrawerTitle,
} from "@/components/common/drawer"
import RecordActivity from "@/components/dashboard/comments/RecordActivity.vue"
import GuestAnswers from "@/components/dashboard/events/GuestAnswers.vue"
import GuestZones from "@/components/dashboard/events/GuestZones.vue"
import type { EmailAttachmentChoice } from "@/data/comments"
import type { EventGuest, GuestAddOn, ZoneStatus } from "@/types"
import { serverErrorMessage } from "@/utils/serverError"

const props = defineProps<{
	guest: EventGuest | null
	hasPrevious: boolean
	hasNext: boolean
}>()

const open = defineModel<boolean>("open", { required: true })

const emit = defineEmits<{ previous: []; next: []; changed: [ticket: string] }>()

const route = useRoute()
const router = useRouter()

// A ticket can be issued before anyone is named on it, so the email stands in.
const name = computed(
	() => props.guest?.attendee_name || props.guest?.attendee_email || "Unnamed guest",
)

// Initials of the "Unnamed guest" placeholder would read as a real person's.
const hasIdentity = computed(() =>
	Boolean(props.guest?.attendee_name || props.guest?.attendee_email),
)

const addOnLabel = (addOn: GuestAddOn) =>
	addOn.value ? `${addOn.title}: ${addOn.value}` : addOn.title

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

// The zone being checked in or undone, so the list waits for one write at a time.
const pendingZone = ref<string | null>(null)

async function toggleCheckIn(ticket: string, zone: ZoneStatus) {
	const method = zone.checked_in_at ? "undo_checkin" : "checkin_ticket"
	pendingZone.value = zone.name
	try {
		const data: { message: string } = await call(`buzz.api.checkin.${method}`, {
			ticket_id: ticket,
			zone: zone.name,
		})
		toast.success(data.message)
		emit("changed", ticket)
	} catch (error) {
		toast.error(serverErrorMessage(error) || "Check-in failed")
	} finally {
		pendingZone.value = null
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
			label: "View transaction",
			icon: "lucide-receipt",
			onClick: openTransaction,
			condition: () => Boolean(guest.booking),
		},
	].filter((action) => action.condition())
})
</script>

<template>
	<Drawer v-model:open="open" swipe-direction="right">
		<DrawerContent size="lg">
			<template v-if="guest">
				<header class="shrink-0 px-6 pt-4 pb-2">
					<DrawerNavBar
						noun="guest"
						:has-previous="hasPrevious"
						:has-next="hasNext"
						@previous="emit('previous')"
						@next="emit('next')"
					>
						<CopyId :value="guest.name" label="Ticket ID" />

						<template #actions>
							<Dropdown v-if="actions.length" :options="actions" align="end">
								<Button
									variant="ghost"
									size="sm"
									icon="lucide-ellipsis"
									aria-label="Guest actions"
								/>
							</Dropdown>
						</template>
					</DrawerNavBar>
				</header>

				<RecordActivity
					:key="guest.name"
					doctype="Event Ticket"
					:name="guest.name"
					:recipients="recipients"
					:attachment-choices="attachmentChoices"
					created-label="registered"
				>
					<div class="flex items-start gap-3">
						<Avatar :label="name" size="2xl" class="shrink-0">
							<template v-if="!hasIdentity" #default>
								<span class="lucide-user" aria-hidden="true" />
							</template>
						</Avatar>
						<div class="min-w-0 space-y-1 pt-1">
							<DrawerTitle class="text-3xl leading-tight font-semibold text-pretty text-ink-gray-9">
								{{ name }}
							</DrawerTitle>
							<DrawerDescription class="text-base [overflow-wrap:anywhere] text-ink-gray-5">
								{{ guest.attendee_email || "No email on this ticket" }}
							</DrawerDescription>
						</div>
					</div>

					<dl class="space-y-3 text-base">
						<DetailRow wrap label="Ticket type" icon="lucide-ticket">
							<Badge
								v-if="guest.ticket_type"
								variant="subtle"
								class="max-w-full"
								:title="guest.ticket_type"
							>
								<span class="truncate">{{ guest.ticket_type }}</span>
							</Badge>
							<span v-else class="text-ink-gray-5">—</span>
						</DetailRow>

						<DetailRow wrap label="Registered" icon="lucide-calendar">
							<Tooltip v-if="registeredAt" :text="registeredAt.fromNow()">
								<span>{{ registeredAt.format("D MMM YYYY, h:mm A") }}</span>
							</Tooltip>
							<span v-else class="text-ink-gray-5">—</span>
						</DetailRow>

						<DetailRow v-if="guest.add_ons.length" wrap label="Add-ons" icon="lucide-package-plus">
							<div class="flex flex-wrap gap-1.5">
								<Badge
									v-for="addOn in guest.add_ons"
									:key="`${addOn.title}: ${addOn.value}`"
									variant="subtle"
									class="max-w-full"
									:title="addOnLabel(addOn)"
								>
									<span class="truncate">{{ addOnLabel(addOn) }}</span>
								</Badge>
							</div>
						</DetailRow>

						<DetailRow v-if="guest.booking" wrap label="Transaction" icon="lucide-receipt">
							<Button
								variant="ghost"
								size="sm"
								class="-my-1 -ml-2 font-mono"
								icon-right="lucide-arrow-up-right"
								:label="guest.booking"
								@click="openTransaction"
							/>
						</DetailRow>
					</dl>

					<GuestZones
						v-if="guest.zones.length"
						:zones="guest.zones"
						:pending-zone="pendingZone"
						@toggle="toggleCheckIn(guest.name, $event)"
					/>

					<GuestAnswers v-if="guest.answers.length" :answers="guest.answers" />
				</RecordActivity>
			</template>
		</DrawerContent>
	</Drawer>
</template>
