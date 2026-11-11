<script setup lang="ts">
import { Avatar, Badge, Button, Checkbox, dayjs, dayjsLocal } from "frappe-ui"
import { computed } from "vue"

import type { RegistrationRequest } from "@/types"
import { requesterName, shortAge, ticketTypeOf } from "@/utils/requestQueue"
import { OPEN_VIEW, REQUEST_VIEWS, type RequestView } from "@/utils/requestStatus"

const props = defineProps<{
	request: RegistrationRequest
	view: RequestView
	selected: boolean
	checked: boolean
	// While anything is checked, every row shows its checkbox.
	selecting: boolean
	showStatus: boolean
}>()
const emit = defineEmits<{ open: []; toggle: []; approve: []; decline: [] }>()

const name = computed(() => requesterName(props.request))
const waitlist = computed(() => props.request.request_type === "Waitlist")
const open = computed(() => props.view === OPEN_VIEW[props.request.request_type])
const status = computed(() => REQUEST_VIEWS[props.view])
const age = computed(() => shortAge(dayjs().diff(dayjsLocal(props.request.requested_at), "minute")))
</script>

<template>
	<li
		class="group relative flex min-h-14 items-center gap-3 px-4 py-2.5 transition-colors duration-150 ease-out hover:bg-surface-gray-1 motion-reduce:transition-none"
		:class="(selected || checked) && 'bg-surface-gray-2'"
	>
		<!-- The whole row opens the drawer; the checkbox and actions sit above it. -->
		<button
			type="button"
			class="absolute inset-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-outline-gray-4"
			:aria-label="`Open ${name}`"
			@click="emit('open')"
		/>

		<span class="relative grid size-7 shrink-0 place-items-center">
			<Avatar
				:label="name"
				size="md"
				class="transition-opacity duration-150"
				:class="open && ['group-hover:opacity-0', (checked || selecting) && 'opacity-0']"
			/>
			<!-- Only an open request can be acted on in bulk. -->
			<Checkbox
				v-if="open"
				class="pointer-events-none absolute z-10 opacity-0 transition-opacity duration-150 group-hover:pointer-events-auto group-hover:opacity-100 focus-visible:opacity-100"
				:class="(checked || selecting) && 'pointer-events-auto opacity-100'"
				:model-value="checked"
				:aria-label="`Select ${name}`"
				@update:model-value="emit('toggle')"
			/>
		</span>

		<span class="flex min-w-0 flex-1 items-baseline gap-2">
			<span class="truncate text-base font-medium text-ink-gray-9">{{ name }}</span>
			<span v-if="request.buyer_email" class="truncate text-base text-ink-gray-5">
				{{ request.buyer_email }}
			</span>
		</span>

		<Badge v-if="ticketTypeOf(request)" variant="subtle" :label="ticketTypeOf(request)" />

		<!-- Status and age give way to the actions on hover, in the same slot. -->
		<span class="grid w-32 shrink-0 justify-items-end">
			<span
				class="col-start-1 row-start-1 flex items-center gap-3 transition-opacity duration-150"
				:class="open && 'group-hover:opacity-0 group-focus-within:opacity-0'"
			>
				<Badge v-if="showStatus" variant="subtle" :theme="status.theme" :label="status.label" />
				<span class="min-w-7 text-right text-sm tabular-nums text-ink-gray-5">{{ age }}</span>
			</span>
			<span
				v-if="open"
				class="pointer-events-none relative z-10 col-start-1 row-start-1 flex gap-1 opacity-0 transition-opacity duration-150 group-hover:pointer-events-auto group-hover:opacity-100 group-focus-within:pointer-events-auto group-focus-within:opacity-100"
			>
				<Button
					variant="ghost"
					size="sm"
					icon="lucide-x"
					:tooltip="waitlist ? 'Remove' : 'Decline'"
					:aria-label="`${waitlist ? 'Remove' : 'Decline'} ${name}`"
					@click="emit('decline')"
				/>
				<Button
					variant="solid"
					size="sm"
					:label="waitlist ? 'Let in' : 'Approve'"
					:aria-label="`${waitlist ? 'Let in' : 'Approve'} ${name}`"
					@click="emit('approve')"
				/>
			</span>
		</span>
	</li>
</template>
