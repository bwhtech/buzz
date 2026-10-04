<script setup lang="ts">
import { Button, DatePicker, Dropdown, Icon, MultiSelect, Rating, TextInput } from "frappe-ui"
import { computed, onMounted, ref } from "vue"

import {
	type Condition,
	type ConditionValue,
	type FilterField,
	currentOperator,
	fieldIcon,
	valueFor,
	valueInput,
} from "./fields"

const props = defineProps<{ field: FilterField; autofocus?: boolean }>()
const condition = defineModel<Condition>({ required: true })
defineEmits<{ remove: [] }>()

const operator = computed(() => currentOperator(props.field, condition.value))
const input = computed(() => valueInput(props.field, operator.value))
const value = computed(() => condition.value[2])
const between = computed(() => operator.value.operator === "between")

const setValue = (next: ConditionValue) =>
	(condition.value = [props.field.key, condition.value[1], next])
const setEnd = (index: number, end: string) =>
	setValue((value.value as string[]).map((held, at) => (at === index ? end : held)))

const operatorOptions = computed(() =>
	props.field.operators.map((choice) => ({
		label: choice.label,
		selected: choice === operator.value,
		onClick: () => {
			const previous = operator.value.value ? undefined : value.value
			condition.value = [props.field.key, choice.operator, valueFor(props.field, choice, previous)]
		},
	})),
)

const choiceSummary = (selected: { label: string }[]) =>
	selected.length > 2
		? `${selected.length} selected`
		: selected.map((option) => option.label).join(", ") || "Select…"

// Ratings are stored as a fraction of five stars.
const stars = computed(() => Math.round(Number(value.value || 0) * 5))

const textInput = ref<InstanceType<typeof TextInput> | null>(null)
// The menu hands focus back to its trigger as it closes, so the input claims it a beat later.
onMounted(() => props.autofocus && setTimeout(() => textInput.value?.focus(), 50))
</script>

<template>
	<!-- A white pill on the grey filter panel, its parts split by hairlines. A ring, not a border,
	     so the xs controls keep their full height; no overflow clip, so their focus rings show. -->
	<div
		class="flex h-6 items-stretch divide-x divide-outline-gray-2 rounded-3 bg-surface-base ring-1 ring-outline-gray-2 [&>div]:flex"
	>
		<span class="flex items-center gap-1 px-2 text-xs text-ink-gray-8">
			<Icon :name="fieldIcon(field)" class="size-3.5 text-ink-gray-5" />
			{{ field.label }}
		</span>

		<Dropdown :options="operatorOptions" align="start">
			<Button variant="ghost" size="xs" class="rounded-none">{{ operator.label }}</Button>
		</Dropdown>

		<MultiSelect
			v-if="input === 'choice'"
			:hide-search="field.options.length < 8"
			:options="field.options"
			:model-value="value as string[]"
			@update:model-value="setValue(($event as unknown[]).map(String))"
		>
			<!-- The same xs ghost Button as the operator, so every segment shares one baseline. -->
			<template #trigger="{ selectedOptions }">
				<Button variant="ghost" size="xs" class="rounded-none">
					{{ choiceSummary(selectedOptions) }}
				</Button>
			</template>
		</MultiSelect>

		<TextInput
			v-else-if="input === 'text'"
			ref="textInput"
			variant="ghost"
			size="xs"
			class="w-36 [&_input]:rounded-none"
			:debounce="300"
			:aria-label="`${field.label} value`"
			:model-value="value as string"
			@update:model-value="setValue(String($event))"
		/>

		<template v-else-if="input === 'number' || input === 'date'">
			<template v-for="index in between ? [0, 1] : [0]" :key="index">
				<span v-if="index" class="flex items-center px-1.5 text-xs text-ink-gray-5"> and </span>
				<TextInput
					v-if="input === 'number'"
					type="number"
					variant="ghost"
					size="xs"
					class="w-16 [&_input]:rounded-none"
					:debounce="300"
					:aria-label="`${field.label} value`"
					:model-value="between ? (value as string[])[index] : (value as string)"
					@update:model-value="between ? setEnd(index, String($event)) : setValue(String($event))"
				/>
				<DatePicker
					v-else
					variant="ghost"
					size="xs"
					class="w-28 [&_button]:rounded-none [&_input]:rounded-none"
					:model-value="between ? (value as string[])[index] : (value as string)"
					@update:model-value="between ? setEnd(index, $event || '') : setValue($event || '')"
				/>
			</template>
		</template>

		<div v-else-if="input === 'rating'" class="flex items-center px-2">
			<Rating
				size="xs"
				:model-value="stars"
				:max="5"
				@update:model-value="setValue(String($event / 5))"
			/>
		</div>

		<Button
			variant="ghost"
			size="xs"
			icon="lucide-x"
			class="rounded-l-none"
			:aria-label="`Remove ${field.label} filter`"
			@click="$emit('remove')"
		/>
	</div>
</template>
