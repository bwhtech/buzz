<script setup lang="ts">
import { Badge, Button, Checkbox, Popover, Select } from "frappe-ui"
import { computed } from "vue"

export interface FilterOption {
	value: string
	label: string
}

export interface FilterGroup {
	/** Doubles as the query-param name. */
	key: string
	label: string
	options: FilterOption[]
	/** Rendered beside the Filters button rather than inside it. */
	quick?: boolean
	/** One choice at a time, shown as a select. Give it an option with an empty value
	 *  for the "no filter" case — that choice drops the param. */
	single?: boolean
}

/** Group key to selected values. Within a group the values are OR-ed. */
export type FilterValues = Record<string, string[]>

const props = defineProps<{ groups: FilterGroup[] }>()
const model = defineModel<FilterValues>({ required: true })

const quickGroups = computed(() => props.groups.filter((group) => group.quick))
const panelGroups = computed(() => props.groups.filter((group) => !group.quick))

// Chips already show their own state, so only what the panel hides gets counted.
const hiddenCount = computed(() =>
	panelGroups.value.reduce((total, group) => total + (model.value[group.key]?.length || 0), 0),
)

const anyActive = computed(() => props.groups.some((group) => model.value[group.key]?.length))

const isOn = (key: string, value: string) => !!model.value[key]?.includes(value)

const chosen = (key: string) => model.value[key]?.[0] || ""

/** An empty value means "no filter", so it clears the group rather than selecting nothing. */
function choose(key: string, value: string) {
	model.value = { ...model.value, [key]: value ? [value] : [] }
}

function toggle(key: string, value: string) {
	const current = model.value[key] || []
	// Assignment, not mutation: a route-backed getter hands back a fresh array each read.
	model.value = {
		...model.value,
		[key]: isOn(key, value) ? current.filter((held) => held !== value) : [...current, value],
	}
}

const clear = () => (model.value = Object.fromEntries(props.groups.map((group) => [group.key, []])))
</script>

<template>
	<div class="flex flex-wrap items-center gap-2">
		<template v-for="group in quickGroups" :key="group.key">
			<Select
				v-if="group.single"
				size="sm"
				:aria-label="group.label"
				:class="chosen(group.key) && 'bg-surface-gray-2 ring-1 ring-outline-gray-4'"
				:options="group.options"
				:model-value="chosen(group.key)"
				@update:model-value="choose(group.key, String($event ?? ''))"
			/>

			<div v-else role="group" :aria-label="group.label" class="flex gap-2">
				<Button
					v-for="option in group.options"
					:key="option.value"
					size="sm"
					:label="option.label"
					:variant="isOn(group.key, option.value) ? 'solid' : 'subtle'"
					:aria-pressed="isOn(group.key, option.value)"
					@click="toggle(group.key, option.value)"
				/>
			</div>
		</template>

		<div v-if="panelGroups.length" class="flex items-center">
			<!-- Popover, not Dropdown: a Dropdown's switch rows sit outside the focus
			     collection, so arrow keys and Tab skip them and the panel is mouse-only. -->
			<Popover align="start">
				<template #trigger>
					<!-- No `label` prop: Button forces aria-label from it, silencing the count. -->
					<Button
						size="sm"
						icon-left="lucide-list-filter"
						:class="anyActive && 'rounded-r-none'"
						:aria-label="hiddenCount ? `Filters, ${hiddenCount} active` : 'Filters'"
					>
						Filters
						<template v-if="hiddenCount" #suffix>
							<Badge theme="blue" size="sm" :label="String(hiddenCount)" />
						</template>
					</Button>
				</template>

				<div class="w-56 space-y-4 p-2">
					<fieldset v-for="group in panelGroups" :key="group.key" class="space-y-0.5">
						<legend class="px-2 pb-1 text-sm text-ink-gray-5">{{ group.label }}</legend>
						<Checkbox
							v-for="option in group.options"
							:key="option.value"
							padded
							:label="option.label"
							:model-value="isOn(group.key, option.value)"
							@update:model-value="toggle(group.key, option.value)"
						/>
					</fieldset>
				</div>
			</Popover>

			<!-- Hairline rather than a gap: the two read as one control, as in Frappe's own
			     filter chip. -->
			<template v-if="anyActive">
				<span class="h-4 w-px bg-outline-gray-2" aria-hidden="true" />
				<Button
					size="sm"
					icon="lucide-x"
					class="rounded-l-none"
					aria-label="Clear filters"
					@click="clear"
				/>
			</template>
		</div>
	</div>
</template>
