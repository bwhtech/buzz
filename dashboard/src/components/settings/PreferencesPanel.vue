<script setup lang="ts">
import {
	Button,
	Combobox,
	ErrorMessage,
	SettingsBody,
	SettingsHeader,
	createResource,
	toast,
} from "frappe-ui"
import type { ComboboxCustomOption, ComboboxSelectableOption } from "frappe-ui"
import { computed, ref, watch } from "vue"

import ThemeSwitcher from "@/components/settings/ThemeSwitcher.vue"
import { userResource } from "@/data/user"
import type { FrappeError } from "@/types"
import {
	allTimeZones,
	currentTimeZone,
	zoneCity,
	zoneCountry,
	zoneOffsetLabel,
	zoneSearchText,
} from "@/utils/timeZones"

// The dialog keeps its panels mounted across tab switches, so the reset below is
// what discards an abandoned edit rather than a remount.
const props = defineProps<{ open?: boolean }>()

// The browser's zone stands in until a choice is stored, which is also what the
// server falls back to when the field is empty.
const savedTimeZone = computed(() => userResource.data?.time_zone || currentTimeZone())

const timeZone = ref(savedTimeZone.value)

watch(
	() => props.open,
	(isOpen) => {
		if (isOpen) timeZone.value = savedTimeZone.value
	},
)

const isDirty = computed(() => timeZone.value !== savedTimeZone.value)

// createResource types its own `error` as `{}`, so the message is kept here for the
// inline ErrorMessage rather than read back off the resource.
const saveError = ref("")

const saveTimeZone = createResource({
	url: "buzz.api.account.update_user_timezone",
	async onSuccess() {
		saveError.value = ""
		await userResource.reload()
		toast.success(__("Preferences updated"))
	},
	onError(error: FrappeError) {
		saveError.value = error.messages?.[0] || __("Could not update your time zone")
	},
})

function save() {
	saveTimeZone.submit({ time_zone: timeZone.value })
}

// The row slot is typed for custom rows too, which carry no value; ours never are.
const zoneOf = (item: ComboboxSelectableOption | ComboboxCustomOption) => String(item.value ?? "")

// Built on first open, not on mount: the 676-code sweep behind `zoneCountry` plus
// 400-odd Intl formatters would otherwise run while the dialog is still opening.
// The trigger reads `timeZone` directly, so an empty list costs it nothing until then.
const hasOpened = ref(false)

const zoneOptions = computed(() =>
	hasOpened.value
		? allTimeZones().map((zone) => ({ label: zoneSearchText(zone), value: zone }))
		: [],
)
</script>

<template>
	<SettingsHeader :title="__('Preferences')" :description="__('How Buzz looks and reads for you.')">
		<template #actions>
			<Transition name="save">
				<Button
					v-if="isDirty || saveTimeZone.loading"
					variant="solid"
					:loading="saveTimeZone.loading"
					@click="save"
				>
					{{ __("Save") }}
				</Button>
			</Transition>
		</template>
	</SettingsHeader>

	<SettingsBody>
		<div class="flex flex-col gap-8 pt-6">
			<section class="flex flex-col gap-4">
				<div class="flex flex-col gap-1">
					<span class="text-base-medium text-ink-gray-8">{{ __("Theme") }}</span>
					<span class="text-p-sm text-ink-gray-6">
						{{ __("Switch between light, dark, or system theme") }}
					</span>
				</div>
				<!-- Applies on click; there is nothing to save, it is a browser preference. -->
				<ThemeSwitcher />
			</section>

			<section class="flex flex-col gap-4">
				<div class="flex flex-col gap-1">
					<span class="text-base-medium text-ink-gray-8">{{ __("Time zone") }}</span>
					<span class="text-p-sm text-ink-gray-6">
						{{ __("Dates and times across Buzz are shown in this zone.") }}
					</span>
				</div>

				<Combobox
					v-model="timeZone"
					:options="zoneOptions"
					:placeholder="__('Search by city, country or zone')"
					@update:open="(isOpen: unknown) => (hasOpened = hasOpened || Boolean(isOpen))"
				>
					<!-- Mounted inside the popover trigger, so the press opens it on its own. -->
					<template #trigger>
						<Button variant="outline" class="w-full sm:w-80">
							<div class="flex gap-2">
								<span class="lucide-globe size-4 shrink-0 text-ink-gray-5" aria-hidden="true" />
								<span class="shrink-0 text-base text-ink-gray-8">
									{{ zoneOffsetLabel(timeZone) }}
								</span>
								<span class="truncate text-base text-ink-gray-5">{{ timeZone }}</span>
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

				<ErrorMessage :message="saveError" />
			</section>
		</div>
	</SettingsBody>
</template>

<style scoped>
/* Matches the Profile panel's Save transition. */
.save-enter-active {
	transition:
		opacity 150ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 150ms cubic-bezier(0.23, 1, 0.32, 1);
}

.save-leave-active {
	transition:
		opacity 100ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 100ms cubic-bezier(0.23, 1, 0.32, 1);
}

.save-enter-from,
.save-leave-to {
	opacity: 0;
	transform: scale(0.95);
}

@media (prefers-reduced-motion: reduce) {
	.save-enter-from,
	.save-leave-to {
		transform: none;
	}
}
</style>
