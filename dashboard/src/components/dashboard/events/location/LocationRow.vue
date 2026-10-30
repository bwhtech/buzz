<script setup lang="ts">
import { ItemListRow } from "frappe-ui"

import LocationNumber from "@/components/dashboard/events/location/LocationNumber.vue"

// `checked` swaps the icon for a checkbox, for picking several places; `number` is the
// place's position among those picked. Vue reads a missing boolean prop as false, so the
// default keeps `checked` undefined when the row is not pickable.
withDefaults(
	defineProps<{
		icon: string
		title: string
		subtitle?: string | null
		active?: boolean
		checked?: boolean
		number?: number
	}>(),
	{ checked: undefined, number: undefined, subtitle: undefined },
)
</script>

<template>
	<!-- The button is written here, not passed as `as="button"`: a dynamic "button" resolves
	 to the globally registered frappe-ui Button. -->
	<button
		type="button"
		class="group block w-full rounded-4 text-left outline-none"
		:aria-pressed="checked"
	>
		<!-- ItemListRow centres its prefix and has no hover of its own: both are set here. -->
		<ItemListRow
			as="span"
			:active="active"
			class="!items-start duration-100 group-focus-visible:bg-surface-gray-2 group-active:bg-surface-gray-3"
			:class="!active && 'group-hover:bg-surface-gray-2'"
		>
			<template #prefix>
				<!-- Drawn, not a Checkbox: an input cannot sit inside a button. The button's
				 aria-pressed carries the state. -->
				<span
					v-if="checked !== undefined"
					class="mt-0.5 grid size-4 place-items-center rounded-[5px] border transition-colors duration-100"
					:class="
						checked
							? 'border-[--ink-gray-9] bg-[--ink-gray-9] text-[--surface-base]'
							: 'border-outline-gray-3 bg-surface-base'
					"
					aria-hidden="true"
				>
					<span v-if="checked" class="lucide-check size-3" />
				</span>
				<span v-else class="mt-0.5 size-4 text-ink-gray-5" :class="icon" aria-hidden="true" />
			</template>
			<template #label>
				<span class="block truncate text-base text-ink-gray-8">{{ title }}</span>
				<span v-if="subtitle" class="block truncate text-p-sm text-ink-gray-5">{{ subtitle }}</span>
			</template>
			<template v-if="number" #suffix>
				<LocationNumber :number="number" class="mt-0.5" />
			</template>
		</ItemListRow>
	</button>
</template>
