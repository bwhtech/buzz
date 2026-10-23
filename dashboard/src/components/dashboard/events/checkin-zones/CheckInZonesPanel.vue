<script setup lang="ts">
import { Badge, Button, Skeleton, Switch, toast } from "frappe-ui"
import { computed, ref } from "vue"

import { serverErrorMessage } from "@/utils/serverError"

import CheckInZoneDialog from "./CheckInZoneDialog.vue"
import { type CheckInZone, useCheckInZones, useEventTicketTypes } from "./checkInZones"

const props = defineProps<{ event: string; disabled?: boolean }>()

const zones = useCheckInZones(props.event)
const ticketTypes = useEventTicketTypes(props.event)

const isDialogOpen = ref(false)
const editing = ref<CheckInZone | null>(null)

const ticketTypeTitles = computed(
	() => new Map((ticketTypes.data ?? []).map((row) => [row.name, row.title])),
)

function open(zone: CheckInZone | null) {
	editing.value = zone
	isDialogOpen.value = true
}

function ticketTypesLabel(zone: CheckInZone) {
	if (!zone.ticket_types.length) return __("All tickets")
	return zone.ticket_types
		.map((row) => ticketTypeTitles.value.get(row.ticket_type) ?? row.ticket_type)
		.join(", ")
}

async function toggleEnabled(zone: CheckInZone, enabled: boolean) {
	await zones.setValue.submit({ name: zone.name, enabled: enabled ? 1 : 0 }).catch(() => null)
	if (zones.setValue.error) toast.error(serverErrorMessage(zones.setValue.error))
}
</script>

<template>
	<section class="flex flex-col gap-3">
		<div class="flex flex-wrap items-end justify-between gap-x-4 gap-y-3">
			<div class="flex min-w-0 flex-[1_1_16rem] flex-col gap-1">
				<h2 class="text-lg font-semibold text-ink-gray-9">{{ __("Check-in zones") }}</h2>
				<p class="text-p-sm text-pretty text-ink-gray-5">
					{{ __("Areas of the venue guests are checked in to, such as entry, workshops or lunch") }}
				</p>
			</div>
			<Button
				variant="solid"
				icon-left="lucide-plus"
				:label="__('Add zone')"
				:disabled="disabled"
				@click="open(null)"
			/>
		</div>

		<div class="rounded-5 border border-outline-gray-2 p-1">
			<Skeleton v-if="!zones.data" class="h-14 w-full rounded-5" />

			<ul v-else>
				<li
					v-for="zone in zones.data"
					:key="zone.name"
					class="flex items-center gap-2 rounded-5 pr-3 transition-colors duration-150 ease-out hover:bg-surface-gray-1"
				>
					<button
						type="button"
						class="flex min-w-0 flex-1 flex-col gap-1 rounded-5 py-2.5 pl-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3 disabled:cursor-default"
						:disabled="disabled"
						:aria-label="__('Edit zone {0}', [zone.title])"
						@click="open(zone)"
					>
						<span class="flex min-w-0 items-center gap-2">
							<span class="truncate text-base font-medium text-ink-gray-9">{{ zone.title }}</span>
							<Badge v-if="zone.is_default" size="sm" :label="__('Default')" />
						</span>
						<span class="truncate text-p-sm text-ink-gray-5">
							{{ __(zone.repeat_rule) }} · {{ ticketTypesLabel(zone) }}
						</span>
					</button>
					<Switch
						:model-value="!!zone.enabled"
						:disabled="disabled || !!zone.is_default"
						:aria-label="__('Enable zone {0}', [zone.title])"
						@update:model-value="toggleEnabled(zone, !!$event)"
					/>
				</li>
			</ul>
		</div>

		<CheckInZoneDialog
			v-model:open="isDialogOpen"
			:event="event"
			:zone="editing"
			:zones="zones"
			:ticket-types="ticketTypes.data ?? []"
		/>
	</section>
</template>
