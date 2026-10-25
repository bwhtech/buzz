<script setup lang="ts">
import { Avatar, Badge, Tooltip, dayjsLocal } from "frappe-ui"
import { computed } from "vue"

import type { EventGuest } from "@/types"

const props = defineProps<{ guest: EventGuest; selected?: boolean }>()

const emit = defineEmits<{ open: [] }>()

// A ticket can be issued before anyone is named on it, so the email is the fallback
// and the row never renders blank.
const name = computed(
	() => props.guest.attendee_name || props.guest.attendee_email || "Unnamed guest",
)

// Two badges is what a row fits beside a name and an email; the rest collapse into a
// count so a guest with five add-ons cannot push the row wider than the list.
const VISIBLE_ADD_ONS = 2

const label = (addOn: EventGuest["add_ons"][number]) =>
	addOn.value ? `${addOn.title}: ${addOn.value}` : addOn.title

// One dot per enabled zone, so a glance down the list shows who has been where.
const zoneLabel = (zone: EventGuest["zones"][number]) => {
	if (zone.checked_in_at) return `${zone.title}: ${dayjsLocal(zone.checked_in_at).format("h:mm A")}`
	return `${zone.title}: ${zone.allowed ? "Not checked in" : "Not allowed"}`
}

const zoneDot = (zone: EventGuest["zones"][number]) => {
	if (zone.checked_in_at) return "bg-surface-green-6"
	return zone.allowed ? "bg-surface-gray-4" : "border border-outline-gray-4"
}

const shown = computed(() => props.guest.add_ons.slice(0, VISIBLE_ADD_ONS))
const hidden = computed(() => props.guest.add_ons.slice(VISIBLE_ADD_ONS))
</script>

<template>
	<li>
		<button
			type="button"
			class="flex min-h-12 w-full items-center gap-3 px-3.5 py-2 text-left transition-colors duration-150 ease-out hover:bg-surface-gray-1 active:bg-surface-gray-2 motion-reduce:transition-none"
			:class="selected && 'bg-surface-gray-2'"
			:aria-label="`Open ${name}`"
			@click="emit('open')"
		>
			<Avatar :label="name" size="md" />

			<!-- Name and email on one line: the email is how you tell two Harshes apart, so it
				 belongs beside the name rather than under it. -->
			<span class="flex min-w-0 flex-1 items-baseline gap-2">
				<span class="truncate text-base font-medium text-ink-gray-9">{{ name }}</span>
				<span v-if="guest.attendee_email" class="truncate text-base text-ink-gray-5">
					{{ guest.attendee_email }}
				</span>
			</span>

			<span class="flex shrink-0 items-center gap-1.5">
				<Badge
					v-for="addOn in shown"
					:key="label(addOn)"
					theme="blue"
					variant="subtle"
					:label="label(addOn)"
				/>
				<Tooltip v-if="hidden.length" :text="hidden.map(label).join(', ')">
					<Badge theme="blue" variant="subtle" :label="`+${hidden.length}`" />
				</Tooltip>
				<Badge v-if="guest.ticket_type" variant="subtle" :label="guest.ticket_type" />
			</span>

			<Tooltip v-if="guest.zones?.length" :text="guest.zones.map(zoneLabel).join(' · ')">
				<span
					class="flex shrink-0 gap-1 p-1"
					role="img"
					:aria-label="guest.zones.map(zoneLabel).join(', ')"
				>
					<span
						v-for="zone in guest.zones"
						:key="zone.name"
						class="size-2 rounded-full transition-colors duration-200 ease-out"
						:class="zoneDot(zone)"
					/>
				</span>
			</Tooltip>
		</button>
	</li>
</template>
