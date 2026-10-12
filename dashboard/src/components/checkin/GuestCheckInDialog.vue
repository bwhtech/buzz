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

const emit = defineEmits<{ checkIn: []; undo: [] }>()

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
			<div class="flex items-start gap-3">
				<Avatar :label="name" size="2xl" />
				<div class="min-w-0 flex-1">
					<p class="break-words text-lg font-semibold text-ink-gray-9">{{ name }}</p>
					<p v-if="guest.attendee_email" class="break-all text-base text-ink-gray-5">
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
			<div class="flex flex-col gap-1.5 rounded-7 bg-surface-gray-2 px-4 py-3.5">
				<span
					class="line-clamp-2 break-words font-display text-4xl uppercase leading-none text-ink-gray-9"
					:title="guest.ticket_type || undefined"
				>
					{{ guest.ticket_type || "Ticket" }}
				</span>
				<span v-if="facts.length" class="text-sm text-ink-gray-5">
					{{ facts.join(" · ") }}
				</span>
			</div>

			<section v-if="guest.add_ons.length" class="space-y-1.5">
				<h3 class="text-sm font-medium text-ink-gray-5">Add-ons</h3>
				<div class="flex flex-wrap gap-1.5">
					<Badge
						v-for="addOn in guest.add_ons"
						:key="addOnLabel(addOn)"
						variant="subtle"
						:label="addOnLabel(addOn)"
						class="!h-auto max-w-full !whitespace-normal break-words py-0.5"
					/>
				</div>
			</section>

			<ErrorMessage :message="error" />

			<template v-if="checkedInAt">
				<div
					class="flex h-14 items-center justify-center gap-2 rounded-[14px] bg-surface-green-2 text-lg font-medium text-ink-green-7"
				>
					<span class="lucide-check size-5" aria-hidden="true" />
					Checked in at {{ checkedInAt }}
				</div>
				<!-- Undo is for a mis-tap, so it stays quiet under the state it reverses. -->
				<Button
					variant="ghost"
					label="Undo check-in"
					icon-left="lucide-undo-2"
					class="self-center"
					:loading="busy"
					@click="emit('undo')"
				/>
			</template>
			<Button
				v-else
				variant="solid"
				theme="green"
				class="!h-14 w-full rounded-[14px] !text-lg dark:!text-white transition-transform duration-150 ease-out active:scale-[0.97] motion-reduce:transition-none"
				label="Check in"
				:loading="busy"
				@click="emit('checkIn')"
			/>
		</div>
	</component>
</template>
