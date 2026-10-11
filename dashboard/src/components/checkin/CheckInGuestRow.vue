<script setup lang="ts">
import { Button, dayjsLocal } from "frappe-ui"
import { computed } from "vue"

import type { EventGuest } from "@/types"

const props = defineProps<{ guest: EventGuest; busy?: boolean }>()

const emit = defineEmits<{ open: []; checkIn: [] }>()

const name = computed(
	() => props.guest.attendee_name || props.guest.attendee_email || "Unnamed guest",
)

const checkedInAt = computed(() =>
	props.guest.checked_in_at ? dayjsLocal(props.guest.checked_in_at).format("h:mm A") : null,
)

const detail = computed(() =>
	[props.guest.ticket_type, props.guest.attendee_email].filter(Boolean).join(" · "),
)
</script>

<template>
	<li
		class="flex items-center gap-3 rounded-[14px] py-2.5 pl-3.5 pr-2.5 transition-colors duration-200 ease-out motion-reduce:transition-none"
		:class="checkedInAt ? 'bg-surface-green-1' : 'bg-surface-gray-1'"
	>
		<button
			type="button"
			class="flex min-w-0 flex-1 flex-col gap-0.5 rounded-4 py-0.5 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
			:aria-label="`Open ${name}`"
			@click="emit('open')"
		>
			<span class="truncate text-base font-semibold text-ink-gray-9">{{ name }}</span>
			<span v-if="checkedInAt" class="truncate text-sm text-ink-green-6">
				Checked in at {{ checkedInAt }}
			</span>
			<span v-else class="truncate text-sm text-ink-gray-5">{{ detail }}</span>
		</button>

		<Button
			v-if="checkedInAt"
			variant="ghost"
			icon="lucide-check"
			class="min-w-[6.5rem] text-ink-green-6"
			:aria-label="`${name} is checked in`"
			disabled
		/>
		<Button
			v-else
			variant="solid"
			theme="green"
			size="md"
			label="Check in"
			class="min-w-[6.5rem] transition-transform duration-150 ease-out active:scale-[0.97] motion-reduce:transition-none"
			:aria-label="`Check in ${name}`"
			:loading="busy"
			@click="emit('checkIn')"
		/>
	</li>
</template>
