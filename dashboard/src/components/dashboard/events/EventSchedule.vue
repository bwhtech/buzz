<script setup lang="ts">
import { alignedEndDate } from "@/utils/eventDates";
import {
	allTimeZones,
	zoneCity,
	zoneCountry,
	zoneOffsetLabel,
	zoneSearchText,
} from "@/utils/timeZones";
import { Combobox, DatePicker, TimePicker, dayjsLocal } from "frappe-ui";
import { computed, ref, watch } from "vue";

const startDate = defineModel<string>("startDate", { default: "" });
const startTime = defineModel<string>("startTime", { default: "" });
const endDate = defineModel<string>("endDate", { default: "" });
const endTime = defineModel<string>("endTime", { default: "" });
const timeZone = defineModel<string>("timeZone", { default: "" });

// An event cannot start in the past, and cannot end before it starts.
const today = dayjsLocal().format("YYYY-MM-DD");
const earliestEnd = computed(() => startDate.value || today);

watch(startDate, (start) => {
	endDate.value = alignedEndDate(start, endDate.value);
});

// The row slot is typed for custom rows too, which carry no value; ours never are.
const zoneOf = (item: { type?: string; value?: string }) => item.value ?? "";

// Built on first open, not on mount. `:options` is a prop, so an eager computed would
// run the 676-code sweep behind `zoneCountry` plus 400-odd Intl formatters while the
// create page is still rendering. The trigger reads `timeZone` directly, so an empty
// list costs it nothing until then.
const hasOpened = ref(false);

const zoneOptions = computed(() =>
	hasOpened.value
		? allTimeZones().map((zone) => ({
				label: zoneSearchText(zone),
				value: zone,
		  }))
		: []
);
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
				/>
				<TimePicker v-model="startTime" placeholder="Time" />
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
				/>
				<TimePicker v-model="endTime" placeholder="Time" />
			</div>
		</div>

		<div class="space-y-1">
			<label class="text-base text-ink-gray-7">Timezone</label>

			<Combobox
				v-model="timeZone"
				:options="zoneOptions"
				placeholder="Search by city, country or zone"
				@update:open="(open: boolean) => (hasOpened = hasOpened || open)"
			>
				<!-- Mounted inside the popover trigger, so the press opens it on its own. -->
				<template #trigger>
					<Button class="w-full mt-2">
						<div class="flex gap-2">
							<span
								class="lucide-globe size-4 shrink-0 text-ink-gray-5"
								aria-hidden="true"
							/>
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
						<span class="truncate text-ink-gray-5">{{
							zoneCountry(zoneOf(item))
						}}</span>
						<span class="ml-auto shrink-0 text-sm text-ink-gray-5">
							{{ zoneOffsetLabel(zoneOf(item)) }}
						</span>
					</div>
				</template>
			</Combobox>
		</div>
	</div>
</template>
