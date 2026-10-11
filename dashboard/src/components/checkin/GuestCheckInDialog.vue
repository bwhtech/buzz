<script setup lang="ts">
import { Avatar, Badge, BottomSheet, Button, Dialog, ErrorMessage, dayjsLocal } from "frappe-ui"
import { computed } from "vue"

import { useIsMobile } from "@/composables/useIsMobile"
import type { EventGuest } from "@/types"

const props = defineProps<{
	guest: EventGuest | null
	payment?: string | null
	busy?: boolean
	error?: string
}>()

const open = defineModel<boolean>("open", { required: true })

const emit = defineEmits<{ checkIn: [] }>()

// A dialog at the desk, a sheet from the bottom edge on a phone held in one hand.
const isMobile = useIsMobile()

const name = computed(
	() => props.guest?.attendee_name || props.guest?.attendee_email || "Unnamed guest",
)

const checkedInAt = computed(() =>
	props.guest?.checked_in_at ? dayjsLocal(props.guest.checked_in_at).format("h:mm A") : null,
)

const registeredAt = computed(() =>
	props.guest?.registered_at ? dayjsLocal(props.guest.registered_at).format("D MMM YYYY") : null,
)

const facts = computed(() =>
	[props.payment, registeredAt.value && `Registered ${registeredAt.value}`].filter(Boolean),
)

const addOnLabel = (addOn: EventGuest["add_ons"][number]) =>
	addOn.value ? `${addOn.title}: ${addOn.value}` : addOn.title
</script>

<template>
	<component
		:is="isMobile ? BottomSheet : Dialog"
		v-model:open="open"
		v-bind="isMobile ? {} : { bare: true, size: 'md' }"
	>
		<div v-if="guest" class="flex flex-col gap-4 p-5">
			<div class="flex items-center gap-3">
				<Avatar :label="name" size="2xl" />
				<div class="min-w-0 flex-1">
					<p class="truncate text-lg font-semibold text-ink-gray-9">{{ name }}</p>
					<p v-if="guest.attendee_email" class="truncate text-base text-ink-gray-5">
						{{ guest.attendee_email }}
					</p>
				</div>
				<Button
					v-if="!isMobile"
					variant="ghost"
					icon="lucide-x"
					aria-label="Close"
					@click="open = false"
				/>
			</div>

			<!-- The tier is what the desk acts on, so it is set large enough to read at arm's length. -->
			<div
				class="flex items-baseline justify-between gap-3 rounded-7 bg-surface-gray-2 px-4 py-3.5"
			>
				<span class="truncate font-display text-4xl uppercase leading-none text-ink-gray-9">
					{{ guest.ticket_type || "Ticket" }}
				</span>
				<span v-if="facts.length" class="shrink-0 text-right text-sm text-ink-gray-5">
					{{ facts.join(" · ") }}
				</span>
			</div>

			<div v-if="guest.add_ons.length" class="flex flex-wrap gap-1.5">
				<Badge
					v-for="addOn in guest.add_ons"
					:key="addOnLabel(addOn)"
					variant="subtle"
					:label="addOnLabel(addOn)"
				/>
			</div>

			<ErrorMessage :message="error" />

			<Button
				variant="solid"
				theme="green"
				class="!h-14 w-full rounded-[14px] !text-lg transition-transform duration-150 ease-out active:scale-[0.97] motion-reduce:transition-none"
				:icon-left="checkedInAt ? 'lucide-check' : undefined"
				:label="checkedInAt ? `Checked in at ${checkedInAt}` : 'Check in'"
				:disabled="Boolean(checkedInAt)"
				:loading="busy"
				@click="emit('checkIn')"
			/>
		</div>
	</component>
</template>
