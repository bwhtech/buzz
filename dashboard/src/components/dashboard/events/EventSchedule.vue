<script setup lang="ts">
import { Combobox, DateTimePicker, ErrorMessage, dayjsLocal } from "frappe-ui"
import type { ComboboxCustomOption, ComboboxSelectableOption } from "frappe-ui"
import type { Ref } from "vue"
import { computed, ref, watch } from "vue"

import { alignedEndDate, isEndBeforeStart, normalizedTime } from "@/utils/eventDates"
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

// An event cannot start in the past.
const today = dayjsLocal().format("YYYY-MM-DD")

watch(startDate, (start) => {
	endDate.value = alignedEndDate(start, endDate.value)
})

// `min` is inclusive, so it still lets the end land exactly on the start, which the
// server refuses. It also cannot undo a time that was already valid as a multi-day
// event before the end date was pulled back to the start.
const endsBeforeItStarts = computed(() =>
	isEndBeforeStart(startDate.value, endDate.value, startTime.value, endTime.value),
)

// DateTimePicker works in `YYYY-MM-DD HH:mm:ss`; the form keeps the halves apart.
function joined(date: string, time: string) {
	return date ? `${date} ${normalizedTime(time) || "00:00:00"}` : ""
}

function splitInto(value: string, date: Ref<string>, time: Ref<string>) {
	const [datePart = "", timePart = ""] = value.split(" ")
	date.value = datePart
	time.value = timePart
}

const startAt = computed({
	get: () => joined(startDate.value, startTime.value),
	set: (value: string) => splitInto(value, startDate, startTime),
})

const endAt = computed({
	get: () => joined(endDate.value, endTime.value),
	set: (value: string) => splitInto(value, endDate, endTime),
})

// The cell draws its own value, so the picker's own format never shows.
const momentLabel = (date: string, time: string) =>
	date ? `${dayjsLocal(date).format("D MMM")}, ${normalizedTime(time).slice(0, 5)}` : "Add date"

// A full moment as the end's `min` also strikes the earlier times off its clock on the
// start's own day; `endsBeforeItStarts` still catches an end landing exactly on it.
const earliestEnd = computed(() => startAt.value || today)

const cellClass =
	"flex w-full flex-col gap-0.5 px-3 py-2 text-left leading-tight transition-colors hover:bg-surface-gray-1"

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
	<!-- The heading and card travel with the fields: both pages present them this way. -->
	<section class="space-y-3 rounded-6 bg-surface-gray-1/90 p-4">
		<h2 class="text-sm font-medium uppercase tracking-wide text-ink-gray-5">When</h2>

		<div class="space-y-6">
			<div class="space-y-2">
				<div
					class="grid grid-cols-2 divide-x divide-outline-gray-2 overflow-hidden rounded-4 border border-outline-gray-2 bg-surface-base"
				>
					<DateTimePicker v-model="startAt" :min="today" :disabled="disabled">
						<template #trigger="{ toggle, open }">
							<button
								type="button"
								:class="[cellClass, open && 'bg-surface-gray-1']"
								:disabled="disabled"
								@click="toggle"
							>
								<span class="text-xs text-ink-gray-5">Start</span>
								<span class="truncate text-base text-ink-gray-9">
									{{ momentLabel(startDate, startTime) }}
								</span>
							</button>
						</template>
					</DateTimePicker>

					<DateTimePicker v-model="endAt" :min="earliestEnd" :disabled="disabled">
						<template #trigger="{ toggle, open }">
							<button
								type="button"
								:class="[cellClass, open && 'bg-surface-gray-1']"
								:disabled="disabled"
								@click="toggle"
							>
								<span class="text-xs text-ink-gray-5">End</span>
								<span class="truncate text-base text-ink-gray-9">
									{{ momentLabel(endDate, endTime) }}
								</span>
							</button>
						</template>
					</DateTimePicker>
				</div>

				<ErrorMessage v-if="endsBeforeItStarts" message="End time must be after start time" />
			</div>

			<Combobox
				v-model="timeZone"
				:options="zoneOptions"
				placeholder="Search by city, country or zone"
				:disabled="disabled"
				@update:open="(open: unknown) => (hasOpened = hasOpened || Boolean(open))"
			>
				<!-- Mounted inside the popover trigger, so the press opens it on its own. -->
				<template #trigger>
					<Button variant="outline" class="w-full mt-2" :disabled="disabled">
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
	</section>
</template>
