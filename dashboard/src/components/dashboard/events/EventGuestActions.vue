<script setup lang="ts">
import { Button, call, toast } from "frappe-ui"
import { computed, ref } from "vue"

import RegistrationDialog from "@/components/dashboard/events/RegistrationDialog.vue"
import type { EventGuest, EventGuests } from "@/types"

const props = defineProps<{
	event: string
	closed: boolean
	title?: string | null
	route?: string | null
}>()
const emit = defineEmits<{ changed: [] }>()

const dialogOpen = ref(false)
const exporting = ref(false)

// Every control in the rail answers a press the same way; the string is written once.
const PRESSABLE =
	"duration-150 ease-out active:scale-[0.98] !transition-[transform,background-color,color]"

const cell = (value: string | null | undefined) => `"${(value ?? "").replace(/"/g, '""')}"`

// The list is paged, so the export walks it: a hundred at a time until the server says
// there is no next page.
async function fetchAll(): Promise<EventGuest[]> {
	const all: EventGuest[] = []
	for (let start = 0; ; start += 100) {
		const page: EventGuests = await call("buzz.api.events.get_event_guests", {
			event: props.event,
			start,
			limit: 100,
		})
		all.push(...page.guests)
		if (!page.has_next_page) return all
	}
}

async function exportGuests() {
	exporting.value = true
	try {
		const guests = await fetchAll()
		const rows = [
			["Name", "Email", "Ticket type", "Registered at"],
			...guests.map((guest) => [
				guest.attendee_name,
				guest.attendee_email,
				guest.ticket_type,
				guest.registered_at,
			]),
		]
		const csv = rows.map((row) => row.map(cell).join(",")).join("\n")
		const link = document.createElement("a")
		link.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }))
		link.download = `${props.title || "guests"}.csv`
		document.body.appendChild(link)
		link.click()
		link.remove()
		URL.revokeObjectURL(link.href)
	} catch {
		toast.error("Could not export the guest list. Try again.")
	} finally {
		exporting.value = false
	}
}
type QuickAction = {
	icon: string
	label: string
	link?: string
	loading?: boolean
	onClick?: () => void
}

// The rows differ only in icon, label and what they do, so they are data rather than
// three near-identical buttons. A link row renders as an anchor; the rest as buttons.
const actions = computed<QuickAction[]>(() =>
	[
		props.route
			? {
					icon: "lucide-arrow-up-right",
					label: "Registration page",
					link: `/b/register/${props.route}`,
				}
			: null,
		{
			icon: "lucide-download",
			label: "Download CSV",
			loading: exporting.value,
			onClick: exportGuests,
		},
	].filter((action) => action !== null),
)
</script>

<template>
	<h3 class="text-p-sm font-medium text-ink-gray-5">Quick actions</h3>
	<!-- The whole block is the control: the state is the label, pressing it is how the
		 state gets changed, and the theme carries the state before the words are read. -->
	<Button
		:class="`h-auto w-full !justify-start !gap-3 px-2.5 py-2.5 ${PRESSABLE}`"
		variant="subtle"
		:theme="closed ? 'red' : 'green'"
		@click="dialogOpen = true"
	>
		<template #prefix>
			<span
				class="grid size-9 shrink-0 place-items-center rounded-4 text-white"
				:class="closed ? 'bg-surface-red-5' : 'bg-surface-green-5'"
			>
				<span
					class="size-5"
					:class="closed ? 'lucide-ticket-x' : 'lucide-ticket'"
					aria-hidden="true"
				/>
			</span>
		</template>
		<span class="flex flex-col items-start">
			<span class="text-p-base font-medium">Registration</span>
			<span class="text-p-sm opacity-70">{{ closed ? "Closed" : "Open" }}</span>
		</span>
	</Button>

	<section class="space-y-1 pt-1">
		<Button
			v-for="action in actions"
			:key="action.label"
			:class="`w-full !justify-start ${PRESSABLE}`"
			variant="ghost"
			:label="action.label"
			:link="action.link"
			:loading="action.loading"
			@click="action.onClick?.()"
		>
			<template #prefix>
				<span :class="[action.icon, 'size-4']" aria-hidden="true" />
			</template>
		</Button>
	</section>

	<RegistrationDialog
		v-model="dialogOpen"
		:event="event"
		:closed="closed"
		@changed="emit('changed')"
	/>
</template>
