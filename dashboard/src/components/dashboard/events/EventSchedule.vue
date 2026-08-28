<script setup lang="ts">
import { Combobox, DatePicker, ErrorMessage, TimePicker, dayjsLocal } from "frappe-ui"
import type { ComboboxCustomOption, ComboboxSelectableOption } from "frappe-ui"
import { computed, ref, watch } from "vue"

import { alignedEndDate, isEndBeforeStart } from "@/utils/eventDates"
import {
	allTimeZones,
	zoneCity,
	zoneCountry,
	zoneOffsetLabel,
	zoneSearchText,
} from "@/utils/timeZones"

defineProps<{ disabled?: boolean }>()

const startDate = defineModel<string>("startDate", { default: "" })
const startTime = defineModel<string>("startTime", { default: "" })
const endDate = defineModel<string>("endDate", { default: "" })
const endTime = defineModel<string>("endTime", { default: "" })
const timeZone = defineModel<string>("timeZone", { default: "" })

// An event cannot start in the past, and cannot end before it starts.
const today = dayjsLocal().format("YYYY-MM-DD")
const earliestEnd = computed(() => startDate.value || today)

watch(startDate, (start) => {
	endDate.value = alignedEndDate(start, endDate.value)
})

// Only a single-day event is bounded: a span that runs into another day may well end
// earlier in the day than it began. The picker rejects a typed value below `min` too,
// not just the ones it lists.
const earliestEndTime = computed(() =>
	!endDate.value || endDate.value === startDate.value ? startTime.value : undefined,
)

// `min` is inclusive, so it still lets the end land exactly on the start, which the
// server refuses. It also cannot undo a time that was already valid as a multi-day
// event before the end date was pulled back to the start.
const endsBeforeItStarts = computed(() =>
	isEndBeforeStart(startDate.value, endDate.value, startTime.value, endTime.value),
)

// The row slot is typed for custom rows too, which carry no value; ours never are.
const zoneOf = (item: ComboboxSelectableOption | ComboboxCustomOption) => String(item.value ?? "")

// Built on first open, not on mount. `:options` is a prop, so an eager computed would
// run the 676-code sweep behind `zoneCountry` plus 400-odd Intl formatters while the
// create page is still rendering. The trigger reads `timeZone` directly, so an empty
// list costs it nothing until then.
const hasOpened = ref(false)

const zoneOptions = computed(() =>
	hasOpened.value
		? allTimeZones().map((zone) => ({
				label: zoneSearchText(zone),
				value: zone,
			}))
		: [],
)
</script>

<template>
	<div class="space-y-4">
		<div class="space-y-1">
			<label class="text-base text-ink-gray-7">Start</label>
			<div class="grid grid-cols-2 gap-2">
				<DatePicker
					v-model="startDate"
					format="ddd D MMM"
					placeholder="Date"
					:min="today"
					:disabled="disabled"
				/>
				<TimePicker v-model="startTime" placeholder="Time" :disabled="disabled" />
			</div>
		</div>

		<div class="space-y-1">
			<label class="text-base text-ink-gray-7">End</label>
			<div class="grid grid-cols-2 gap-2">
				<DatePicker
					v-model="endDate"
					format="ddd D MMM"
					placeholder="Date"
					:min="earliestEnd"
					:disabled="disabled"
				/>
				<TimePicker
					v-model="endTime"
					placeholder="Time"
					:min="earliestEndTime"
					:disabled="disabled"
				/>
			</div>

			<ErrorMessage v-if="endsBeforeItStarts" message="End time must be after start time" />
		</div>

		<div class="space-y-1">
			<label class="text-base text-ink-gray-7">Timezone</label>

			<Combobox
				v-model="timeZone"
				:options="zoneOptions"
				placeholder="Search by city, country or zone"
				:disabled="disabled"
				@update:open="(open: unknown) => (hasOpened = hasOpened || Boolean(open))"
			>
				<!-- Mounted inside the popover trigger, so the press opens it on its own. -->
				<template #trigger>
					<Button class="w-full mt-2" :disabled="disabled">
						<div class="flex gap-2">
							<span class="lucide-globe size-4 shrink-0 text-ink-gray-5" aria-hidden="true" />
							<span class="shrink-0 text-base text-ink-gray-8">
								{{ timeZone ? zoneOffsetLabel(timeZone) : "Time zone" }}
							</span>
							<span v-if="timeZone" class="truncate text-base text-ink-gray-5">
								{{ timeZone }}
							</span>
						</div>
					</Button>
				</template>

				<!-- The option label is search text, so the row is drawn from the zone itself. -->
				<template #item="{ item }">
					<div class="flex w-full items-center gap-2 overflow-hidden p-2">
						<span class="truncate text-ink-gray-8">{{ zoneCity(zoneOf(item)) }}</span>
						<span class="truncate text-ink-gray-5">{{ zoneCountry(zoneOf(item)) }}</span>
						<span class="ml-auto shrink-0 text-sm text-ink-gray-5">
							{{ zoneOffsetLabel(zoneOf(item)) }}
						</span>
					</div>
				</template>
			</Combobox>
		</div>
	</div>
</template>
