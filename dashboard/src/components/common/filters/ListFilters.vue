<script setup lang="ts">
import { onKeyStroke } from "@vueuse/core"
import { Button, Dropdown, type DropdownOptions } from "frappe-ui"
import { computed, ref } from "vue"

import {
	type Condition,
	type ConditionValue,
	type FilterField,
	fieldIcon,
	valueFor,
} from "./fields"
import FilterChip from "./FilterChip.vue"

const props = defineProps<{ fields: FilterField[] }>()
const conditions = defineModel<Condition[]>({ required: true })

const menuOpen = ref(false)
// The chip added from the menu without a value takes focus, so typing can start at once.
const focusIndex = ref<number | null>(null)

const fieldOf = (key: string) => props.fields.find((field) => field.key === key)

function add(field: FilterField, value?: ConditionValue) {
	const operator = field.operators[0]
	if (Array.isArray(value) && mergeInto(field.key, operator.operator, value)) return
	// Read before the write: a route-backed model only updates once the URL does.
	focusIndex.value = value ? null : conditions.value.length
	conditions.value = [
		...conditions.value,
		[field.key, operator.operator, value ?? valueFor(field, operator)],
	]
}

// Separate chips are AND-ed, so a second pick on the same "is" chip joins it as "any of"
// rather than becoming a chip nothing can match.
function mergeInto(key: string, operator: string, picked: string[]) {
	const index = conditions.value.findIndex(([field, held]) => field === key && held === operator)
	if (index < 0) return false
	const values = conditions.value[index][2] as string[]
	update(index, [key, operator, [...new Set([...values, ...picked])]])
	return true
}

const update = (index: number, next: Condition) =>
	(conditions.value = conditions.value.map((condition, at) => (at === index ? next : condition)))

const remove = (index: number) =>
	(conditions.value = conditions.value.filter((_, at) => at !== index))

// Fields with options open onto them, so the first value is picked in the same motion.
const menuItem = (field: FilterField) => ({
	label: field.label,
	icon: fieldIcon(field),
	...(field.options.length
		? {
				submenu: field.options.map((option) => ({
					label: option.label,
					onClick: () => add(field, [option.value]),
				})),
			}
		: { onClick: () => add(field) }),
})

const menu = computed<DropdownOptions>(() =>
	(["standard", "question"] as const)
		.map((section) => ({
			group: section === "standard" ? "Fields" : "Form questions",
			options: props.fields.filter((field) => field.section === section).map(menuItem),
		}))
		.filter((group) => group.options.length),
)

onKeyStroke("f", (event) => {
	const target = event.target as HTMLElement
	if (/^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName) || target.isContentEditable) return
	if (event.metaKey || event.ctrlKey || event.altKey) return
	event.preventDefault()
	menuOpen.value = true
})
</script>

<template>
	<div class="space-y-2">
		<!-- The page's own controls (search, sort) lead the toolbar; Filter closes it. -->
		<div class="flex flex-wrap items-center gap-2">
			<slot />
			<Dropdown v-if="fields.length" v-model:open="menuOpen" :options="menu" align="end">
				<Button
					icon="lucide-list-filter"
					tooltip="Filter (F)"
					aria-label="Filter"
					aria-keyshortcuts="F"
				/>
			</Dropdown>
		</div>

		<div v-if="conditions.length" class="flex items-center gap-2 rounded-5 bg-surface-gray-2 p-1.5">
			<div class="flex min-w-0 flex-1 flex-wrap items-center gap-2">
				<template v-for="(condition, index) in conditions" :key="index">
					<FilterChip
						v-if="fieldOf(condition[0])"
						:field="fieldOf(condition[0])!"
						:autofocus="focusIndex === index"
						:model-value="condition"
						@update:model-value="update(index, $event)"
						@remove="remove(index)"
					/>
				</template>
				<Dropdown :options="menu" align="start">
					<Button variant="ghost" size="xs" icon="lucide-plus" aria-label="Add filter" />
				</Dropdown>
			</div>
			<Button variant="ghost" size="xs" class="h-5 px-1" @click="conditions = []"> Clear </Button>
		</div>
	</div>
</template>
